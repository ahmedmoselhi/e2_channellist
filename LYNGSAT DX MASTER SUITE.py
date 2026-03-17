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
# [ 🛰️ ENGINE B: RECURSIVE MUX PARSER ]
# ==============================================================================
def parse_mux_channels(url, save_path, freq_label):
    try:
        from curl_cffi import requests
        from bs4 import BeautifulSoup
        
        res = requests.get(url, impersonate="chrome", timeout=15)
        if res.status_code != 200:
            log_proc(f"Failed to fetch {url} with status code {res.status_code}", C_CRIMSON)
            return 0
        soup = BeautifulSoup(res.content, 'html.parser')
        
        # Find the channel list table by class
        mux_table = soup.find('table', class_='mux-table')
        if not mux_table:
            log_proc("No 'mux-table' found on page", C_CRIMSON)
            return 0
        
        rows = mux_table.find_all('tr')
        if len(rows) <= 1:
            log_proc("No data rows found in 'mux-table'", C_CRIMSON)
            return 0

        ch_list = []
        for row in rows[1:]:  # Skip header
            tds = row.find_all('td')
            if len(tds) < 12:
                continue  # Skip malformed rows
            
            sid_text = tds[0].get_text(strip=True)
            channel_name = tds[2].get_text(strip=True)
            # ---------------------------------------------------------
            # NEW FILTER: Skip the "Channel Name" header row
            # ---------------------------------------------------------
            if channel_name.lower() == "channel name":
                continue
            video_info = tds[4].get_text(strip=True)
            link = tds[2].find('a', href=True)
            ch_type = "RADIO" if link and "radiochannels" in link['href'] else "TV"
            
            # Extract SID, ensure it's a number
            sid_match = re.search(r'\d+', sid_text)
            sid = sid_match.group() if sid_match else "0"
            
            # Append data
            ch_data = [sid, channel_name, "1" if ch_type=="TV" else "2"]
            if ch_data not in ch_list:
                ch_list.append(ch_data)

        # Print the table
        print(f"\n      {C_VIOLET}┌{'─'*10}┬{'─'*45}┬{'─'*10}┐{ENDC}")
        print(f"      {C_VIOLET}│ {C_SKY}{'SID':<8} {C_VIOLET}│ {C_SKY}{'CHANNEL NAME':<43} {C_VIOLET}│ {C_SKY}{'TYPE':<8} {C_VIOLET}│{ENDC}")
        print(f"      {C_VIOLET}├{'─'*10}┼{'─'*45}┼{'─'*10}┤{ENDC}")
        for ch in ch_list:
            print(f"      {C_VIOLET}│{ENDC} {C_GOLD}{ch[0]:<8} {C_VIOLET}│{ENDC} {C_BASE}{ch[1][:43]:<43} {C_VIOLET}│{ENDC} {C_LIME}{'TV' if ch[2]=='1' else 'RADIO':<8} {C_VIOLET}│{ENDC}")
        print(f"      {C_VIOLET}└{'─'*10}┴{'─'*45}┴{'─'*10}┘{ENDC}")
        print(f"  {C_LIME}└─► Services extracted: {BOLD}{len(ch_list)}{ENDC}")

        # Save to CSV
        fname = os.path.join(save_path, f"{freq_label}.csv")
        with open(fname, 'w', newline='', encoding='utf-8') as f:
            writer = csv.writer(f)
            writer.writerows(ch_list)

        return len(ch_list)

    except Exception as e:
        log_proc(f"Error in parse_mux_channels: {e}", C_CRIMSON)
        return 0

# ==============================================================================
# [ 🛰️ ENGINE A: DEEP SATELLITE SCANNER ]
# ==============================================================================
def deep_scan_satellite(url):
    global global_total_channels, global_total_tps
    try:
        from curl_cffi import requests
        from bs4 import BeautifulSoup
        import re
        import os
        import csv

        log_proc(f"Establishing Uplink: {url}", C_GOLD)
        res = requests.get(url, impersonate="chrome", timeout=15)
        html_source = res.text

        # Parse HTML with BeautifulSoup
        soup = BeautifulSoup(html_source, 'html.parser')

        # ---------------------------------------------------------
        # FIX 1: Broaden the early-exit keyword detection.
        # Removed "PID" to prevent false positives from VPID/APID headers.
        # Added "Multistream" and "PLS" which LyngSat frequently uses.
        # ---------------------------------------------------------
        t2mi_keywords = ["T2-MI", "T2MI", "PLP", "Multistream", "PLS"]
        
        tds = soup.find_all('td')
        t2mi_in_tds = any(kw in td.get_text() for td in tds for kw in t2mi_keywords)
        t2mi_in_source = any(kw in html_source for kw in t2mi_keywords)

        # Proceed only if multistream or T2-MI related keywords are detected
        if not (t2mi_in_tds or t2mi_in_source):
            # No relevant keywords found; skip processing EFFICIENTLY
            return

        # Extract satellite position from the <title> or other marker
        title = soup.title.string if soup.title else ""
        sat_m = re.search(r'(\d+\.?\d*)\s?°?\s?([EW])', title)
        if not sat_m:
            return

        sat_deg, sat_dir = float(sat_m.group(1)), sat_m.group(2)
        sat_slug = url.split('/')[-1].replace(".html", "")
        sat_name_digits = re.findall(r'\d+', sat_slug)

        rows = soup.find_all('tr')

        # --- ENHANCED INTERACTIVE BAND DETERMINATION ---
        # 1. Advanced Automated Suggestion Logic (Spectrum & Hardware Weighting)
        auto_suggest_cband = False
        cband_weight = 0
        kuband_weight = 0

        for r in rows:
            first_td = r.find('td')
            if first_td:
                td_text = first_td.get_text(strip=True).upper()
                
                # Strict Regex: Matches EXACTLY 4-5 digits followed by L, R, H, or V
                # Anchored to the start (^) to completely eliminate PID, SID, or Date false positives
                freq_match = re.search(r'^(\d{4,5})\s*([LRHV])', td_text)
                
                if freq_match:
                    freq_val = int(freq_match.group(1))
                    pol_val = freq_match.group(2)
                    
                    # Factor A: C-Band Spectrum (typically 3000 MHz - 4999 MHz)
                    if 3000 <= freq_val <= 4999:
                        cband_weight += 2  # Strong C-Band frequency indicator
                        if pol_val in ['L', 'R']:
                            cband_weight += 1  # Hardware confirms Circular Pol (MFV pass)
                            
                    # Factor B: Ku-Band Spectrum (typically > 10000 MHz)
                    elif freq_val >= 10000:
                        kuband_weight += 2  # Strong Ku-Band frequency indicator
                        if pol_val in ['H', 'V']:
                            kuband_weight += 1  # Hardware confirms Linear Pol

        # Evaluate the weights to formulate the smartest suggestion
        if cband_weight > 0 and cband_weight >= kuband_weight:
            auto_suggest_cband = True
        elif cband_weight > 0 and kuband_weight > cband_weight:
            # Hybrid Payload (e.g., mostly Ku but has some C-Band)
            # We suggest C-BAND defensively so you are prompted to acknowledge the +0.1 offset
            auto_suggest_cband = True

        # 2. Enhanced UI Dialogue Box
        print(f"\n{C_VIOLET}┌──[ BAND CONFIGURATION ]────────────────────────────────────────────────┐{ENDC}")
        print(f"{C_VIOLET}│{ENDC}  Target: {C_GOLD}{sat_slug:<55}{ENDC}{C_VIOLET}│{ENDC}")
        print(f"{C_VIOLET}│{ENDC}  Sat Degree: {C_SKY}{sat_deg}° {sat_dir:<46}{ENDC}{C_VIOLET}│{ENDC}")
        print(f"{C_VIOLET}│{ENDC}  Auto-Detection Suggestion: {C_LIME if auto_suggest_cband else C_BASE}{'C-BAND' if auto_suggest_cband else 'KU-BAND':<35}{ENDC}{C_VIOLET}│{ENDC}")
        print(f"{C_VIOLET}└────────────────────────────────────────────────────────────────────────┘{ENDC}")
        
        # 3. User Decision Input (Strict 10-Second Non-Blocking Auto-Continue)
        prompt_text = f"{C_SKY}❓ Treat this satellite as C-BAND? (y/n) [Auto-resolving in 10s]: {ENDC}"
        print(prompt_text, end='', flush=True)

        user_choice = None
        start_time = time.time()
        timeout = 10

        # High-performance non-blocking input loop
        while (time.time() - start_time) < timeout:
            if sys.platform == 'win32':
                if msvcrt.kbhit():
                    user_choice = sys.stdin.readline().strip().lower()
                    break
            else:
                # Linux/macOS non-blocking check
                ready, _, _ = select.select([sys.stdin], [], [], 0.1)
                if ready:
                    user_choice = sys.stdin.readline().strip().lower()
                    break
            time.sleep(0.1) # Prevents CPU spiking

        # 4. Final Determination Logic
        if user_choice is None:
            # TRUE AUTO-CONTINUE: This triggers without needing any key press
            print(f"\n  {C_GOLD}└─► ⏳ Timeout reached. System Proceeding with: {BOLD}{'C-BAND' if auto_suggest_cband else 'KU-BAND'}{ENDC}")
            is_cband_sat = auto_suggest_cband
        else:
            if user_choice in ['y', 'yes']:
                is_cband_sat = True
                print(f"  {C_LIME}└─► User Override: C-BAND Selected.{ENDC}")
            elif user_choice in ['n', 'no']:
                is_cband_sat = False
                print(f"  {C_SKY}└─► User Override: KU-BAND Selected.{ENDC}")
            else:
                is_cband_sat = auto_suggest_cband
                print(f"  {C_BASE}└─► Using Auto-Detection: {'C-BAND' if auto_suggest_cband else 'KU-BAND'}{ENDC}")

        # Setup directories and labels
        f_dir, c_dir, pos_label = setup_storage(sat_deg, sat_dir, is_cband_sat)

        # Preserved UI Graphics
        print(f"\n{C_GOLD}╔═{ '═'*84 }═╗")
        print(f"║ {BOLD}{C_SKY}SATELLITE POSITION:{ENDC} {sat_deg}°{sat_dir:<10} {BOLD}{C_SKY}TARGET:{ENDC} {sat_slug:<44} ║")
        print(f"╚═{ '═'*84 }═╝{ENDC}")

        transponders_data = []
        seen_tps = set()

        # Loop through each row for T2-MI / Multistream detection
        for row in rows:
            row_text = row.get_text(" ", strip=True)
            
            # ---------------------------------------------------------
            # FIX 2: Check for any Multistream/T2-MI keyword in the row
            # instead of strictly requiring "T2-MI".
            # ---------------------------------------------------------
            if any(kw in row_text for kw in t2mi_keywords):
                
                # Extract frequency and polarization info
                fm = re.search(r'(\d{4,5})\s*([LRHV])', row_text)
                if not fm:
                    continue
                f_v, p_r = fm.group(1), fm.group(2)

                # Fetch mux content
                # ---------------------------------------------------------
                # DYNAMIC MUX URL ENGINE (Fixed for Express-AM7 / 40.0E)
                # ---------------------------------------------------------
                if sat_deg == 16.0:
                    mux_url = f"https://www.lyngsat.com/muxes/Eutelsat-16A_Europe-B_{f_v}-{p_r}.html"
                else:
                    # Look for the actual link in the row to find the Footprint name (e.g., C-Fixed)
                    beam_link = row.find('a', href=re.compile(r'/muxes/'))
                    if beam_link:
                        # Extracts the full filename from LyngSat's own link
                        mux_filename = beam_link['href'].split('/')[-1]
                        mux_url = f"https://www.lyngsat.com/muxes/{mux_filename}"
                    else:
                        # Fallback for unexpected formats
                        mux_url = f"https://www.lyngsat.com/muxes/{sat_slug}_beam_{f_v}-{p_r}.html"

                mux_content = ""
                try:
                    mux_res = requests.get(mux_url, impersonate="chrome", timeout=10)
                    mux_content = mux_res.text
                except:
                    mux_content = ""

                # RELAXED T2-MI VERIFICATION: Strict for 16.0E, Flexible for others
                is_verified_t2mi = False
                if sat_deg == 16.0:
                    if "PLP" in mux_content and "PID" in mux_content:
                        is_verified_t2mi = True
                else:
                    # For Express-AM7 and others, if we found it via the T2-MI keyword, it's valid
                    if any(kw in mux_content for kw in ["PLP", "T2-MI", "T2MI", "Stream"]):
                        is_verified_t2mi = True
                    elif any(kw in row_text for kw in ["T2-MI", "T2MI", "Multistream"]):
                        is_verified_t2mi = True

                if is_verified_t2mi:
                    sr = "0"
                    sr_m = re.search(r'SR\s*(\d+)', row_text)
                    if sr_m:
                        sr = sr_m.group(1)
                    else:
                        # Improved SR hunt: look for numbers between 1000 and 45000 
                        # that aren't the frequency or the year.
                        potential_srs = re.findall(r'\b(\d{4,5})\b', row_text)
                        for s in potential_srs:
                            if s == f_v or s in ["2024", "2025", "2026"]: continue
                            if 1000 <= int(s) <= 45000:
                                sr = s
                                break

                    # Filter out invalid SRs
                    if sr == "0" or int(sr) < 1000:
                        continue

                    # Extract PLP and PID from the deep-scan mux content
                    plp_id = "0"
                    pid_id = "0"
                    plp_m = re.search(r'PLP\s*(\d+)', mux_content)
                    pid_m = re.search(r'PID\s*(\d+)', mux_content)
                    if plp_m: plp_id = plp_m.group(1)
                    if pid_m: pid_id = pid_m.group(1)
                    
                    # Construct the new naming convention
                    file_label = f"{f_v}{p_r}{sr}PLP{plp_id}PID{pid_id}"

                    tp_id = f"{f_v}{p_r}{sr}"
                    if tp_id not in seen_tps:
                        seen_tps.add(tp_id)
                        mod = "8PSK" if "8PSK" in row_text else "QPSK"

                        # Explicitly index C-Band satellites by +0.1 for tracking
                        if is_cband_sat:
                            hw_pos = round(float(sat_deg) + 0.1, 1)
                        else:
                            hw_pos = float(sat_deg)
                        p_map = {"H":"0","V":"1","L":"2","R":"3"}

                        transponders_data.append({
                            "f_v": f_v,
                            "p_r": p_r,
                            "sr": sr,
                            "mod": mod,
                            "mux_url": mux_url,
                            "file_label": file_label,  # <--- ENSURE THIS IS ADDED
                            "csv_row": [f_v, p_map.get(p_r,"0"), sr, f"{hw_pos:.1f}", sat_dir, "2", "9", "1", "1", "2" if mod=="8PSK" else "1", "0", "2", mux_url]
                        })

        # Update total TPS
        global_total_tps += len(transponders_data)

        # Preserved UI Graphics - Frequency Table Summary
        print(f"\n{C_TEAL}┌{'─'*10}┬{'─'*8}┬{'─'*10}┬{'─'*10}┬{'─'*42}┐{ENDC}")
        print(f"{C_TEAL}│ {C_SKY}{'FREQ':<8} │ {C_SKY}{'POL':<6} │ {C_SKY}{'SR':<8} │ {C_SKY}{'MOD':<8} │ {C_SKY}{'MUX URL / BEAM REFERENCE':<40} │{ENDC}")
        print(f"{C_TEAL}├{'─'*10}┼{'─'*8}┼{'─'*10}┼{'─'*10}┼{'─'*42}┤{ENDC}")

        for tp in transponders_data:
            slug_disp = tp['mux_url'].split('/')[-1][:40]
            print(f"{C_TEAL}│{ENDC} {C_LIME}{tp['f_v']:<8} {C_TEAL}│{ENDC} {C_BASE}{tp['p_r']:<6} {C_TEAL}│{ENDC} {C_GOLD}{tp['sr']:<8} {C_TEAL}│{ENDC} {C_VIOLET}{tp['mod']:<8} {C_TEAL}│{ENDC} {C_BASE}{slug_disp:<40} {C_TEAL}│{ENDC}")

        print(f"{C_TEAL}└{'─'*10}┴{'─'*8}┴{'─'*10}┴{'─'*10}┴{'─'*42}┘{ENDC}")
        print(f"  {C_LIME}└─► Total Verified T2-MI Frequencies Discovered: {BOLD}{len(transponders_data)}{ENDC}")

        # Loop through each transponder to fetch and parse services
        sat_services_total = 0
        csv_data = []

        for tp in transponders_data:
            print(f"\n{C_TEAL}▶ {C_SKY}Drill-Down: Fetching services for {ENDC}{BOLD}{C_LIME}{tp['f_v']} {tp['p_r']}{ENDC} {C_SKY}(SR: {tp['sr']}){ENDC}")
            tp_channels = parse_mux_channels(tp['mux_url'], c_dir, tp['file_label'])
            sat_services_total += tp_channels
            global_total_channels += tp_channels
            csv_data.append(tp['csv_row'])

        # Save CSV
        out_file = os.path.join(f_dir, f"f{pos_label}.csv")
        with open(out_file, 'w', newline='', encoding='utf-8') as f:
            writer = csv.writer(f)
            writer.writerow(["Freq", "Pol", "SR", "Pos", "Dir", "Inv", "FEC", "Sys", "Mod", "RO", "Pilot", "MuxURL"])
            writer.writerows(csv_data)

    except Exception as e:
        log_proc(f"Error: {e}", C_CRIMSON)

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
