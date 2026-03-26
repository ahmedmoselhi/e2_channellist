import requests
from bs4 import BeautifulSoup
import re
import xml.etree.ElementTree as ET
from xml.dom import minidom
import time
import sys
import threading
from datetime import datetime, timezone

# --- Enable Arrow Keys for Input ---
try:
    import readline
except ImportError:
    try:
        from pyreadline3 import Readline
        readline = Readline()
    except ImportError:
        readline = None 

try:
    import cloudscraper
    HAS_CLOUDSCRAPER = True
except ImportError:
    HAS_CLOUDSCRAPER = False

class OperationSummary:
    """Tracks and displays the final scraping statistics."""
    def __init__(self):
        self.total_sats = 0
        self.total_tps = 0

    def display(self):
        print("\n" + "═"*45)
        print("         🛰️  ORION SCRAPER SUMMARY")
        print("═"*45)
        print(f" 📂 Total Satellites Merged:  {self.total_sats}")
        print(f" 📶 Total Frequencies Found:  {self.total_tps}")
        print("═"*45)
        print(" ✅ Operation Complete. satellites.xml is ready.")

class OrionScraper:
    def __init__(self):
        # Enigma2 standard mappings
        self.POLARIZATION = {'H': '0', 'V': '1', 'L': '2', 'R': '3'}
        self.SYSTEM = {'DVB-S': '0', 'DVB-S2': '1'}
        self.MODULATION = {'QPSK': '1', '8PSK': '2', '16APSK': '3', '32APSK': '4'}
        self.FEC = { 
            '1/2': '1', '2/3': '2', '3/4': '3', '5/6': '4', '7/8': '5', 
            '8/9': '6', '9/10': '9', '3/5': '7', '4/5': '8', 'Auto': '0' 
        }
        self.PLS_MODES = {'ROOT': '0', 'GOLD': '1', 'COMBO': '2'}

        # Regex Engine
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
            {"name": "Asia",     "url": "https://www.lyngsat.com/asia.html",     "min": 73.0,   "max": 180.0},
            {"name": "Europe",   "url": "https://www.lyngsat.com/europe.html",   "min": 0.0,    "max": 73.0},
            {"name": "Atlantic", "url": "https://www.lyngsat.com/atlantic.html", "min": -70.0,  "max": 0.0},
            {"name": "America",  "url": "https://www.lyngsat.com/america.html",  "min": -180.0, "max": -70.0}
        ]
        
        # Persistence: Initialize session once
        if HAS_CLOUDSCRAPER:
            self.session = cloudscraper.create_scraper(browser={'browser': 'chrome', 'platform': 'windows'})
        else:
            self.session = requests.Session()
            
        self.merged_db = []
        self.processed_urls = set()
        self.stats = OperationSummary()

    def get_html(self, url, retries=3):
        """Enhanced with Session Persistence and Exponential Backoff."""
        headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'}
        for i in range(retries):
            try:
                resp = self.session.get(url, headers=headers, timeout=25)
                if resp.status_code == 200:
                    return resp.text
                if resp.status_code == 403:
                    time.sleep(5) # Cooldown for blocks
            except Exception:
                pass
            
            if i < retries - 1:
                time.sleep(2 ** i) # Exponential backoff: 1s, 2s, 4s
        return None

    def parse_to_float(self, pos_str):
        if not pos_str: return None
        pos_str = pos_str.upper().strip()
        match = re.search(r'(\d+\.?\d*)\s*°?\s*([EW])', pos_str)
        if not match: return None
        val = float(match.group(1))
        return -val if match.group(2) == 'W' else val

    def is_in_range(self, pos, start, end):
        if start <= end: return start <= pos <= end
        return pos >= start or pos <= end

    def clean_merged_name(self, existing_name, new_name):
        if not existing_name: return new_name
        parts = re.split(r'[ /&]+', existing_name)
        new_parts = re.split(r'[ /&]+', new_name)
        if all(p in parts for p in new_parts): return existing_name
        return f"{existing_name} / {new_name}"

    def scrape_sat_page(self, url):
        html = self.get_html(url)
        if not html: return None
        soup = BeautifulSoup(html, 'html.parser')
        
        # Defensive check for title
        if not soup.title or not soup.title.string: return None
        title_match = self.re_title.search(soup.title.string)
        if not title_match: return None
        
        name, deg, direct = title_match.groups()
        raw_pos = self.parse_to_float(f"{deg}{direct}")
        
        tps = []
        for row in soup.find_all('tr'):
            cells = row.find_all(['td', 'th'])
            if len(cells) < 2: continue
            
            freq_pol, params_txt = None, ""
            for i in range(len(cells) - 1):
                cell_txt = cells[i].get_text(separator=' ', strip=True)
                f_p_match = self.re_freq_pol.search(cell_txt)
                if f_p_match:
                    nxt_txt = cells[i+1].get_text(separator=' ', strip=True)
                    s_f_match = self.re_sr_fec.search(nxt_txt)
                    if s_f_match:
                        freq_pol, params_txt = f_p_match, nxt_txt
                        break
            
            if not freq_pol or not params_txt: continue
                
            freq, pol = freq_pol.groups()
            s_f = self.re_sr_fec.search(params_txt)
            sr, fec = s_f.groups()
            sys_match = self.re_sys.search(params_txt)
            mod_match = self.re_mod.search(params_txt)

            base_tp = {
                "frequency": str(int(freq)*1000), 
                "symbol_rate": str(int(sr)*1000),
                "polarization": self.POLARIZATION.get(pol,'0'), 
                "fec_inner": self.FEC.get(fec,'0'),
                "system": self.SYSTEM.get(sys_match.group(1) if sys_match else 'DVB-S', '0'),
                "modulation": self.MODULATION.get(mod_match.group(1) if mod_match else 'QPSK', '1')
            }

            mis_streams = self.re_mis.findall(params_txt)
            pls_match = self.re_pls.search(params_txt)
            t2mi_pids = self.re_t2mi_pid.findall(params_txt)
            t2mi_plps = self.re_t2mi_plp.findall(params_txt)

            pls_mode, pls_code = None, None
            if pls_match:
                pls_mode = self.PLS_MODES.get(pls_match.group(1).upper(), '0')
                pls_code = pls_match.group(2)

            if mis_streams or t2mi_plps:
                max_len = max(len(mis_streams), len(t2mi_plps), 1)
                for i in range(max_len):
                    new_tp = base_tp.copy()
                    s_id = mis_streams[i] if i < len(mis_streams) else (mis_streams[-1] if mis_streams else "1" if pls_match else None)
                    plp_id = t2mi_plps[i] if i < len(t2mi_plps) else (t2mi_plps[-1] if t2mi_plps else None)
                    pid_id = t2mi_pids[i] if i < len(t2mi_pids) else (t2mi_pids[-1] if t2mi_pids else None)
                    if s_id: new_tp["is_id"] = s_id
                    if pls_mode:
                        new_tp["pls_mode"] = pls_mode
                        new_tp["pls_code"] = pls_code
                    if pid_id: new_tp["t2mi_pid"] = pid_id
                    if plp_id: new_tp["t2mi_plp_id"] = plp_id
                    tps.append(new_tp)
            else:
                new_tp = base_tp.copy()
                if pls_match:
                    new_tp["is_id"] = "1"
                    new_tp["pls_mode"] = pls_mode
                    new_tp["pls_code"] = pls_code
                tps.append(new_tp)

        return {"name": name, "pos": raw_pos, "tps": tps, "display": f"{deg}{direct}"}

    def timed_input(self, prompt, default, timeout=10):
        print(f"{prompt} [Default: {default}] (Auto-exec in {timeout}s): ", end='', flush=True)
        result = [None]
        def get_input(): result[0] = sys.stdin.readline().strip()
        thread = threading.Thread(target=get_input)
        thread.daemon = True
        thread.start()
        thread.join(timeout)
        if result[0] is not None: return result[0] if result[0] != "" else default
        print(f"\n[!] Using default: {default}")
        return default

    def print_banner(self):
        banner = r"""
 ____         _                _____                                
/ __ \       (_)              / ____|                               
| |  | |_ __ _  ___  _ __   | (___   ___ _ __ __ _ _ __   ___ _ __ 
| |  | | '__| |/ _ \| '_ \   \___ \ / __| '__/ _` | '_ \ / _ \ '__|
| |__| | |  | | (_) | | | |  ____) | (__| | | (_| | |_) |  __/ |   
 \____/|_|  |_|\___/|_| |_| |_____/ \___|_|  \__,_| .__/ \___|_|   
                                                  | |               
       🛰️  THE ABSOLUTE EDITION v6.0 (UPDATED)      |_|               
        """
        print(banner)

    def run(self):
        self.print_banner()
        s_in = self.timed_input("  ➤ Enter Start Position", "45.0W")
        e_in = self.timed_input("  ➤ Enter End Position", "108.2E")
        sep_choice = self.timed_input("  ➤ Separate C and KU bands? (Y/N)", "Y").upper()
        adv_choice = self.timed_input("  ➤ Add MIS/PLS/T2-MI parameters? (Y/N)", "Y").upper()
        
        u_start, u_end = self.parse_to_float(s_in), self.parse_to_float(e_in)
        if u_start is None or u_end is None: return

        print(f"\n[⚡] Initializing Scan: {s_in} to {e_in}...")

        for region in self.REGIONS:
            should_scan = False
            if u_start <= u_end:
                if not (u_end < region["min"] or u_start > region["max"]): should_scan = True
            else:
                if u_start <= region["max"] or u_end >= region["min"]: should_scan = True
            
            if should_scan:
                print(f"\n🔍 Searching {region['name']} Region...")
                html = self.get_html(region['url'])
                if not html: continue
                soup = BeautifulSoup(html, 'html.parser')
                last_pos = None
                for row in soup.find_all('tr'):
                    cells = row.find_all('td')
                    if not cells or len(cells) < 2: continue
                    row_txt = cells[0].get_text(strip=True)
                    if '°' in row_txt:
                        found_pos = self.parse_to_float(row_txt)
                        if found_pos is not None: last_pos = found_pos
                    
                    if last_pos is not None and self.is_in_range(last_pos, u_start, u_end):
                        for link in row.find_all('a', href=True):
                            href = link['href']
                            if "html" in href and "index" not in href and "lyngsat.com" not in href:
                                full_url = "https://www.lyngsat.com/" + href
                                if full_url not in self.processed_urls:
                                    self.processed_urls.add(full_url)
                                    data = self.scrape_sat_page(full_url)
                                    if data and self.is_in_range(data['pos'], u_start, u_end):
                                        print(f"    📡 Found: {data['name']} ({data['display']})")
                                        matched = False
                                        for group in self.merged_db:
                                            if abs(group['pos'] - data['pos']) <= 0.4:
                                                group['tps'].extend(data['tps'])
                                                group['name'] = self.clean_merged_name(group['name'], data['name'])
                                                matched = True
                                                break
                                        if not matched: self.merged_db.append(data)

        self.save_xml(separate_bands=(sep_choice == "Y"), add_adv=(adv_choice == "Y"))
        self.stats.display()

    def save_xml(self, separate_bands=True, add_adv=True):
        root = ET.Element("satellites")
        gmt_now = datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M:%S GMT')
        comment = ET.Comment(f" created by Absolute Edition (Orion v6.0) on {gmt_now} ")
        root.insert(0, comment)
        
        self.merged_db.sort(key=lambda x: x['pos'])

        for item in self.merged_db:
            base_pos = int(item['pos'] * 10)
            if separate_bands:
                c_band = [t for t in item['tps'] if 3400000 <= int(t['frequency']) <= 4200000]
                ku_band = [t for t in item['tps'] if 10700000 <= int(t['frequency']) <= 12750000]
                
                # FIX: Process KU-band FIRST in the loop so it is added to XML first
                if ku_band:
                    ku_name = f"{item['display']} KU-band {item['name']}"
                    self.add_sat_node(root, ku_name, str(base_pos), ku_band, add_adv)

                if c_band:
                    c_name = f"{item['display']} C-band {item['name']}"
                    # Keep your logic: East positive (+1), West negative (-1)
                    c_pos = base_pos + (1 if base_pos >= 0 else -1)
                    self.add_sat_node(root, c_name, str(c_pos), c_band, add_adv)
            else:
                self.add_sat_node(root, f"{item['display']} {item['name']}", str(base_pos), item['tps'], add_adv)

        raw_xml = ET.tostring(root, 'utf-8')
        pretty_xml = minidom.parseString(raw_xml).toprettyxml(indent="    ")
        final_output = re.sub(r'<\?xml.*?\?>', '<?xml version="1.0" encoding="iso-8859-1"?>', pretty_xml)
        with open('satellites.xml', 'w', encoding='iso-8859-1', errors='ignore') as f: f.write(final_output)

    def add_sat_node(self, root, name, position, tps, add_adv):
        sat_node = ET.SubElement(root, "sat", name=name, flags="1", position=position)
        self.stats.total_sats += 1
        
        seen_tps = set()
        for tp in tps:
            tp_key = (tp["frequency"], tp["polarization"], tp.get("is_id", ""), tp.get("t2mi_plp_id", ""))
            
            if tp_key not in seen_tps:
                seen_tps.add(tp_key)
                if not add_adv:
                    tp = {k: v for k, v in tp.items() if k not in ["is_id", "pls_mode", "pls_code", "t2mi_pid", "t2mi_plp_id"]}
                ET.SubElement(sat_node, "transponder", **tp)
                self.stats.total_tps += 1

if __name__ == "__main__":
    OrionScraper().run()
