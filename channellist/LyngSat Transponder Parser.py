import os
import sys
import subprocess
import re
import csv
import time

# ==============================================================================
# [ 🎨 HYPER-ENHANCED GRAPHICS & UI COMPONENTS ]
# ==============================================================================
C_BASE    = "\033[38;5;250m"  # Grey
C_GOLD    = "\033[38;5;220m"  # Gold
C_SKY     = "\033[38;5;117m"  # Sky Blue
C_LIME    = "\033[38;5;121m"  # Lime Green
C_CRIMSON = "\033[38;5;196m"  # Bright Red
C_VIOLET  = "\033[38;5;141m"  # Soft Violet
BOLD      = "\033[1m"
ENDC      = "\033[0m"

def print_banner():
    """Renders a high-impact Unicode banner with versioning."""
    banner = f"""
{C_GOLD}█▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀█
█  {C_SKY}🛰️  {BOLD}LYNGSAT T2-MI ULTIMATE DX GENERATOR{ENDC}{C_GOLD}  |  {C_LIME}VERSION 8.0{ENDC}{C_GOLD}  |  {C_VIOLET}SERIAL-PRO{ENDC}{C_GOLD}   █
█▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄█{ENDC}
    """
    print(banner)

def draw_divider(label=""):
    """Creates a stylized horizontal divider with an optional label."""
    width = 80
    if not label:
        print(f"{C_BASE}─" * width + f"{ENDC}")
    else:
        side_width = (width - len(label) - 4) // 2
        print(f"{C_BASE}─" * side_width + f" {C_GOLD} {label} {ENDC}{C_BASE} " + "─" * side_width + f"{ENDC}")

# ==============================================================================
# [ ⚙️ STEP 1: ENVIRONMENT & DEPENDENCY ARCHITECT ]
# ==============================================================================
def install_dependencies():
    """
    CHOICE: Automated Library Management.
    INSTRUCTION: Ensures curl_cffi and BeautifulSoup4 are available.
    RESULT: Bypasses Ubuntu PEP 668 restrictions via --break-system-packages.
    """
    packages = ["curl_cffi", "beautifulsoup4"]
    for package in packages:
        try:
            module_name = "curl_cffi" if package == "curl_cffi" else "bs4"
            __import__(module_name)
        except ImportError:
            subprocess.check_call([sys.executable, "-m", "pip", "install", 
                                   package, "--break-system-packages", "--user", "--quiet"])

install_dependencies()
from curl_cffi import requests
from bs4 import BeautifulSoup

# ==============================================================================
# [ 🛰️ STEP 2: THE MULTI-PID ENGINE ]
# ==============================================================================
def parse_pro_mux(url):
    try:
        response = requests.get(url, impersonate="chrome", timeout=15)
        response.raise_for_status()
        
        soup = BeautifulSoup(response.content, 'html.parser')
        full_text = soup.get_text()

        # --- PHASE: METADATA EXTRACTION ---
        url_fn = url.split('/')[-1]
        fp = re.search(r'(\d+)-([LRHV])', url_fn)
        freq, pol = (fp.group(1), fp.group(2)) if fp else ("0000", "X")

        sr = "0000"
        sr_m = re.search(r'SR-FEC:[\s\n]*(\d+)', full_text)
        if sr_m: sr = sr_m.group(1)

        # Satellite Position (PRECISION FIX: Ensures 8.0W instead of 8W)
        sat_pos = "0.0E"
        sat_m = re.search(r'(\d+\.?\d*)\s?°?\s?([EW])', full_text)
        if sat_m:
            deg = sat_m.group(1)
            if "." not in deg: deg = f"{deg}.0"
            sat_pos = f"{deg}{sat_m.group(2)}"
        
        print(f"{C_LIME}[+] METADATA:{ENDC} Freq:{freq} | Pol:{pol} | SR:{sr} | Pos:{sat_pos}")

        # --- PHASE: T2-MI STREAM DISCOVERY ---
        stream_headers = soup.find_all(string=re.compile(r'PLP\s*\d+\s*on\s*PID\s*\d+'))
        
        if not stream_headers:
            print(f"{C_CRIMSON}[!] WARNING:{ENDC} No T2-MI streams found for this transponder.")
            return

        for header_text in stream_headers:
            m = re.search(r'PLP\s*(\d+)\s*on\s*PID\s*(\d+)', header_text)
            if not m: continue
            
            plp, pid = m.group(1), m.group(2)
            filename = f"{freq}{pol}{sr}PID{pid}PLP{plp}@{sat_pos}.csv"
            
            draw_divider(f"PID {pid} | PLP {plp}")

            channels = []
            target_table = None
            for sibling in header_text.parent.find_all_next():
                if sibling.name == 'table' and 'mux-table' in sibling.get('class', []):
                    target_table = sibling
                    break
            
            if target_table:
                for row in target_table.find_all('tr'):
                    tds = row.find_all('td')
                    if len(tds) >= 3:
                        sid_raw = tds[0].get_text(strip=True)
                        if sid_raw.isdigit():
                            name_c = tds[2]
                            name = name_c.get_text(strip=True).replace('[', '').replace(']', '')
                            link = name_c.find('a', href=True)
                            # Type determination: Radio=2, TV/Other=1
                            s_type = "2" if link and "radiochannels" in link['href'] else "1"
                            channels.append([sid_raw, name, s_type])

            if channels:
                with open(filename, 'w', newline='', encoding='utf-8') as f:
                    writer = csv.writer(f)
                    writer.writerows(channels)
                print(f"{C_LIME}[✓] EXPORTED:{ENDC} {BOLD}{filename}{ENDC} ({len(channels)} channels)")

    except Exception as e:
        print(f"{C_CRIMSON}[✗] ERROR:{ENDC} {str(e)}")

# ==============================================================================
# [ 🚀 SERIAL INPUT ENTRY POINT ]
# ==============================================================================
if __name__ == "__main__":
    os.system('clear' if os.name == 'posix' else 'cls')
    print_banner()
    
    print(f"{C_SKY}╔══════════════════════════════════════════════════════════════════════════╗{ENDC}")
    print(f"{C_SKY}║{ENDC} {BOLD}SERIAL ENTRY MODE:{ENDC}                                                       {C_SKY}║{ENDC}")
    print(f"{C_SKY}║{ENDC} - Enter each URL one by one and press Enter.                             {C_SKY}║{ENDC}")
    print(f"{C_SKY}║{ENDC} - {BOLD}Press Enter on an empty line to start processing.{ENDC}                      {C_SKY}║{ENDC}")
    print(f"{C_SKY}╚══════════════════════════════════════════════════════════════════════════╝{ENDC}")
    
    urls_to_process = []
    while True:
        count = len(urls_to_process) + 1
        entry = input(f"{C_GOLD}🔗 URL #{count}:{ENDC} ").strip()
        
        if not entry:
            break
            
        if entry.startswith("http"):
            urls_to_process.append(entry)
        else:
            print(f"{C_CRIMSON}[!] Invalid URL format skipped.{ENDC}")

    if not urls_to_process:
        print(f"{C_CRIMSON}[✗] ABORTED: No URLs entered.{ENDC}")
    else:
        draw_divider("BATCH PROCESSING STARTED")
        print(f"{C_VIOLET}[i] HELPER:{ENDC} Processing {len(urls_to_process)} transponders sequentially...")
        
        for index, target in enumerate(urls_to_process, 1):
            print(f"\n{C_BASE}▼ JOB {index}/{len(urls_to_process)}:{ENDC} {target}")
            parse_pro_mux(target)
            time.sleep(1) # Anti-block delay
            
        draw_divider()
        print(f"{C_GOLD}█{C_LIME}  TASK COMPLETE: {len(urls_to_process)} transponders processed successfully. {C_GOLD}█{ENDC}\n")
