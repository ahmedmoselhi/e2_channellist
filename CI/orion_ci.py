import argparse
import requests
from bs4 import BeautifulSoup
import re
import xml.etree.ElementTree as ET
from xml.dom import minidom
from datetime import datetime, timezone
from urllib.parse import urljoin
import cloudscraper
import sys
import os
import time
import random

try:
    # curl_cffi impersonates a real browser's TLS fingerprint and is much more
    # reliable against Cloudflare than cloudscraper on GitHub-hosted runners.
    from curl_cffi import requests as curl_requests
except Exception:  # pragma: no cover - optional fallback for local use
    curl_requests = None


class FetchError(Exception):
    """Raised when a page could not be downloaded or was not a valid LyngSat page."""


class PermanentFetchError(FetchError):
    """Raised when a page is gone and retrying the same URL cannot help."""


class OrionScraperCI:
    """
    Orion Scraper CI - Absolute Edition (Orion v6.0)
    Logic: Exact name extraction and merging from v6.0 Archive.
    """
    def __init__(self, start_pos, end_pos, separate, advanced):
        self.start_pos = start_pos
        self.end_pos = end_pos
        self.separate = separate
        self.advanced = advanced
        
        self.POLARIZATION = {'H': '0', 'V': '1', 'L': '2', 'R': '3'}
        self.SYSTEM = {'DVB-S': '0', 'DVB-S2': '1'}
        self.MODULATION = {'QPSK': '1', '8PSK': '2', '16APSK': '3', '32APSK': '4'}
        self.FEC = {'1/2': '1', '2/3': '2', '3/4': '3', '5/6': '4', '7/8': '5', '8/9': '6', '9/10': '9', '3/5': '7', '4/5': '8', 'Auto': '0'}
        self.PLS_MODES = {'ROOT': '0', 'GOLD': '1', 'COMBO': '2'}
        
        # v6.0 Regex Engine
        self.re_freq_pol = re.compile(r'(\d{4,5})\s+([HVLR])')
        self.re_sr_fec = re.compile(r'(\d{4,5})\s+(\d{1,2}/\d{1,2})')
        self.re_sys = re.compile(r'(DVB-S2?)')
        self.re_mod = re.compile(r'(QPSK|8PSK|16APSK|32APSK)')
        self.re_title = re.compile(r'(.*?)\s+at\s+(\d+\.\d+)°([EW])')
        self.re_mis = re.compile(r'Stream\s+(\d+)', re.IGNORECASE)
        self.re_pls = re.compile(r'(Root|Gold|Combo)\s+(\d+)', re.IGNORECASE)
        self.re_t2mi_pid = re.compile(r'PID\s+(\d+)', re.IGNORECASE)
        self.re_t2mi_plp = re.compile(r'PLP\s+(\d+)', re.IGNORECASE)
        
        self.REGIONS = [
            {"name": "Asia", "url": "https://www.lyngsat.com/asia.html", "min": 73.0, "max": 180.0},
            {"name": "Europe", "url": "https://www.lyngsat.com/europe.html", "min": 0.0, "max": 73.0},
            {"name": "Atlantic", "url": "https://www.lyngsat.com/atlantic.html", "min": -70.0, "max": 0.0},
            {"name": "America", "url": "https://www.lyngsat.com/america.html", "min": -180.0, "max": -70.0}
        ]
        self.merged_db = []
        self.overrides = []
        self.mux_cache = {}
        self._not_found = set()
        self.skipped_urls = []
        self.out_of_range = []
        self.curl_session = (
            curl_requests.Session(impersonate="chrome") if curl_requests else None
        )
        self.cloud_session = cloudscraper.create_scraper()
        self.request_delay = 0.25
        self.jina_api_key = os.environ.get("JINA_API_KEY", "").strip()
        # The keyless Jina Reader tier is rate-limited; be conservative.
        self.jina_request_delay = 1.0 if self.jina_api_key else 3.0
        self._jina_last = False
        self._jina_notified = False
        self.max_attempts = 5

    def load_overrides(self, filename="custom_positions.txt"):
        """Loads user-defined exact satellite positions to snap adjacent satellites together."""
        if not os.path.exists(filename):
            return
        
        try:
            with open(filename, "r") as f:
                for line in f:
                    line = line.strip()
                    if line and not line.startswith("#"):
                        val = self.parse_to_float(line)
                        if val is not None:
                            # Reconstruct a clean display string (e.g., "19.2E")
                            display_str = line.upper().replace(' ', '')
                            self.overrides.append((val, display_str))
            
            if self.overrides:
                print(f"[+] Loaded {len(self.overrides)} position overrides from '{filename}'")
        except Exception as e:
            print(f"[!] Could not load {filename}: {e}")

    def _fetch_once(self, url, headers):
        """Fetch a URL once, preferring curl_cffi and falling back to cloudscraper.

        ``curl_cffi`` impersonates a real browser's TLS/JA3 fingerprint. GitHub
        Actions runners are frequently served HTTP 403 by Cloudflare when using
        plain requests/cloudscraper, so it is used as the primary client.

        If both direct clients are rejected, Jina Reader is used as a last
        resort. It fetches the page server-side and can return the original
        HTML, which bypasses IP-based blocks on GitHub-hosted runners.
        """
        errors = []
        last_resp = None
        self._jina_last = False

        if self.curl_session is not None:
            try:
                resp = self.curl_session.get(url, headers=headers, timeout=45)
                if resp.status_code != 403:
                    return resp, None
                last_resp = resp
                errors.append("curl_cffi HTTP 403")
            except Exception as exc:
                errors.append(f"curl_cffi {type(exc).__name__}: {exc}")

        try:
            resp = self.cloud_session.get(url, headers=headers, timeout=(15, 45))
            if resp.status_code != 403:
                return resp, None
            last_resp = resp
            errors.append("cloudscraper HTTP 403")
        except Exception as exc:
            errors.append(f"cloudscraper {type(exc).__name__}: {exc}")

        # Last resort: ask Jina Reader to fetch the page and return its HTML.
        jina_headers = {
            'Accept': 'text/html',
            'X-Return-Format': 'html',
        }
        if self.jina_api_key:
            jina_headers['Authorization'] = f'Bearer {self.jina_api_key}'

        try:
            resp = requests.get(
                "https://r.jina.ai/" + url,
                headers=jina_headers,
                timeout=(15, 90),
            )
            if resp.status_code == 200 and '<html' in resp.text.lower():
                self._jina_last = True
                if not self._jina_notified:
                    print("[i] Direct LyngSat access is blocked; using Jina Reader fallback.")
                    self._jina_notified = True
                return resp, None
            errors.append(f"jina HTTP {resp.status_code}")
        except Exception as exc:
            errors.append(f"jina {type(exc).__name__}: {exc}")

        if last_resp is not None:
            return last_resp, None
        return None, "; ".join(errors)

    def get_html(self, url, attempts=None):
        """Download a page with retries, exponential backoff and rate-limit handling.

        GitHub Actions runners occasionally hit transient Cloudflare/network
        failures. Returning ``None`` after a single request silently dropped
        whole regions or satellites, which produced incomplete XML files.
        """
        attempts = attempts or self.max_attempts
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) '
                          'AppleWebKit/537.36 (KHTML, like Gecko) '
                          'Chrome/124.0.0.0 Safari/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
            'Accept-Language': 'en-US,en;q=0.9',
        }
        last_error = "unknown error"

        for attempt in range(1, attempts + 1):
            retry_after = None
            resp, fetch_error = self._fetch_once(url, headers)

            if resp is not None and resp.status_code == 200:
                delay = self.jina_request_delay if self._jina_last else self.request_delay
                time.sleep(delay)
                return resp.text

            if resp is not None:
                last_error = f"HTTP {resp.status_code}"
                if resp.status_code in (404, 410):
                    # The page is gone; retrying the same URL cannot help.
                    self._not_found.add(url)
                    break
                if resp.status_code == 429:
                    try:
                        retry_after = float(resp.headers.get('Retry-After', ''))
                    except (TypeError, ValueError):
                        retry_after = None
                elif resp.status_code not in (403, 408, 425, 500, 502, 503, 504):
                    # Other 4xx errors will not improve with a retry.
                    break
            else:
                last_error = fetch_error or "unknown error"

            if attempt < attempts:
                delay = min(60.0, (2 ** (attempt - 1)) + random.uniform(0.0, 1.5))
                if retry_after is not None:
                    delay = max(delay, min(retry_after, 120.0))
                print(f"[!] GET failed ({last_error}); retry {attempt}/{attempts - 1} "
                      f"in {delay:.1f}s: {url}")
                time.sleep(delay)

        if url in self._not_found:
            print(f"[i] GET not found: {url} ({last_error})")
        else:
            print(f"[!] GET failed permanently: {url} ({last_error})")
        return None

    def scrape_mux_t2mi(self, url):
        """Extract the T2-MI streams published on a LyngSat mux subpage.

        The satellite page only lists the stream/PLP combinations; the actual
        T2-MI PIDs are published on the per-transponder mux page, in
        ``div.mux-header`` blocks such as:
            Stream 4, PLP 0 on PID 4098

        A transponder can publish several PIDs for the same stream/PLP (for
        example an SI stream on PID 4096 and a T2-MI stream on PID 4097), so
        the result is an ordered list of entries rather than a dict keyed by
        ``(stream, plp)``, which would drop all but the last PID.
        """
        if url in self.mux_cache:
            return self.mux_cache[url]

        entries = []
        seen = set()
        # Mux pages are optional: if one is unavailable we fall back to the
        # default T2-MI PID instead of delaying the whole run.
        html = self.get_html(url, attempts=2)
        if html:
            soup = BeautifulSoup(html, 'html.parser')
            for header in soup.select('div.mux-header'):
                text = header.get_text(' ', strip=True)
                pid_match = self.re_t2mi_pid.search(text)
                if not pid_match:
                    continue
                stream_match = self.re_mis.search(text)
                plp_match = self.re_t2mi_plp.search(text)
                stream = stream_match.group(1) if stream_match else None
                plp = plp_match.group(1) if plp_match else None
                pid = pid_match.group(1)
                key = (stream, plp, pid)
                if key in seen:
                    continue
                seen.add(key)
                entries.append({
                    "stream": stream, "plp": plp, "pid": pid, "used": False,
                })

        self.mux_cache[url] = entries
        return entries

    @staticmethod
    def resolve_t2mi_pid(entries, stream, plp):
        """Resolve one T2-MI PID for a stream/PLP combination.

        Each mux entry is claimed once, in document order, so a satellite
        page that lists the same stream/PLP on several rows receives every
        PID the mux page publishes (4096, then 4097, ...). The ``used`` flags
        are reset at the start of each satellite page.
        """
        if not entries:
            return None

        def matches(entry):
            s, p = entry["stream"], entry["plp"]
            return (
                (s is None or stream is None or s == stream)
                and (p is None or plp is None or p == plp)
            )

        # Prefer an exact (stream, plp) entry that has not been claimed yet.
        for entry in entries:
            if entry["stream"] == stream and entry["plp"] == plp and not entry["used"]:
                entry["used"] = True
                return entry["pid"]

        # Then any unused wildcard match (a mux header may omit stream or PLP).
        for entry in entries:
            if matches(entry) and not entry["used"]:
                entry["used"] = True
                return entry["pid"]

        # Fall back to a PID that is unique for this stream or PLP.
        if stream is not None:
            stream_pids = {e["pid"] for e in entries if e["stream"] == stream}
            if len(stream_pids) == 1:
                return next(iter(stream_pids))
        if plp is not None:
            plp_pids = {e["pid"] for e in entries if e["plp"] == plp}
            if len(plp_pids) == 1:
                return next(iter(plp_pids))

        # The mux page published fewer entries than the satellite page has
        # rows; reuse the last matching PID instead of dropping the row.
        for entry in reversed(entries):
            if matches(entry):
                return entry["pid"]
        if len(entries) == 1:
            return entries[0]["pid"]
        return None

    def parse_to_float(self, pos_str):
        if not pos_str: return None
        # Tolerate whitespace inserted inside the number ("19. 2 °E") so a
        # position is never silently truncated to its decimal part.
        match = re.search(r'(\d+(?:\s*\.\s*\d+)?)\s*°?\s*([EW])', pos_str, re.IGNORECASE)
        if not match: return None
        val = float(re.sub(r'\s+', '', match.group(1)))
        return -val if match.group(2).upper() == 'W' else val

    def is_in_range(self, pos, start, end):
        if start <= end: return start <= pos <= end
        return pos >= start or pos <= end

    @staticmethod
    def _tp_key(tp):
        """Identity of a transponder, used to drop exact duplicates."""
        return (
            tp["frequency"],
            tp["polarization"],
            tp["symbol_rate"],
            tp["system"],
            tp["modulation"],
            tp.get("is_id", ""),
            tp.get("t2mi_plp_id", ""),
            tp.get("t2mi_pid", ""),
        )

    @staticmethod
    def _tp_band(tp):
        """Return the frequency band of a transponder from its frequency (Hz)."""
        freq = int(tp["frequency"])
        if 3400000 <= freq <= 4200000:
            return "C"
        if 10700000 <= freq <= 12750000:
            return "KU"
        if 17000000 <= freq <= 22000000:
            return "KA"
        return "other"

    def _summarize_tps(self, tps, dedupe=False):
        """Count transponders by band plus T2-MI and multistream usage."""
        stats = {"total": 0, "C": 0, "KU": 0, "KA": 0, "other": 0,
                 "t2mi": 0, "mis": 0}
        seen = set()
        for tp in tps:
            if dedupe:
                key = self._tp_key(tp)
                if key in seen:
                    continue
                seen.add(key)
            stats["total"] += 1
            stats[self._tp_band(tp)] += 1
            if tp.get("_t2mi"):
                stats["t2mi"] += 1
            if tp.get("_mis"):
                stats["mis"] += 1
        return stats

    def _summarize_db(self):
        """Summarize every transponder that will be written this run."""
        total = {"total": 0, "C": 0, "KU": 0, "KA": 0, "other": 0,
                 "t2mi": 0, "mis": 0}
        for item in self.merged_db:
            stats = self._summarize_tps(item["tps"], dedupe=True)
            for key, value in stats.items():
                total[key] += value
        return total

    @staticmethod
    def _numeric_sort_key(value):
        return (0, int(value)) if value.isdigit() else (1, value)

    @staticmethod
    def _format_tp_stats(stats):
        return (f"{stats['total']} tp (C:{stats['C']} KU:{stats['KU']} "
                f"KA:{stats['KA']} other:{stats['other']} | "
                f"T2-MI:{stats['t2mi']} multistream:{stats['mis']})")

    def clean_merged_name(self, existing_name, new_name):
        """Restored v6.0 exact merging logic for satellite names."""
        if not existing_name: return new_name
        parts = re.split(r'[ /&]+', existing_name)
        new_parts = re.split(r'[ /&]+', new_name)
        if all(p in parts for p in new_parts): return existing_name
        return f"{existing_name} / {new_name}"

    def scrape_sat_page(self, url):
        html = self.get_html(url)
        if not html:
            if url in self._not_found:
                raise PermanentFetchError(f"page not found (HTTP 404): {url}")
            raise FetchError(f"download failed: {url}")
        soup = BeautifulSoup(html, 'html.parser')
        title = soup.title.string if soup.title and soup.title.string else ""
        title_match = self.re_title.search(title)
        if not title_match:
            lowered = html.lower()
            if "doesn't exist" in lowered or "tried to access" in lowered:
                raise PermanentFetchError(f"page no longer exists on LyngSat: {url}")
            # Usually a Cloudflare challenge or an incomplete response.
            raise FetchError(f"unexpected page title {title[:100]!r}: {url}")
        
        name, deg, direct = title_match.groups()
        raw_pos = self.parse_to_float(f"{deg}{direct}")
        tps = []

        # Mux entries are cached across satellites and carry a ``used`` marker
        # so each row on this page claims its own PID in document order.
        # Reset the markers for this page (also matters when a page is retried).
        for entries in self.mux_cache.values():
            for entry in entries:
                entry["used"] = False

        for row in soup.find_all('tr'):
            cells = row.find_all(['td', 'th'])
            if len(cells) < 2: continue
            freq_pol, params_txt = None, ""
            for i in range(len(cells) - 1):
                f_p_match = self.re_freq_pol.search(cells[i].get_text(separator=' ', strip=True))
                if f_p_match:
                    nxt_txt = cells[i+1].get_text(separator=' ', strip=True)
                    if self.re_sr_fec.search(nxt_txt):
                        freq_pol, params_txt = f_p_match, nxt_txt
                        break
            if not freq_pol: continue
            freq, pol = freq_pol.groups()
            sr, fec = self.re_sr_fec.search(params_txt).groups()
            sys_m = self.re_sys.search(params_txt); mod_m = self.re_mod.search(params_txt)
            
            base_tp = {
                "frequency": str(int(freq)*1000), "symbol_rate": str(int(sr)*1000),
                "polarization": self.POLARIZATION.get(pol,'0'), "fec_inner": self.FEC.get(fec,'0'),
                "system": self.SYSTEM.get(sys_m.group(1) if sys_m else 'DVB-S', '0'),
                "modulation": self.MODULATION.get(mod_m.group(1) if mod_m else 'QPSK', '1')
            }
            mis = self.re_mis.findall(params_txt); pls = self.re_pls.search(params_txt)
            plps = self.re_t2mi_plp.findall(params_txt); pids = self.re_t2mi_pid.findall(params_txt)
            pmode = self.PLS_MODES.get(pls.group(1).upper(), '0') if pls else None
            pcode = pls.group(2) if pls else None
            has_mis = bool(mis or pls)
            has_t2mi = bool(plps or pids or 'T2-MI' in params_txt.upper())

            # The satellite page lists Stream/PLP but not the T2-MI PID.
            # That value lives on the transponder's mux subpage.
            t2mi_entries = []
            mux_link = row.find('a', href=re.compile(r'/muxes/'))
            if mux_link and (plps or 'T2-MI' in params_txt.upper()):
                mux_url = urljoin('https://www.lyngsat.com/', mux_link['href'])
                t2mi_entries = self.scrape_mux_t2mi(mux_url)

            if mis or plps:
                for i in range(max(len(mis), len(plps), 1)):
                    new_tp = base_tp.copy()
                    if has_mis:
                        new_tp["_mis"] = True
                    if has_t2mi:
                        new_tp["_t2mi"] = True
                    sid = mis[i] if i < len(mis) else (mis[-1] if mis else "1" if pls else None)
                    plp = plps[i] if i < len(plps) else (plps[-1] if plps else None)
                    pid = pids[i] if i < len(pids) else (pids[-1] if pids else None)
                    if not pid and t2mi_entries:
                        pid = self.resolve_t2mi_pid(t2mi_entries, sid, plp)
                    # Some mux pages omit the PID entirely; Enigma2 expects one for T2-MI.
                    if not pid and (plps or 'T2-MI' in params_txt.upper()):
                        pid = "4096"
                    if sid: new_tp["is_id"] = sid
                    if pmode: new_tp["pls_mode"], new_tp["pls_code"] = pmode, pcode
                    if plp: new_tp["t2mi_plp_id"] = plp
                    if pid: new_tp["t2mi_pid"] = pid
                    tps.append(new_tp)
            else:
                new_tp = base_tp.copy()
                if has_mis:
                    new_tp["_mis"] = True
                if has_t2mi:
                    new_tp["_t2mi"] = True
                if pls: new_tp["is_id"], new_tp["pls_mode"], new_tp["pls_code"] = "1", pmode, pcode
                tps.append(new_tp)
        return {"name": name.strip(), "pos": raw_pos, "tps": tps, "display": f"{deg}{direct}"}

    def _region_is_in_scan(self, region, u_s, u_e):
        if u_s <= u_e:
            return not (u_e < region["min"] or u_s > region["max"])
        return u_s <= region["max"] or u_e >= region["min"]

    def _collect_satellite_urls(self, region_htmls, u_s, u_e):
        """Collect every satellite page URL that falls inside the requested range."""
        urls = []
        seen = set()
        region_counts = {}

        for region in self.REGIONS:
            html = region_htmls.get(region["name"])
            if not html:
                continue

            soup = BeautifulSoup(html, 'html.parser')
            last_pos = None
            region_count = 0
            for row in soup.find_all('tr'):
                cells = row.find_all('td')
                if len(cells) < 2:
                    continue
                # Advert/news/navigation rows contain many cells and inherit
                # the previous satellite's position, which would queue their
                # cross-reference links at the wrong position. Real satellite
                # rows (position or continuation) have only a handful of cells.
                if len(cells) > 8:
                    continue

                txt = cells[0].get_text(strip=True)
                if not txt:
                    # "News at LyngSat" channel cross-reference rows have an
                    # empty first cell and would otherwise inherit the previous
                    # satellite's position, queueing their satellite links at
                    # the wrong slot.
                    continue
                if '°' in txt:
                    # A real position cell contains exactly one degree sign.
                    # Summary/navigation rows hold the whole region's positions
                    # at once and must be ignored entirely. Notes such as
                    # "Yamal 402 (incl. 1.6°)" are continuation rows and simply
                    # keep the previous position.
                    if txt.count('°') > 1:
                        continue
                    parsed = self.parse_to_float(txt)
                    if parsed is not None:
                        last_pos = parsed

                if last_pos is None or not self.is_in_range(last_pos, u_s, u_e):
                    continue

                for link in row.find_all('a', href=True):
                    href = link['href'].strip()
                    if not href or '.html' not in href:
                        continue
                    # Skip tracker/channel/package/index pages. Only actual
                    # satellite pages belong in the scrape queue.
                    if any(part in href for part in (
                        'index', 'tracker/', 'packages/', 'stream/',
                        'tvchannels/', 'advert',
                    )):
                        continue

                    if href.startswith(('http://', 'https://')):
                        if 'lyngsat.com' not in href:
                            continue
                        url = href
                    elif href.startswith('/'):
                        url = 'https://www.lyngsat.com' + href
                    else:
                        url = 'https://www.lyngsat.com/' + href

                    if url not in seen:
                        seen.add(url)
                        urls.append(url)
                        region_count += 1

            region_counts[region["name"]] = region_count

        self.region_counts = region_counts
        return urls

    def _merge_data(self, data):
        """Apply position overrides and merge a scraped satellite into the database."""
        for target_pos, target_display in self.overrides:
            # If scraped satellite is within 0.6 degrees of target override, force it
            if abs(data['pos'] - target_pos) <= 0.6:
                data['pos'] = target_pos
                data['display'] = target_display
                break

        for group in self.merged_db:
            if abs(group['pos'] - data['pos']) <= 0.4:
                group['tps'].extend(data['tps'])
                group['name'] = self.clean_merged_name(group['name'], data['name'])
                return group

        self.merged_db.append(data)
        return data

    @staticmethod
    def _is_lyngsat_page(html):
        """Return True only for a real LyngSat page, not a Cloudflare challenge."""
        if not html:
            return False
        soup = BeautifulSoup(html, 'html.parser')
        title = soup.title.string if soup.title and soup.title.string else ""
        return 'lyngsat' in title.lower() and ('°' in html or '&deg;' in html)

    def run(self):
        self.load_overrides()  # Load predefined positions
        run_started = time.time()

        u_s, u_e = self.parse_to_float(self.start_pos), self.parse_to_float(self.end_pos)
        if u_s is None or u_e is None:
            print(f"[!] Invalid scan range: {self.start_pos} -> {self.end_pos}")
            sys.exit(1)
        self._scan_start, self._scan_end = u_s, u_e

        print("=" * 60)
        print(f"[i] Orion Scraper CI | scan range: {self.start_pos} -> {self.end_pos} "
              f"({u_s:+.1f}° to {u_e:+.1f}°)")
        print(f"[i] Separate C/KU bands: {self.separate} | "
              f"Advanced MIS/PLS/T2-MI: {self.advanced}")
        print(f"[i] Output file: {os.path.abspath('satellites.xml')}")
        print(f"[i] Jina Reader API key: "
              f"{'configured' if self.jina_api_key else 'not set'}")
        if self.overrides:
            print(f"[i] Position overrides: "
                  f"{', '.join(display for _, display in self.overrides)}")
        print("=" * 60)

        # --- Download region indexes first. A missing region index used to be
        # skipped silently, which dropped every satellite in that region.
        region_htmls = {}
        failed_regions = []
        for region in self.REGIONS:
            if not self._region_is_in_scan(region, u_s, u_e):
                continue

            print(f"[i] Downloading {region['name']} index: {region['url']}")
            html = self.get_html(region['url'], attempts=6)
            if html and not self._is_lyngsat_page(html):
                print(f"[!] {region['name']} index returned a non-LyngSat page "
                      f"(likely a Cloudflare challenge).")
                html = None
            if not html:
                print(f"[!] {region['name']} index failed; making one delayed attempt...")
                time.sleep(20)
                html = self.get_html(region['url'], attempts=3)
                if html and not self._is_lyngsat_page(html):
                    html = None

            if html:
                region_htmls[region['name']] = html
                print(f"[+] {region['name']} index downloaded "
                      f"({len(html) / 1024:.1f} KB).")
            else:
                failed_regions.append(region['name'])
                print(f"[!] Could not download {region['name']} index.")

        satellite_urls = self._collect_satellite_urls(region_htmls, u_s, u_e)
        print(f"[i] Discovered {len(satellite_urls)} satellite page(s) in range.")
        if getattr(self, 'region_counts', None):
            breakdown = ", ".join(
                f"{name}={count}" for name, count in self.region_counts.items()
            )
            print(f"    by region: {breakdown}")

        # --- Scrape in several rounds so a transient failure is retried instead
        # of producing an incomplete satellites.xml.
        pending = satellite_urls
        scraped = 0
        for round_no in range(1, 4):
            if not pending:
                break

            print(f"[i] Scrape round {round_no}: {len(pending)} satellite page(s) remaining.")
            round_started = time.time()
            retry_urls = []
            round_ok = 0
            round_skipped = 0
            round_out = 0
            round_tps = 0

            for index, url in enumerate(pending, 1):
                try:
                    data = self.scrape_sat_page(url)
                except PermanentFetchError as exc:
                    print(f"    [i] {index}/{len(pending)} {url}: {exc} (skipped)")
                    self.skipped_urls.append(url)
                    round_skipped += 1
                    continue
                except FetchError as exc:
                    print(f"    [!] {index}/{len(pending)} {url}: {exc}")
                    retry_urls.append(url)
                    continue
                except Exception as exc:
                    print(f"    [!] {index}/{len(pending)} {url}: "
                          f"{type(exc).__name__}: {exc}")
                    retry_urls.append(url)
                    continue

                if data and self.is_in_range(data['pos'], u_s, u_e):
                    group = self._merge_data(data)
                    scraped += 1
                    round_ok += 1
                    stats = self._summarize_tps(data['tps'])
                    round_tps += stats['total']
                    print(f"    [+] {index}/{len(pending)} "
                          f"{data['display']:>7} {data['name']}: "
                          f"{self._format_tp_stats(stats)}")
                    if group is not data:
                        print(f"         merged into {group['display']} "
                              f"{group['name']} "
                              f"(combined {len(group['tps'])} tp before dedupe)")
                    if stats['total'] == 0:
                        print(f"         source: {url}")
                    if stats['t2mi'] or stats['mis']:
                        ids = sorted({
                            tp.get('is_id') for tp in data['tps']
                            if tp.get('is_id')
                        }, key=self._numeric_sort_key)
                        plps = sorted({
                            tp.get('t2mi_plp_id') for tp in data['tps']
                            if tp.get('t2mi_plp_id')
                        }, key=self._numeric_sort_key)
                        detail = []
                        if ids:
                            detail.append("stream/IS ids=" + ",".join(ids))
                        if plps:
                            detail.append("PLP ids=" + ",".join(plps))
                        if detail:
                            print(f"         T2-MI/multistream detail: "
                                  f"{'; '.join(detail)}")
                elif data:
                    # Region indexes occasionally link satellites just outside
                    # the requested arc. They are not failures, so skip them
                    # instead of retrying the same page three times.
                    print(f"    [i] {index}/{len(pending)} {url} is at "
                          f"{data['display']} "
                          f"(outside {self.start_pos}-{self.end_pos}); skipping")
                    self.out_of_range.append(url)
                    round_out += 1
                else:
                    print(f"    [!] {index}/{len(pending)} No usable data from {url}")
                    retry_urls.append(url)

            print(f"[i] Round {round_no} complete: scraped={round_ok} "
                  f"(transponders={round_tps}) failed={len(retry_urls)} "
                  f"skipped={round_skipped} out_of_range={round_out} "
                  f"in {time.time() - round_started:.1f}s")

            pending = retry_urls
            if pending and round_no < 3:
                delay = 15 * round_no
                print(f"[!] {len(pending)} satellite page(s) failed; "
                      f"retrying in {delay}s...")
                time.sleep(delay)

        overall = self._summarize_db()
        print("=" * 60)
        print(f"[i] Scrape summary: pages discovered={len(satellite_urls)} "
              f"scraped={scraped} failed={len(pending)} "
              f"skipped={len(self.skipped_urls)} "
              f"out_of_range={len(self.out_of_range)}")
        print(f"[i] Satellites discovered (after position merge): "
              f"{len(self.merged_db)}")
        if self.merged_db:
            positions = [item['pos'] for item in self.merged_db]
            print(f"[i] Position coverage: {min(positions):+.1f}° to "
                  f"{max(positions):+.1f}°")
        if self.separate:
            output_entries = sum(
                (1 if any(self._tp_band(t) == "KU" for t in item['tps']) else 0)
                + (1 if any(self._tp_band(t) == "C" for t in item['tps']) else 0)
                for item in self.merged_db
            )
            print(f"[i] Scraped satellite entries (C/KU split): {output_entries} "
                  f"(+1 terrestrial network entry)")
            unseparated = overall['KA'] + overall['other']
            if unseparated:
                print(f"[i] Note: {unseparated} KA/other transponder(s) are not "
                      f"written in --separate mode (C/KU bands only).")
        else:
            print(f"[i] Scraped satellite entries: {len(self.merged_db)} "
                  f"(+1 terrestrial network entry)")
        print(f"[i] Transponders discovered: {self._format_tp_stats(overall)}")
        if self.mux_cache:
            mapped = sum(1 for mapping in self.mux_cache.values() if mapping)
            print(f"[i] T2-MI mux pages fetched: {len(self.mux_cache)} "
                  f"(with PID mappings: {mapped})")
        if failed_regions:
            print(f"[!] Region indexes that failed: {', '.join(failed_regions)}")
        if self.skipped_urls:
            print("[i] Satellite pages that no longer exist on LyngSat (skipped):")
            for url in self.skipped_urls:
                print(f"    - {url}")
        if self.out_of_range:
            print("[i] Satellite pages outside the requested arc (skipped):")
            for url in self.out_of_range:
                print(f"    - {url}")
        if pending:
            print("[!] Satellite pages that could not be scraped:")
            for url in pending:
                print(f"    - {url}")
        elapsed = time.time() - run_started
        print(f"[i] Total run time: {int(elapsed // 60)}m {elapsed % 60:.1f}s")
        print("=" * 60)

        # Only fall back to the previous file when this run was incomplete.
        # A complete run is authoritative and may legitimately drop satellites.
        # A permanently missing page is treated as a skip, but the previous
        # data is still kept for it so a dead LyngSat link cannot erase a
        # satellite that was downloaded successfully before.
        incomplete = bool(
            failed_regions or pending or self.skipped_urls or not satellite_urls
        )
        self.save_xml(merge_previous=incomplete)

    def save_xml(self, merge_previous=False):
        root = ET.Element("satellites")
        gmt_now = datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M:%S GMT')
        comment = ET.Comment(f" created by Absolute Edition (Orion v6.0 Enhanced) on {gmt_now} ")
        root.insert(0, comment)

        new_positions = set()
        self.merged_db.sort(key=lambda x: x['pos'])
        for item in self.merged_db:
            base_p = int(item['pos'] * 10)
            if self.separate:
                c_band = [t for t in item['tps'] if 3400000 <= int(t['frequency']) <= 4200000]
                ku_band = [t for t in item['tps'] if 10700000 <= int(t['frequency']) <= 12750000]

                if ku_band:
                    ku_name = f"{item['display']} KU-band {item['name']}"
                    self.add_node(root, ku_name, str(base_p), ku_band)
                    new_positions.add(str(base_p))

                if c_band:
                    c_name = f"{item['display']} C-band {item['name']}"
                    c_pos = base_p + (1 if base_p >= 0 else -1)
                    self.add_node(root, c_name, str(c_pos), c_band)
                    new_positions.add(str(c_pos))
            else:
                self.add_node(root, f"{item['display']} {item['name']}", str(base_p), item['tps'])
                new_positions.add(str(base_p))

        self.add_terrestrial_networks(root)
        new_positions.add("1800")

        # Keep satellites from the previous run when their page could not be
        # scraped this time. This prevents a transient GitHub runner/Cloudflare
        # failure from deleting valid satellites from the committed file.
        if merge_previous:
            merged_previous = self._merge_previous_satellites(root, new_positions)
            if merged_previous:
                print(f"[i] Kept {merged_previous} satellite(s) from the previous satellites.xml.")

        # Keep the XML ordered by position (comment stays first).
        satellites = root.findall("sat")
        for sat in satellites:
            root.remove(sat)
        satellites.sort(key=lambda sat: int(sat.get("position", "0") or 0))
        for sat in satellites:
            root.append(sat)

        # Never write a <sat> node without transponders: the receiver would see
        # an unusable entry, and a rerun could silently keep it because the
        # position already exists. Fail loudly instead of committing bad data.
        sat_nodes = root.findall("sat")
        empty_nodes = [
            sat for sat in sat_nodes if not sat.findall("transponder")
        ]
        if empty_nodes:
            print("[!] Refusing to write satellites.xml: "
                  "satellite entries without transponders:")
            for sat in empty_nodes:
                print(f"    - position {sat.get('position')}: "
                      f"{sat.get('name', '')}")
            print("[!] The existing satellites.xml was left untouched.")
            sys.exit(1)

        pretty = minidom.parseString(ET.tostring(root, 'utf-8')).toprettyxml(indent="    ")
        final = re.sub(r'<\?xml.*?\?>', '<?xml version="1.0" encoding="iso-8859-1"?>', pretty)
        with open('satellites.xml', 'w', encoding='iso-8859-1') as f: f.write(final)

        tp_count = sum(len(sat.findall("transponder")) for sat in sat_nodes)
        print(f"[i] Wrote {os.path.abspath('satellites.xml')}: "
              f"{len(sat_nodes)} satellite entries, {tp_count} transponders, "
              f"{os.path.getsize('satellites.xml') / 1024:.1f} KB.")
        per_position = sorted(
            (int(sat.get("position")), len(sat.findall("transponder")))
            for sat in sat_nodes
            if (sat.get("position") or "").lstrip("-").isdigit()
        )
        if per_position:
            print("[i] Written transponders per position: " + " ".join(
                f"{position / 10:+.1f}°={count}"
                for position, count in per_position
            ))

    def _merge_previous_satellites(self, root, new_positions, path="satellites.xml"):
        """Append previous <sat> nodes whose position was not scraped this run."""
        if not os.path.exists(path):
            return 0

        try:
            old_root = ET.parse(path).getroot()
        except Exception as exc:
            print(f"[!] Could not read previous {path} for merge: {exc}")
            return 0

        scan_start = getattr(self, '_scan_start', None)
        scan_end = getattr(self, '_scan_end', None)

        new_position_ints = {
            int(p) for p in new_positions
            if p.lstrip('-').isdigit()
        }

        merged = 0
        for old_sat in list(old_root.findall("sat")):
            position = old_sat.get("position")
            name = old_sat.get("name", "")
            if not position or position in new_positions:
                continue
            if name == "Teresterrial Networks":
                continue

            try:
                old_position = int(position)
            except (TypeError, ValueError):
                continue

            # The same satellite may have been scraped at a corrected position
            # this run (LyngSat titles can be off by a few tenths of a degree,
            # e.g. 7.3W vs 7.1W). Keeping the old entry as well would create a
            # permanent duplicate, because the corrected position will never
            # match the stale one. _merge_data() uses the same 0.4° tolerance.
            if any(abs(old_position - p) <= 4 for p in new_position_ints):
                continue

            # Do not re-introduce satellites outside the requested scan range.
            if scan_start is not None and scan_end is not None:
                pos = old_position / 10.0
                if not self.is_in_range(pos, scan_start - 0.2, scan_end + 0.2):
                    continue

            # Parsed pretty-printed XML carries indentation as text/tail nodes.
            # Drop them so minidom can indent the merged node cleanly.
            for element in old_sat.iter():
                if element.text is not None and not element.text.strip():
                    element.text = None
                if element.tail is not None and not element.tail.strip():
                    element.tail = None

            root.append(old_sat)
            new_positions.add(position)
            merged += 1
            print(f"[!] Keeping previous satellite (not scraped this run): "
                  f"{name} (position {position})")

        return merged

    @staticmethod
    def add_terrestrial_networks(root):
        """Append the fixed terrestrial network transponders to the output XML."""
        satellite = ET.SubElement(
            root, "sat", name="Teresterrial Networks", flags="1", position="1800"
        )
        for frequency, symbol_rate in (("11665000", "45000000"), ("11895000", "44000000")):
            ET.SubElement(
                satellite,
                "transponder",
                frequency=frequency,
                symbol_rate=symbol_rate,
                polarization="0",
                fec_inner="3",
                system="1",
                modulation="2",
                onid="1",
                tsid="1",
            )

    def add_node(self, root, name, pos, tps):
        sat = ET.SubElement(root, "sat", name=name, flags="1", position=pos)
        seen = set()
        for tp in tps:
            # Internal logging flags (``_mis``/``_t2mi``) must never reach XML.
            tp = {k: v for k, v in tp.items() if not k.startswith("_")}
            # Expanded key to distinguish between feeds/streams sharing a frequency
            key = self._tp_key(tp)
            if key not in seen:
                seen.add(key)
                if not self.advanced:
                    tp = {k: v for k, v in tp.items() if k not in ["is_id", "pls_mode", "pls_code", "t2mi_pid", "t2mi_plp_id"]}
                ET.SubElement(sat, "transponder", **tp)

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--start", default="45.0W")
    parser.add_argument("--end", default="108.2E")
    parser.add_argument("--separate", action="store_true", default=True)
    parser.add_argument("--advanced", action="store_true", default=True)
    args = parser.parse_args()
    OrionScraperCI(args.start, args.end, args.separate, args.advanced).run()
