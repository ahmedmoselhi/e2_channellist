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
    # Locked at 80 characters
    line_top = "█" + "▀" * 78 + "█"
    line_bot = "█" + "▄" * 78 + "█"
    
    # We use :<60 and :>15 to anchor the title and version to opposite sides
    title = f"🛰️  LYNGSAT DX MASTER SUITE"
    meta = f"VER 15.8 | TWO-PASS"
    
    # Print with the gold color wrapper
    print(f"{C_GOLD}{line_top}{ENDC}")
    print(f"{C_GOLD}█  {C_SKY}{BOLD}{title:<52}{ENDC}{C_GOLD} | {meta:>20}  █{ENDC}")
    print(f"{C_GOLD}{line_bot}{ENDC}")

def log_proc(msg, color=C_BASE):
    ts = datetime.now().strftime("%H:%M:%S")
    print(f"{C_BASE}[{ts}]{ENDC} {color}{msg}{ENDC}")

def setup_storage(sat_deg, sat_dir, is_cband):
    effective_pos = float(sat_deg) + 0.1 if is_cband else float(sat_deg)
    pos_label = f"{effective_pos:.1f}{sat_dir}"
    f_dir, c_dir = "frequencies", os.path.join("channellist", pos_label)
    
    for d in [f_dir, c_dir]:
        if not os.path.exists(d): 
            os.makedirs(d)
        else:
            # --- NEW: DELETE EXISTING CSVs BEFORE SAVING ---
            for item in os.listdir(d):
                if item.endswith(".csv") and (d == f_dir or d == c_dir):
                    # For 'frequencies', only delete the file matching this sat's label
                    if d == f_dir and item == f"f{pos_label}.csv":
                        os.remove(os.path.join(d, item))
                    # For 'channellist', clear the specific satellite sub-directory
                    elif d == c_dir:
                        os.remove(os.path.join(d, item))
                        
    return f_dir, c_dir, pos_label

# ==============================================================================
# [ 📝 LOGGING & DX DUAL-STREAM ENGINE - VERSION 13.5 ]
# ==============================================================================
class MasterLogger:
    def __init__(self, filename="dx_session.log"):
        self.terminal = sys.stdout
        self.log_file = open(filename, "a", encoding="utf-8")
        self.ansi_escape = re.compile(r'\x1B(?:[@-Z\\-_]|\[[0-?]*[ -/]*[@-~])')

    def write(self, message):
        self.terminal.write(message)
        # Strip ANSI colors before writing to file for clean logs
        clean_msg = self.ansi_escape.sub('', message)
        self.log_file.write(clean_msg)

    def flush(self):
        self.terminal.flush()
        self.log_file.flush()

    def log_debug(self, msg):
        """Writes detailed technical data ONLY to the file, hidden from screen"""
        ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        self.log_file.write(f"[DEBUG][{ts}] {msg}\n")
        self.log_file.flush()

# Initialize Global Logger
logger = None 

def log_proc(msg, color=C_BASE, debug_only=False):
    ts = datetime.now().strftime("%H:%M:%S")
    formatted_msg = f"{C_BASE}[{ts}]{ENDC} {color}{msg}{ENDC}"
    
    if debug_only:
        if logger: logger.log_debug(msg)
    else:
        print(formatted_msg)

# ==============================================================================
# [ 🛰️ ENGINE B: PURE-NAME MATRIX PARSER - VERSION 15.5 ]
# ==============================================================================
def parse_mux_channels(url, save_path, freq_label):
    try:
        from curl_cffi import requests
        from bs4 import BeautifulSoup
        
        res = requests.get(url, impersonate="chrome", timeout=15)
        soup = BeautifulSoup(res.content, 'html.parser')
        
        matrix_buckets = {}
        current_plp, current_isi, current_pid = "0", "0", "4096"
        
        # Comprehensive noise filter
        junk_keywords = ["ROLL-OFF", "FOOTPRINT", "C BAND", "KU BAND", "DVB-S", "CLEAR", "MPEG", "HEVC", "DBW", "INDEX", "VERIFIED"]

        for el in soup.find_all(['div', 'tr']):
            el_text = el.get_text(" ", strip=True).upper()

            # --- 1. HEADER TRACKING ---
            if el.name == 'div':
                plp_m = re.search(r'PLP\s*(\d+)', el_text)
                isi_m = re.search(r'STREAM\s*(\d+)', el_text)
                pid_m = re.search(r'PID\s*(\d+)', el_text)
                if plp_m: current_plp = plp_m.group(1)
                if isi_m: current_isi = isi_m.group(1)
                if pid_m: current_pid = pid_m.group(1)
                continue 

            # --- 2. CHANNEL ROW EXTRACTION ---
            tds = el.find_all('td')
            if len(tds) < 3: continue

            # Clean Name Extraction (No technical suffixes)
            raw_name = tds[2].get_text(strip=True)
            if not raw_name or any(jk in raw_name.upper() for jk in junk_keywords) or "," in raw_name:
                continue

            # Strict numeric SID check
            sid_raw = tds[0].get_text(strip=True)
            if not re.match(r'^\d+$', sid_raw): continue
            
            # Determine Radio/TV
            link = tds[2].find('a', href=True)
            ch_type = "2" if link and "radiochannels" in link['href'] else "1"
            
            # Identify the Bucket
            bucket_id = f"PLP{current_plp}PID{current_pid}_ISI{current_isi}"
            if bucket_id not in matrix_buckets:
                matrix_buckets[bucket_id] = []
            
            # SAVE ONLY THE PURE NAME TO THE CSV LIST
            matrix_buckets[bucket_id].append([sid_raw, raw_name, ch_type])

        # --- 3. SAVE AND DISPLAY (v15.7 Precision Fixed) ---
        if matrix_buckets:
            # Extract Frequency Label (e.g., 3732L40410)
            clean_prefix = re.match(r'(\d+[LRHV]\d+)', freq_label).group(1)
            output_dir = os.path.dirname(save_path)
            total_services = 0

            for bucket, channels in matrix_buckets.items():
                # --- CONDITIONAL ISI FILENAME LOGIC ---
                h_plp = re.search(r'PLP(\d+)', bucket).group(1)
                h_isi = re.search(r'ISI(\d+)', bucket).group(1)
                h_pid = re.search(r'PID(\d+)', bucket).group(1)
                
                # Only include _ISI if it's a Multistream transponder (ISI > 0)
                isi_prefix = f"_ISI{h_isi}" if h_isi != "0" else ""
                specific_filename = f"{clean_prefix}PLP{h_plp}PID{h_pid}{isi_prefix}.csv"
                final_path = os.path.join(output_dir, specific_filename)
                
                with open(final_path, 'w', newline='', encoding='utf-8') as f:
                    writer = csv.writer(f)
                    writer.writerows(channels)
                
                # --- ALIGNMENT MATH ---
                # Column 1 (SID): 10 chars
                # Column 2 (NAME): 45 chars
                # Column 3 (TYPE): 10 chars
                
                h_plp = re.search(r'PLP(\d+)', bucket).group(1)
                h_isi = re.search(r'ISI(\d+)', bucket).group(1)
                
                # We build the string and tell Python to pad it to exactly 43 chars 
                # to leave 1 space of breathing room on each side (Total 45)
                header_content = f"SERVICE NAME (Matrix: {h_plp}/{h_isi})"
                
                print(f"\n      {C_VIOLET}┌──────────┬─────────────────────────────────────────────┬──────────┐{ENDC}")
                # The :<43 ensures the border never moves regardless of the numbers in (0/171)
                print(f"      {C_VIOLET}│{ENDC} SID      {C_VIOLET}│{ENDC} {header_content:<43} {C_VIOLET}│{ENDC} TYPE     {C_VIOLET}│{ENDC}")
                print(f"      {C_VIOLET}├──────────┼─────────────────────────────────────────────┼──────────┤{ENDC}")
                
                for c in channels:
                    c_type = "TV" if c[2]=="1" else "Radio"
                    clean_n = c[1][:43] # Limit name length to prevent overflow
                    print(f"      {C_VIOLET}│{ENDC} {c[0]:<8} {C_VIOLET}│{ENDC} {clean_n:<43} {C_VIOLET}│{ENDC} {c_type:<8} {C_VIOLET}│{ENDC}")
                
                print(f"      {C_VIOLET}└──────────┴─────────────────────────────────────────────┴──────────┘{ENDC}")
                print(f"      {C_LIME}└─► Saved: {specific_filename} | Total: {len(channels)} services{ENDC}")
                total_services += len(channels)

            return total_services

        return 0

    except Exception as e:
        log_proc(f"DEBUG: Matrix Error: {e}", debug_only=True)
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

        # UI DIALOGUE
        print(f"\n{C_VIOLET}┌──[ BAND CONFIGURATION ]────────────────────────────────────────────────┐{ENDC}")
        print(f"{C_VIOLET}│{ENDC}  Target: {C_GOLD}{sat_slug:<62}{ENDC}{C_VIOLET}│{ENDC}")
        print(f"{C_VIOLET}│{ENDC}  Sat Degree: {C_SKY}{sat_deg}° {sat_dir:<52}{ENDC}{C_VIOLET}│{ENDC}")
        sug_col = C_LIME if auto_suggest_cband else C_BASE
        sug_val = 'C-BAND' if auto_suggest_cband else 'KU-BAND'
        print(f"{C_VIOLET}│{ENDC}  Auto-Detection Suggestion: {sug_col}{sug_val:<43}{ENDC}{C_VIOLET}│{ENDC}")
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
        print(f"\n{C_GOLD}╔═{ '═'*84 }═╗\n║ {BOLD}{C_SKY}SATELLITE POSITION:{ENDC} {sat_deg}°{sat_dir:<10} {BOLD}{C_SKY}TARGET:{ENDC} {sat_slug:<40} ║\n╚═{ '═'*84 }═╝{ENDC}")

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

            # Add this to see which Muxes are being evaluated in the log
            log_proc(f"DEBUG: Evaluating potential T2-MI candidate: {f_v} {p_r}", debug_only=True)

            # STAGE 3: Recursive T2-MI Validation & Extraction (v13.8 Forensic Mode)
            try:
                log_proc(f"DEBUG: [REQ] Requesting Mux Data -> {mux_url}", debug_only=True)
                
                req_start = time.time()
                mux_res = requests.get(mux_url, impersonate="chrome", timeout=12)
                latency = (time.time() - req_start) * 1000
                
                log_proc(f"DEBUG: [RES] HTTP {mux_res.status_code} | Latency: {latency:.2f}ms | Size: {len(mux_res.content)} bytes", debug_only=True)
                
                if mux_res.status_code != 200:
                    log_proc(f"DEBUG: [FAIL] Skipping due to HTTP Error {mux_res.status_code}", debug_only=True)
                    continue

                mux_soup = BeautifulSoup(mux_res.text, 'html.parser')
                mux_text = mux_soup.get_text().upper()
                
                # --- Forensic Logic Tracking ---
                is_t2mi = "PLP" in mux_text
                is_vidi = "VIDI TV" in mux_text and "PLP" in mux_text
                
                log_proc(f"DEBUG: [LOGIC] PLP_Found={is_t2mi} | VidiTV_Found={is_vidi}", debug_only=True)

                if not (is_t2mi or is_vidi):
                    log_proc(f"DEBUG: [FILTER] Frequency {f_v} {p_r} rejected: No T2-MI/PLP markers detected.", debug_only=True)
                    continue

                # --- Deep Regex Extraction & Validation (v14.0 Multi-PLP Fix) ---
                # Use findall to capture EVERY instance of PLP and PID on the page
                plp_matches = re.findall(r'PLP\s*(\d+)', mux_text)
                pid_matches = re.findall(r'PID\s*(\d+)', mux_text)
                sr_m  = re.search(r'SR-FEC:.*?(\d+)', mux_text)
                nid_m = re.search(r'NID\s*:\s*(\d+)', mux_text) # Hidden detail
                tid_m = re.search(r'TID\s*:\s*(\d+)', mux_text) # Hidden detail
                
                # Sort and combine multiple matches into a single hyphenated string (e.g., "0-2-5")
                plp_id = "-".join(sorted(set(plp_matches), key=int)) if plp_matches else "0"
                pid_id = "-".join(sorted(set(pid_matches), key=int)) if pid_matches else "4096"
                
                sr     = sr_m.group(1)  if sr_m  else "0"
                nid    = nid_m.group(1) if nid_m else "N/A"
                tid    = tid_m.group(1) if tid_m else "N/A"

                log_proc(f"DEBUG: [EXTRACT] PLP:{plp_id} | PID:{pid_id} | SR:{sr} | NID:{nid} | TID:{tid}", debug_only=True)

                if int(sr) < 1000: 
                    log_proc(f"DEBUG: [ABORT] Invalid SR detected ({sr}). Frequency discarded.", debug_only=True)
                    continue

                tp_id = f"{f_v}{p_r}{sr}"
                if tp_id not in seen_tps:
                    seen_tps.add(tp_id)
                    mod = "8PSK" if "8PSK" in mux_text else "QPSK"
                    hw_pos = round(float(sat_deg) + 0.1, 1) if is_cband_sat else float(sat_deg)
                    p_map = {"H":"0","V":"1","L":"2","R":"3"}

                    log_proc(f"DEBUG: [SUCCESS] Verified T2-MI Mux: {f_v} {p_r} {sr} {mod}", debug_only=True)

                    transponders_data.append({
                        "f_v": f_v, "p_r": p_r, "sr": sr, "mod": mod, "mux_url": mux_url,
                        "file_label": f"{f_v}{p_r}{sr}PLP{plp_id}PID{pid_id}",
                        "csv_row": [f_v, p_map.get(p_r,"0"), sr, f"{hw_pos:.1f}", sat_dir, "2", "9", "1", "1", "2" if mod=="8PSK" else "1", "0", "2", mux_url]
                    })
                else:
                    log_proc(f"DEBUG: [DUPLICATE] Frequency {tp_id} already in stack. Skipping.", debug_only=True)

            except Exception as e:
                log_proc(f"DEBUG: [CRITICAL ERROR] Exception in Stage 3: {str(e)}", debug_only=True)
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

    # NEW: Log File Option
    enable_log = input(f"{C_GOLD}❓ Enable detailed session logging to file? (y/n): {ENDC}").lower()
    if enable_log == 'y':
        log_name = f"DX_LOG_{datetime.now().strftime('%Y%m%d_%H%M%S')}.log"
        logger = MasterLogger(log_name)
        sys.stdout = logger # Redirects all prints to the logger
        log_proc(f"Session started. Outputting to {log_name}", C_LIME)

    print_banner()
    
    # Restore All Helper Texts (Locked 80-Character Frame)
    print(f"{C_BASE}┌──────────────────────────────────────────────────────────────────────────┐{ENDC}")
    print(f"{C_BASE}│{ENDC}  {BOLD}{C_SKY}RECURSIVE DEEP-SCAN SYSTEM v12.4{ENDC}                                        {C_BASE}│{ENDC}")
    print(f"{C_BASE}│{ENDC}                                                                          {C_BASE}│{ENDC}")
    print(f"{C_BASE}│{ENDC}  {C_LIME}Instructions:{ENDC}                                                           {C_BASE}│{ENDC}")
    print(f"{C_BASE}│{ENDC}  • Paste your LyngSat URLs line by line.                                 {C_BASE}│{ENDC}")
    print(f"{C_BASE}│{ENDC}  • Press {BOLD}ENTER{ENDC} on an empty line to trigger the batch extraction.         {C_BASE}│{ENDC}")
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
        
        # FINAL GLOBAL SUMMARY (CALIBRATED 80-CHAR ALIGNMENT)
        line_t = "█" + "▀" * 78 + "█"
        line_b = "█" + "▄" * 78 + "█"
        print(f"\n{C_GOLD}{line_t}{ENDC}")
        
        # Header: Manual space padding to reach column 78 visually
        print(f"{C_GOLD}█ {C_SKY}GLOBAL DX EXECUTION SUMMARY{ENDC}{' ':<50}{C_GOLD}█{ENDC}")
        
        # Content lines: Use :<89 to compensate for the ~11 hidden BOLD/ENDC characters
        print(f"{C_GOLD}█{ENDC} {C_BASE}├─ Total Satellites Processed: {BOLD}{len(urls):<10}{ENDC}{' ':<36}{C_GOLD}█{ENDC}")
        print(f"{C_GOLD}█{ENDC} {C_BASE}├─ Total Unique Transponders:  {BOLD}{global_total_tps:<10}{ENDC}{' ':<36}{C_GOLD}█{ENDC}")
        print(f"{C_GOLD}█{ENDC} {C_BASE}├─ Total Channels Mapped:      {BOLD}{global_total_channels:<10}{ENDC}{' ':<36}{C_GOLD}█{ENDC}")
        print(f"{C_GOLD}█{ENDC} {C_BASE}└─ Operation Time:             {BOLD}{duration:<7.2f}s{ENDC}{' ':<38}{C_GOLD}█{ENDC}")
        
        print(f"{C_GOLD}{line_b}{ENDC}\n")
