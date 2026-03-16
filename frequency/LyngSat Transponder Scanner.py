import os
import sys
import subprocess
import re
import csv
import time
from datetime import datetime

# ==============================================================================
# [ 🎨 MASTER GRAPHICS ENGINE - PRESERVING V2.2 STYLING ]
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
    banner = f"""
{C_GOLD}█▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀█
█  {C_SKY}📡  {BOLD}LYNGSAT T2-MI TRANSPONDER SCANNER{ENDC}{C_GOLD}  |  {C_LIME}VERSION 2.3{ENDC}{C_GOLD}  |  {C_VIOLET}STRICT-FILTER{ENDC}{C_GOLD} █
█▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄█{ENDC}
    """
    print(banner)

def draw_header(label):
    print(f"\n{C_GOLD}╔═{ '—' * (len(label) + 2) }═╗")
    print(f"║ {BOLD}{C_SKY}{label}{ENDC}{C_GOLD} ║")
    print(f"╚═{ '—' * (len(label) + 2) }═╝{ENDC}")

# ==============================================================================
# [ ⚙️ STEP 1: DEPENDENCY ARCHITECT ]
# ==============================================================================
def install_dependencies():
    packages = ["curl_cffi", "beautifulsoup4"]
    for package in packages:
        try:
            __import__("curl_cffi" if package == "curl_cffi" else "bs4")
        except ImportError:
            subprocess.check_call([sys.executable, "-m", "pip", "install", package, "--break-system-packages", "--user", "--quiet"])

install_dependencies()
from curl_cffi import requests
from bs4 import BeautifulSoup

# ==============================================================================
# [ 🛰️ STEP 2: STRICT EXTRACTION ENGINE ]
# ==============================================================================
def scan_satellite_for_t2mi(url):
    try:
        response = requests.get(url, impersonate="chrome", timeout=20)
        response.raise_for_status()
        soup = BeautifulSoup(response.content, 'html.parser')
        
        # --- SAT IDENTIFICATION ---
        sat_base_deg = 0.0
        sat_direction = "E"
        title_text = soup.title.string if soup.title else ""
        sat_m = re.search(r'(\d+\.?\d*)\s?°?\s?([EW])', title_text)
        if sat_m:
            sat_base_deg = float(sat_m.group(1))
            sat_direction = sat_m.group(2)
        
        output_file = f"f{sat_base_deg:.1f}{sat_direction}.csv"
        csv_header = ["Freq", "Pol", "SR", "Pos", "Dir", "Inv", "FEC", "Sys", "Mod", "RO", "Pilot"]
        
        transponders = []
        rows = soup.find_all('tr')
        current_years = [str(y) for y in range(2020, 2032)]
        
        pol_names = {"0": "HORIZ", "1": "VERT", "2": "L-CIRC", "3": "R-CIRC"}
        mod_names = {"1": "QPSK", "2": "8PSK", "3": "16APSK", "4": "32APSK"}

        draw_header(f"SCANNING: {sat_base_deg}°{sat_direction}")
        print(f"{C_TEAL}{BOLD}{'ID':<4} | {'FREQ':<8} | {'POLARITY':<10} | {'SR (kHz)':<10} | {'MODULATION':<12} | {'STATUS'}{ENDC}")
        print(f"{C_BASE}{'—' * 70}{ENDC}")

        for row in rows:
            tds = row.find_all('td')
            # Double-Lock: Ensure the row contains the necessary technical cells
            if len(tds) < 6: continue
            
            # Target technical columns (System/Mux info) to avoid false positives
            sys_info = tds[1].get_text().upper() if len(tds) > 1 else ""
            mux_info = tds[3].get_text().upper() if len(tds) > 3 else ""
            
            # Check for T2-MI in the specific technical columns
            if "T2-MI" in sys_info or "T2-MI" in mux_info:
                row_content = " ".join([td.get_text(separator=" ", strip=True) for td in tds])
                
                # Extract Frequency and Polarity
                freq_m = re.search(r'(\d{4,5})\s*([LRHV])', row_content)
                if not freq_m: continue
                freq_val = int(freq_m.group(1))
                pol_raw = freq_m.group(2)
                pol_map = {"H": "0", "V": "1", "L": "2", "R": "3"}
                polarization = pol_map.get(pol_raw, "0")

                # Symbol Rate Extraction
                sr = "0"
                sr_m = re.search(r'SR\s*(\d+)', row_content)
                if sr_m:
                    sr = sr_m.group(1)
                else:
                    candidates = re.findall(r'\b(\d{4,5})\b', row_content)
                    for val in candidates:
                        if int(val) != freq_val and val not in current_years:
                            sr = val
                            break

                current_pos = sat_base_deg + 0.1 if freq_val < 5000 else sat_base_deg
                
                # Modulation Logic (DVB-S2 specific)
                modulation = "1"
                if "8PSK" in row_content: modulation = "2"
                elif "16APSK" in row_content: modulation = "3"
                elif "32APSK" in row_content: modulation = "4"

                numeric_line = [freq_val, polarization, sr, f"{current_pos:.1f}", sat_direction, "2", "9", "1", modulation, "0", "2"]
                
                if numeric_line not in transponders:
                    transponders.append(numeric_line)
                    # Updated Dashboard Logging
                    idx = len(transponders)
                    p_name = pol_names.get(polarization, "N/A")
                    m_name = mod_names.get(modulation, "N/A")
                    print(f"{C_BASE}{idx:02}{ENDC}   | {C_LIME}{freq_val:<8}{ENDC} | {C_SKY}{p_name:<10}{ENDC} | {C_GOLD}{sr:<10}{ENDC} | {C_VIOLET}{m_name:<12}{ENDC} | {C_LIME}EXTRACTED{ENDC}")

        if transponders:
            with open(output_file, 'w', newline='', encoding='utf-8') as f:
                writer = csv.writer(f)
                writer.writerow(csv_header)
                writer.writerows(transponders)
            
            print(f"{C_BASE}{'—' * 70}{ENDC}")
            print(f"{C_LIME}█ STATUS: Success{ENDC}")
            print(f"{C_LIME}█ TOTAL TP EXTRACTED: {BOLD}{len(transponders)}{ENDC}")
            print(f"{C_LIME}█ FILE GENERATED: {C_GOLD}{output_file}{ENDC}")
        else:
            print(f"\n{C_CRIMSON}█ STATUS: No verified T2-MI frequencies found.{ENDC}")

    except Exception as e:
        print(f"\n{C_CRIMSON}[✗] ERROR: {str(e)}{ENDC}")

# ==============================================================================
# [ 🚀 BATCH SYSTEM ]
# ==============================================================================
if __name__ == "__main__":
    os.system('clear' if os.name == 'posix' else 'cls')
    print_banner()
    
    print(f"{C_BASE}┌──────────────────────────────────────────────────────────────────────────┐{ENDC}")
    print(f"{C_BASE}│{ENDC}  {BOLD}STRICT-FILTER BATCH INPUT{ENDC}                                               {C_BASE}│{ENDC}")
    print(f"{C_BASE}│{ENDC}  Paste URLs line by line. Empty line starts the scan.                    {C_BASE}│{ENDC}")
    print(f"{C_BASE}└──────────────────────────────────────────────────────────────────────────┘{ENDC}")
    
    urls = []
    while True:
        entry = input(f"{C_GOLD}📡 SAT URL #{len(urls)+1}:{ENDC} ").strip()
        if not entry: break
        if entry.startswith("http"): urls.append(entry)
        else: print(f"{C_CRIMSON}    [!] Invalid URL.{ENDC}")

    if urls:
        for idx, target in enumerate(urls, 1):
            scan_satellite_for_t2mi(target)
            time.sleep(0.5)
        
        print(f"\n{C_GOLD}█▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀█")
        print(f"█  {C_LIME}BATCH COMPLETE: {len(urls)} Satellites Clean-Scanned.{ENDC}{C_GOLD}                       █")
        print(f"█▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄█{ENDC}\n")
