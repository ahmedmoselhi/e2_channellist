import argparse
import requests
from bs4 import BeautifulSoup
import re
import xml.etree.ElementTree as ET
from xml.dom import minidom
from datetime import datetime, timezone
import cloudscraper
import sys

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
        self.processed_urls = set()

    def get_html(self, url):
        headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'}
        try:
            scraper = cloudscraper.create_scraper()
            resp = scraper.get(url, headers=headers, timeout=20)
            return resp.text if resp.status_code == 200 else None
        except: return None

    def parse_to_float(self, pos_str):
        if not pos_str: return None
        match = re.search(r'(\d+\.?\d*)\s*°?\s*([EW])', pos_str.upper())
        if not match: return None
        val = float(match.group(1))
        return -val if match.group(2) == 'W' else val

    def is_in_range(self, pos, start, end):
        if start <= end: return start <= pos <= end
        return pos >= start or pos <= end

    def clean_merged_name(self, existing_name, new_name):
        """Restored v6.0 exact merging logic for satellite names."""
        if not existing_name: return new_name
        parts = re.split(r'[ /&]+', existing_name)
        new_parts = re.split(r'[ /&]+', new_name)
        if all(p in parts for p in new_parts): return existing_name
        return f"{existing_name} / {new_name}"

    def scrape_sat_page(self, url):
        html = self.get_html(url)
        if not html: return None
        soup = BeautifulSoup(html, 'html.parser')
        title_match = self.re_title.search(soup.title.string if soup.title else "")
        if not title_match: return None
        
        name, deg, direct = title_match.groups()
        raw_pos = self.parse_to_float(f"{deg}{direct}")
        tps = []
        
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
            
            if mis or plps:
                for i in range(max(len(mis), len(plps), 1)):
                    new_tp = base_tp.copy()
                    sid = mis[i] if i < len(mis) else (mis[-1] if mis else "1" if pls else None)
                    if sid: new_tp["is_id"] = sid
                    if pmode: new_tp["pls_mode"], new_tp["pls_code"] = pmode, pcode
                    if i < len(pids): new_tp["t2mi_pid"] = pids[i]
                    if i < len(plps): new_tp["t2mi_plp_id"] = plps[i]
                    tps.append(new_tp)
            else:
                new_tp = base_tp.copy()
                if pls: new_tp["is_id"], new_tp["pls_mode"], new_tp["pls_code"] = "1", pmode, pcode
                tps.append(new_tp)
        return {"name": name.strip(), "pos": raw_pos, "tps": tps, "display": f"{deg}{direct}"}

    def run(self):
        u_s, u_e = self.parse_to_float(self.start_pos), self.parse_to_float(self.end_pos)
        for region in self.REGIONS:
            if (u_s <= u_e and not (u_e < region["min"] or u_s > region["max"])) or \
               (u_s > u_e and (u_s <= region["max"] or u_e >= region["min"])):
                html = self.get_html(region['url'])
                if not html: continue
                soup = BeautifulSoup(html, 'html.parser')
                l_pos = None
                for row in soup.find_all('tr'):
                    cells = row.find_all('td')
                    if len(cells) < 2: continue
                    txt = cells[0].get_text(strip=True)
                    if '°' in txt: l_pos = self.parse_to_float(txt)
                    if l_pos is not None and self.is_in_range(l_pos, u_s, u_e):
                        for link in row.find_all('a', href=True):
                            href = link['href']
                            if "html" in href and "index" not in href and "lyngsat.com" not in href:
                                url = "https://www.lyngsat.com/" + href
                                if url not in self.processed_urls:
                                    self.processed_urls.add(url)
                                    data = self.scrape_sat_page(url)
                                    if data and self.is_in_range(data['pos'], u_s, u_e):
                                        matched = False
                                        for g in self.merged_db:
                                            if abs(g['pos'] - data['pos']) <= 0.4:
                                                g['tps'].extend(data['tps'])
                                                # Exact v6.0 name merging
                                                g['name'] = self.clean_merged_name(g['name'], data['name'])
                                                matched = True; break
                                        if not matched: self.merged_db.append(data)
        self.save_xml()

    def save_xml(self):
        root = ET.Element("satellites")
        gmt_now = datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M:%S GMT')
        comment = ET.Comment(f" created by Absolute Edition (Orion v6.0 Enhanced) on {gmt_now} ")
        root.insert(0, comment)

        self.merged_db.sort(key=lambda x: x['pos'])
        for item in self.merged_db:
            base_p = int(item['pos'] * 10)
            if self.separate:
                c_band = [t for t in item['tps'] if 3400000 <= int(t['frequency']) <= 4200000]
                ku_band = [t for t in item['tps'] if 10700000 <= int(t['frequency']) <= 12750000]
                
                if ku_band:
                    ku_name = f"{item['display']} KU-band {item['name']}"
                    self.add_node(root, ku_name, str(base_p), ku_band)

                if c_band:
                    c_name = f"{item['display']} C-band {item['name']}"
                    c_pos = base_p + (1 if base_p >= 0 else -1)
                    self.add_node(root, c_name, str(c_pos), c_band)
            else:
                self.add_node(root, f"{item['display']} {item['name']}", str(base_p), item['tps'])
        
        pretty = minidom.parseString(ET.tostring(root, 'utf-8')).toprettyxml(indent="    ")
        final = re.sub(r'<\?xml.*?\?>', '<?xml version="1.0" encoding="iso-8859-1"?>', pretty)
        with open('satellites.xml', 'w', encoding='iso-8859-1') as f: f.write(final)

    def add_node(self, root, name, pos, tps):
        sat = ET.SubElement(root, "sat", name=name, flags="1", position=pos)
        seen = set()
        for tp in tps:
            key = (tp["frequency"], tp["polarization"], tp.get("is_id", ""), tp.get("t2mi_plp_id", ""))
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
