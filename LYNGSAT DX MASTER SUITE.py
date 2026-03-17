import os
import sys
import re
import csv
import time
import concurrent.futures
# Platform-specific input handling
if sys.platform == 'win32':
    import msvcrt
else:
    import select
from datetime import datetime

# ==============================================================================
# [ 🎨 MASTER GRAPHICS ENGINE ]
# ==============================================================================
C_BASE    = "\033[38;5;250m"  
C_GOLD    = "\033[38;5;220m"  
C_SKY     = "\033[38;5;117m"  
C_LIME    = "\033[38;5;121m"  
C_CRIMSON = "\033[38;5;196m"  
C_VIOLET  = "\033[38;5;141m"  
C_TEAL    = "\033[38;5;51m"
BOLD      = "\033[1m"
ENDC      = "\033[0m"

def print_banner():
    print(f"""
{C_GOLD}█▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀█
█  {C_SKY}🛰️  {BOLD}LYNGSAT DX MASTER SUITE{ENDC}{C_GOLD}           |  {C_LIME}VERSION 12.4{ENDC}{C_GOLD} |  {C_VIOLET}TWO-PASS PRO{ENDC}{C_GOLD}   █
█▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄█{ENDC}""")

def log_proc(msg, color=C_BASE):
    ts = datetime.now().strftime("%H:%M:%S")
    print(f"{C_BASE}[{ts}]{ENDC} {color}{msg}{ENDC}")

def setup_storage(sat_deg, sat_dir, is_cband):
    effective_pos = float(sat_deg) + 0.1 if is_cband else float(sat_deg)
    pos_label = f"{effective_pos:.1f}{sat_dir}"
    f_dir, c_dir = "frequencies", os.path.join("channellist", pos_label)
    for d in [f_dir, c_dir]:
        if not os.path.exists(d): os.makedirs(d)
    return f_dir, c_dir, pos_label

# ==============================================================================
# [ 🛰️ ENGINE B: RECURSIVE MUX PARSER - VERSION 12.8 ]
# ==============================================================================
def parse_mux_channels(url, save_path, freq_label):
    try:
        from curl_cffi import requests
        from bs4 import BeautifulSoup
        
        res = requests.get(url, impersonate="chrome", timeout=15)
        soup = BeautifulSoup(res.content, 'html.parser')
        
        rows = soup.find_all('tr')
        ch_list = []
        current_stream_id = "0"
        is_validated_t2mi = False 
        
        # Metadata Keywords to ignore (The "Junk" Filter)
        junk_keywords = [
            "ROLL-OFF", "FOOTPRINT", "C BAND", "KU BAND", "DVB-S", 
            "CLEAR", "MPEG", "HEVC", "SD", "HD", "UHD", "4K", "WITHIN", "DBW"
        ]

        for row in rows:
            tds = row.find_all('td')
            if len(tds) < 3: continue

            row_text = row.get_text(" ", strip=True).upper()
            
            # The Discriminator: Must see "PLP" to be T2-MI
            if "PLP" in row_text:
                is_validated_t2mi = True

            # Extract PLP ID (Not Stream ID)
            plp_m = re.search(r'PLP\s*(\d+)', row_text, re.I)
            if plp_m:
                current_stream_id = plp_m.group(1)
                continue 

            # 2. Extract Channel Name & Link
            name_td = tds[2]
            channel_name = name_td.get_text(strip=True)
            
            # --- THE JUNK FILTER ---
            if not channel_name or any(jk in channel_name.upper() for jk in junk_keywords):
                continue

            # 3. Extract & Validate SID
            sid_text = tds[0].get_text(strip=True)
            sid_match = re.search(r'\d+', sid_text)
            sid = sid_match.group() if sid_match else "0"
            
            # Filter out technical rows that often have SID 0 or very low placeholder SIDs
            if sid == "0" or len(channel_name) < 2:
                continue

            # 4. Determine Type
            link = name_td.find('a', href=True)
            is_radio = link and "radiochannels" in link['href']
            
            ch_data = [sid, f"{channel_name} (S{current_stream_id})", "1" if not is_radio else "2"]
            
            if ch_data not in ch_list:
                ch_list.append(ch_data)

        # --- v12.8 ABORT GATE (The 12537 V Fix) ---
        # Only proceed if we found a PLP/Stream marker OR it's a known Bosnian T2-MI provider
        if not is_validated_t2mi:
            # Special check: If no Stream ID found, but it claims to be Vidi TV, 
            # we check if 'PLP' appears anywhere else in the body
            if "VIDI TV" in soup.get_text().upper() and "PLP" in soup.get_text().upper():
                pass # Allow it
            else:
                return 0 # Kill standard transponders like 12537 V

        # --- UI LOGIC (Preserved v5.0 Graphics) ---
        if ch_list:
            os.makedirs(os.path.dirname(save_path), exist_ok=True)
            with open(save_path, 'w', newline='', encoding='utf-8') as f:
                writer = csv.writer(f)
                writer.writerows(ch_list)
            
            print(f"      {C_VIOLET}┌──────────┬─────────────────────────────────────────────┬──────────┐{ENDC}")
            print(f"      {C_VIOLET}│ SID      │ CHANNEL NAME                                │ TYPE     │{ENDC}")
            print(f"      {C_VIOLET}├──────────┼─────────────────────────────────────────────┼──────────┤{ENDC}")
            
            for c in ch_list: 
                c_type = "TV" if c[2]=="1" else "Radio"
                print(f"      {C_VIOLET}│{ENDC} {c[0]:<8} {C_VIOLET}│{ENDC} {c[1][:43]:<43} {C_VIOLET}│{ENDC} {c_type:<8} {C_VIOLET}│{ENDC}")
            
            print(f"      {C_VIOLET}└──────────┴─────────────────────────────────────────────┴──────────┘{ENDC}")
            print(f"  {C_LIME}└─► Services extracted: {len(ch_list)}{ENDC}\n")
            return len(ch_list)
            
        return 0

    except Exception as e:
        return 0

# ==============================================================================
# [ 🛰️ ENGINE A: DEEP SATELLITE SCANNER - VERSION 12.5 ]
# ==============================================================================
def deep_scan_satellite(url):
    global global_total_channels, global_total_tps
    try:
        from curl_cffi import requests
        from bs4 import BeautifulSoup
        import re, os, csv

        log_proc(f"Establishing Uplink: {url}", C_GOLD)
        res = requests.get(url, impersonate="chrome", timeout=15)
        html_source = res.text
        soup = BeautifulSoup(html_source, 'html.parser')

        # Extract satellite position
        title = soup.title.string if soup.title else ""
        sat_m = re.search(r'(\d+\.?\d*)\s?°?\s?([EW])', title)
        if not sat_m: return

        sat_deg, sat_dir = float(sat_m.group(1)), sat_m.group(2)
        sat_slug = url.split('/')[-1].replace(".html", "")
        rows = soup.find_all('tr')

        # --- AUTO BAND DETECTION ---
        c_w, k_w = 0, 0
        for r in rows:
            td1 = r.find('td')
            if td1:
                fm = re.search(r'^(\d{4,5})\s*([LRHV])', td1.get_text(strip=True).upper())
                if fm:
                    f_val = int(fm.group(1))
                    if 3000 <= f_val <= 4999: c_w += 2
                    elif f_val >= 10000: k_w += 2

        auto_suggest_cband = c_w >= k_w if (c_w + k_w) > 0 else False

        # UI DIALOGUE (Preserved v5.0 Graphics)
        print(f"\n{C_VIOLET}┌──[ BAND CONFIGURATION ]────────────────────────────────────────────────┐{ENDC}")
        print(f"{C_VIOLET}│{ENDC}  Target: {C_GOLD}{sat_slug:<55}{ENDC}{C_VIOLET}│{ENDC}")
        print(f"{C_VIOLET}│{ENDC}  Sat Degree: {C_SKY}{sat_deg}° {sat_dir:<46}{ENDC}{C_VIOLET}│{ENDC}")
        print(f"{C_VIOLET}│{ENDC}  Auto-Detection Suggestion: {C_LIME if auto_suggest_cband else C_BASE}{'C-BAND' if auto_suggest_cband else 'KU-BAND':<35}{ENDC}{C_VIOLET}│{ENDC}")
        print(f"{C_VIOLET}└────────────────────────────────────────────────────────────────────────┘{ENDC}")
        
        prompt_text = f"{C_SKY}❓ Treat this satellite as C-BAND? (y/n) [Auto-resolving in 10s]: {ENDC}"
        print(prompt_text, end='', flush=True)

        user_choice = None
        st_t = time.time()
        while (time.time() - st_t) < 10:
            if sys.platform == 'win32':
                if msvcrt.kbhit(): user_choice = sys.stdin.readline().strip().lower(); break
            else:
                rdy, _, _ = select.select([sys.stdin], [], [], 0.1)
                if rdy: user_choice = sys.stdin.readline().strip().lower(); break
            time.sleep(0.1)

        is_cband_sat = (user_choice in ['y', 'yes']) if user_choice else auto_suggest_cband
        print(f"\n  {C_GOLD}└─► Proceeding with: {BOLD}{'C-BAND' if is_cband_sat else 'KU-BAND'}{ENDC}")

        f_dir, c_dir, pos_label = setup_storage(sat_deg, sat_dir, is_cband_sat)
        print(f"\n{C_GOLD}╔═{ '═'*84 }═╗\n║ {BOLD}{C_SKY}SATELLITE POSITION:{ENDC} {sat_deg}°{sat_dir:<10} {BOLD}{C_SKY}TARGET:{ENDC} {sat_slug:<44} ║\n╚═{ '═'*84 }═╝{ENDC}")

        transponders_data = []
        seen_tps = set()

        # --- PRECISION DISCOVERY ENGINE ---
        for row in rows:
            tds = row.find_all('td')
            if len(tds) < 5: continue
            
            row_text = row.get_text(" ", strip=True).upper()
            fm = re.search(r'(\d{4,5})\s*([LRHV])', row_text)
            if not fm: continue
            
            f_v, p_r = fm.group(1), fm.group(2)
            beam_link = row.find('a', href=re.compile(r'muxes/|/muxes/'))
            if not beam_link: continue
            
            mux_url = f"https://www.lyngsat.com/muxes/{beam_link['href'].split('/')[-1]}"

            # STAGE 3: Recursive T2-MI Validation & Extraction (v13.0 Fixed)
            try:
                mux_res = requests.get(mux_url, impersonate="chrome", timeout=10)
                mux_soup = BeautifulSoup(mux_res.text, 'html.parser')
                mux_text = mux_soup.get_text().upper()
                
                # STRICT T2-MI CHECK: Must contain "PLP"
                is_t2mi = "PLP" in mux_text
                # Bosnian Exception (Vidi TV 11402V)
                is_vidi = "VIDI TV" in mux_text and "PLP" in mux_text

                if not (is_t2mi or is_vidi):
                    continue

                # --- EXTRACT PLP, PID & SYMBOL RATE ---
                plp_m = re.search(r'PLP\s*(\d+)', mux_text)
                pid_m = re.search(r'PID\s*(\d+)', mux_text)
                sr_m  = re.search(r'SR-FEC:.*?(\d+)', mux_text)
                
                plp_id = plp_m.group(1) if plp_m else "0"
                pid_id = pid_m.group(1) if pid_m else "4096"
                sr     = sr_m.group(1)  if sr_m  else "0"

                if int(sr) < 1000: 
                    continue

                tp_id = f"{f_v}{p_r}{sr}"
                if tp_id not in seen_tps:
                    seen_tps.add(tp_id)
                    mod = "8PSK" if "8PSK" in mux_text else "QPSK"
                    hw_pos = round(float(sat_deg) + 0.1, 1) if is_cband_sat else float(sat_deg)
                    p_map = {"H":"0","V":"1","L":"2","R":"3"}

                    transponders_data.append({
                        "f_v": f_v, "p_r": p_r, "sr": sr, "mod": mod, "mux_url": mux_url,
                        "file_label": f"{f_v}{p_r}{sr}PLP{plp_id}PID{pid_id}",
                        "csv_row": [f_v, p_map.get(p_r,"0"), sr, f"{hw_pos:.1f}", sat_dir, "2", "9", "1", "1", "2" if mod=="8PSK" else "1", "0", "2", mux_url]
                    })
            except Exception:
                continue

        # --- SUMMARY & DRILL DOWN (Preserved Graphics) ---
        print(f"\n{C_TEAL}┌{'─'*10}┬{'─'*8}┬{'─'*10}┬{'─'*10}┬{'─'*42}┐{ENDC}")
        print(f"{C_TEAL}│ {C_SKY}{'FREQ':<8} │ {C_SKY}{'POL':<6} │ {C_SKY}{'SR':<8} │ {C_SKY}{'MOD':<8} │ {C_SKY}{'MUX URL / BEAM REFERENCE':<40} │{ENDC}")
        print(f"{C_TEAL}├{'─'*10}┼{'─'*8}┼{'─'*10}┼{'─'*10}┼{'─'*42}┤{ENDC}")

        csv_rows = []
        for tp in transponders_data:
            print(f"{C_TEAL}│{ENDC} {C_LIME}{tp['f_v']:<8} {C_TEAL}│{ENDC} {C_BASE}{tp['p_r']:<6} {C_TEAL}│{ENDC} {C_GOLD}{tp['sr']:<8} {C_TEAL}│{ENDC} {C_VIOLET}{tp['mod']:<8} {C_TEAL}│{ENDC} {C_BASE}{tp['mux_url'].split('/')[-1][:40]:<40} {C_TEAL}│{ENDC}")
            csv_rows.append(tp['csv_row'])

        print(f"{C_TEAL}└{'─'*10}┴{'─'*8}┴{'─'*10}┴{'─'*10}┴{'─'*42}┘{ENDC}")
        print(f"  {C_LIME}└─► Total Verified T2-MI Frequencies Discovered: {BOLD}{len(transponders_data)}{ENDC}")

        global_total_tps += len(transponders_data)

        for tp in transponders_data:
            print(f"\n{C_TEAL}▶ {C_SKY}Drill-Down: Fetching services for {ENDC}{BOLD}{C_LIME}{tp['f_v']} {tp['p_r']}{ENDC}")
            target_csv = os.path.join(c_dir, f"{tp['file_label']}.csv")
            global_total_channels += parse_mux_channels(tp['mux_url'], target_csv, tp['file_label'])

        with open(os.path.join(f_dir, f"f{pos_label}.csv"), 'w', newline='', encoding='utf-8') as f:
            writer = csv.writer(f)
            writer.writerow(["Freq", "Pol", "SR", "Pos", "Dir", "Inv", "FEC", "Sys", "Mod", "RO", "Pilot", "MuxURL"])
            writer.writerows(csv_rows)

    except Exception as e: log_proc(f"Error: {e}", C_CRIMSON)

# ==============================================================================
# [ 🚀 MAIN INTERFACE ]
# ==============================================================================
global_total_channels = 0
global_total_tps = 0

if __name__ == "__main__":
    os.system('clear' if os.name == 'posix' else 'cls')
    print_banner()
    
    # Restore All Helper Texts
    print(f"{C_BASE}┌──────────────────────────────────────────────────────────────────────────┐{ENDC}")
    print(f"{C_BASE}│{ENDC}  {BOLD}{C_SKY}RECURSIVE DEEP-SCAN SYSTEM v12.4{ENDC}                                       {C_BASE}│{ENDC}")
    print(f"{C_BASE}│{ENDC}                                                                          {C_BASE}│{ENDC}")
    print(f"{C_BASE}│{ENDC}  {C_LIME}Instructions:{ENDC}                                                           {C_BASE}│{ENDC}")
    print(f"{C_BASE}│{ENDC}  • Paste your LyngSat URLs line by line.                                 {C_BASE}│{ENDC}")
    print(f"{C_BASE}│{ENDC}  • Press {BOLD}ENTER{ENDC} on an empty line to trigger the batch extraction.          {C_BASE}│{ENDC}")
    print(f"{C_BASE}│{ENDC}                                                                          {C_BASE}│{ENDC}")
    print(f"{C_BASE}│{ENDC}  {C_GOLD}System Notes:{ENDC}                                                           {C_BASE}│{ENDC}")
    print(f"{C_BASE}│{ENDC}  • C-Band frequencies automatically apply +0.1 degree indexing.          {C_BASE}│{ENDC}")
    print(f"{C_BASE}│{ENDC}  • Two-Pass Engine: Extracts Frequencies first, then Service Tables.     {C_BASE}│{ENDC}")
    print(f"{C_BASE}└──────────────────────────────────────────────────────────────────────────┘{ENDC}")
    
    urls = []
    while True:
        u = input(f"{C_GOLD}🔗 SAT URL #{len(urls)+1}:{ENDC} ").strip()
        if not u: break
        urls.append(u)

    if urls:
        start = time.time()
        for u in urls:
            deep_scan_satellite(u)
        duration = time.time() - start
        
        # FINAL GLOBAL SUMMARY WITH FULL METRICS
        print(f"\n{C_GOLD}█▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀█{ENDC}")
        print(f"{C_GOLD}█ {C_SKY}GLOBAL DX EXECUTION SUMMARY{ENDC}{C_GOLD}                                                  █{ENDC}")
        print(f"{C_GOLD}█ {C_BASE}├─ Total Satellites Processed: {BOLD}{len(urls):<10}{ENDC}{C_GOLD}                                █{ENDC}")
        print(f"{C_GOLD}█ {C_BASE}├─ Total Unique Transponders:  {BOLD}{global_total_tps:<10}{ENDC}{C_GOLD}                                █{ENDC}")
        print(f"{C_GOLD}█ {C_BASE}├─ Total Channels Mapped:      {BOLD}{global_total_channels:<10}{ENDC}{C_GOLD}                                █{ENDC}")
        print(f"{C_GOLD}█ {C_BASE}└─ Operation Time:             {BOLD}{duration:.2f}s{ENDC}{C_GOLD}                                      █{ENDC}")
        print(f"{C_GOLD}█▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄█{ENDC}\n")
