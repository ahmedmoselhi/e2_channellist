import os
import sys
import shutil
import time
from prompt_toolkit.completion import PathCompleter
# --- Ensure prompt_toolkit exists ---
try:
    from prompt_toolkit import prompt as pt_prompt
    from prompt_toolkit.history import FileHistory
    from prompt_toolkit.shortcuts import radiolist_dialog
except ImportError:
    print("Installing required module: prompt_toolkit ...")
    import subprocess
    import sys
    subprocess.check_call([
        sys.executable,
        "-m",
        "pip",
        "install",
        "--break-system-packages",
        "prompt_toolkit"
    ])
    from prompt_toolkit import prompt as pt_prompt
    from prompt_toolkit.history import FileHistory
    from prompt_toolkit.shortcuts import radiolist_dialog

class Color:
    BLUE = '\033[94m'
    CYAN = '\033[96m'
    GREEN = '\033[92m'
    YELLOW = '\033[93m'
    RED = '\033[91m'
    BOLD = '\033[1m'
    END = '\033[0m'

def clear_screen():
    os.system('cls' if os.name == 'nt' else 'clear')

def print_header():
    print(f"{Color.BLUE}{Color.BOLD}" + "="*80)
    print(r"""
  _______ ___       __  __ ___   _   _ _   _ _   _ __  __  _   _____ _____ 
 |__   __|__ \     |  \/  |_ _| | | | | | | | | | |  \/  |/ \ |_   _| ____|
    | |     ) |____| |\/| || |  | | | | | | | | | | |\/| / _ \  | | |  _|  
    | |    / /|____| |  | || |  | |_| | |_| | |_| | |  |/ ___ \ | | | |___ 
    |_|   |___|    |_|  |_|___|  \___/ \___/ \___/|_|  /_/   \_\|_| |_____|
                                                                           
               v9.7 - [ THE ENCYCLOPEDIA ARCHITECT ]
    """)
    print("="*80 + f"{Color.END}")

def draw_progress(percent, width=40, task="Processing"):
    filled = int(width * percent / 100)
    bar = "█" * filled + "░" * (width - filled)
    sys.stdout.write(f"\r  {Color.CYAN}{task.ljust(20)}: {Color.BOLD}[{bar}]{Color.END} {percent}%")
    sys.stdout.flush()
    time.sleep(0.01)

def ask(prompt, default=None, help_text="", icon="ℹ"):
    while True:
        print(f"\n{Color.YELLOW}┌── {Color.BOLD}INPUT FIELD{Color.END}{Color.YELLOW} " + "─"*65 + "┐")
        # RESTORED: Full helper documentation with explicit default markers
        full_help = f"{help_text}"
        if default is not None:
            full_help += f"\n[ DEFAULT CHOICE: {default} ] (Press Enter to use default)"
        else:
            full_help += f"\n[ REQUIRED FIELD: Manual entry necessary ]"
            
        for line in full_help.strip().split('\n'):
            print(f"│ {Color.BLUE}{icon} {line.ljust(74)}{Color.END}{Color.YELLOW} │")
        print(f"└" + "─"*78 + "┘" + Color.END)
        prompt_text = f"  {prompt}: "
        val = pt_prompt(prompt_text, history=history).strip()
        if val == "" and default is not None: return default
        if val != "": return val
        print(f"  {Color.RED}⚠ ALERT: Value required for database integrity.{Color.END}")

def choose_option(title, text, options, default=None):
    result = radiolist_dialog(
        title=title,
        text=text,
        values=options,
        default=default
    ).run()
    return result

# --- Initialize ---
clear_screen()
print_header()

path_completer = PathCompleter(expanduser=True)
history = FileHistory(".dx_history")
cleanup = ask(
    "Clean workspace?", 
    "n", 
    "Wipe existing files to avoid conflicts.\ny = Yes (Delete lamedb/astra/bouquets) | n = No (Safe Merge).", 
    "🧹"
)
if cleanup.lower() == 'y':
    for i in range(0, 101, 10): draw_progress(i, task="Wiping Data")
    for f in os.listdir('.'):
        if (f.startswith('userbouquet.') and f.endswith('.tv')) or f == 'lamedb':
            try: os.remove(f)
            except: pass
    if os.path.exists('astra'): shutil.rmtree('astra')

new_tps, new_srvs, bouquet, astra_blocks = {}, {}, [], []
ONID, TSID, marker_count = "0001", "0001", 1

print(f"\n{Color.YELLOW}┌── {Color.BOLD}DATABASE SOURCE{Color.END}{Color.YELLOW} " + "─" * 61 + "┐")
print(f"│ {Color.BLUE}📂 Path to your existing lamedb for merging.                             {Color.END}{Color.YELLOW} │")
print(f"│ {Color.BLUE}ℹ  Leave blank to create a new file in the current directory (./lamedb)  {Color.END}{Color.YELLOW} │")
print(f"└" + "─" * 78 + "┘" + Color.END)

merge_path = pt_prompt(
    "  Source lamedb path: ",
    completer=path_completer,
    history=history
).strip() or "./lamedb"

bouquet_name = ask("Bouquet name", "T2MI DX", "The name of the favorites group in your channel list.", "🏷️")
bouquet_file = f"userbouquet.{bouquet_name.lower().replace(' ', '_')}.tv"

while True:
    print(f"\n{Color.CYAN}╔" + "═"*78 + "╗")
    print(f"║ {Color.BOLD}DETAILED PARAMETER CONFIGURATION{Color.END}{Color.CYAN}".center(88) + "║")
    print(f"╚" + "═"*78 + "╝" + Color.END)
    
    freq = int(ask("Frequency MHz", "4014", "Downlink Frequency (e.g., 4014, 3665, 11495).", "📡"))
    sr = int(ask("Symbol Rate", "15284", "Transponder Symbol Rate (e.g., 15284, 30000, 7325).", "📶"))
    pol = choose_option(
        "Polarization",
        "Select antenna polarization:",
        [
            ("H", "Horizontal"),
            ("V", "Vertical"),
            ("L", "Left Circular"),
            ("R", "Right Circular")
        ],
        "L"
    )
    sat_pos = float(ask("Satellite position", "18.1", "Orbital position (e.g., 18.1, 40.0, 4.8).", "🌍"))
    sat_dir = ask("Direction (E/W)", "W", "Orbital direction:\nE = East | W = West (Affects D5B0FAE calculation).", "🧭").upper()

    raw_sat = int(sat_pos * 10)
    ns_sat = (3600 - raw_sat) if sat_dir == "W" else raw_sat
    disp_sat = -raw_sat if sat_dir == "W" else raw_sat
    ns_hex = format((ns_sat << 16) | freq, '08x').lower()

    # RESTORED: EXHAUSTIVE CHOICE DOCUMENTATION
    inv = ask("Inversion", "2", 
        "Spectral Inversion settings:\n0 = Off | 1 = On | 2 = Auto (Recommended for most LNBs).", "🛠️")
    fec = choose_option(
        "FEC",
        "Forward Error Correction:",
        [
            ("1","1/2"),
            ("2","2/3"),
            ("3","3/4"),
            ("4","5/6"),
            ("5","7/8"),
            ("6","8/9"),
            ("7","3/5"),
            ("8","4/5"),
            ("9","Auto")
        ],
        "9"
    )
    sys_type = ask("System", "1", 
        "DVB Delivery System:\n0 = DVB-S (Legacy) | 1 = DVB-S2 (Modern/T2-MI Standard).", "🛠️")
    mod = ask("Modulation", "2", 
        "Constellation Type:\n1 = QPSK | 2 = 8PSK | 3 = 16APSK | 4 = 32APSK.", "🛠️")
    roll = ask("RollOff", "0", 
        "Pulse Shaping Factor (Roll-Off):\n0 = 0.35 | 1 = 0.25 | 2 = 0.20.", "🛠️")
    pilot = ask("Pilot", "2", 
        "DVB-S2 Pilot Tones:\n0 = Off | 1 = On | 2 = Auto.", "🛠️")

    tp_key = f"{ns_hex}:{TSID}:{ONID}"
# Accept both letter or numeric input
    pol_map = {
        "H": "0", "0": "0",
        "V": "1", "1": "1",
        "L": "2", "2": "2",
        "R": "3", "3": "3"
    }

    p_digit = pol_map.get(pol, "0")
    new_tps[tp_key] = f"{tp_key}\n\ts {freq*1000}:{sr*1000}:{p_digit}:{fec}:{disp_sat}:{inv}:0:{sys_type}:{mod}:{roll}:{pilot}\n/\n"
    
    sid = int(ask("Feed SID", "320", "Service ID (Decimal) for the raw T2-MI PID carrier.", "🆔"))
    sid_hex = format(sid, '04x').lower()
    provider = ask("Provider name", "ORTM", "Provider label for service metadata.", "🏢")
    pid_input = ask("T2-MI PIDs", "4096", "PIDs carrying T2-MI data. Use commas for multiple (e.g., 4096,4097).", "🔢")
    path = ask("Astra path", "ortm", "URL segment for Astra-SM (e.g., http://0.0.0.0:9999/path/...).", "🔗")

    for pid in [p.strip() for p in pid_input.split(",")]:
        s_ref_core = f"{sid_hex}:{TSID}:{ONID}:{ns_hex}"
        srv_key = f"{sid_hex}:{ns_hex}:{TSID}:{ONID}"
        # Ensure 3-line lamedb standard
        new_srvs[srv_key] = f"{srv_key}:1:0\n{provider} PID{pid} FEED\np:{provider},c:15{format(int(pid),'04x')},f:01\n"
        bouquet.append(f"#SERVICE 1:0:1:{s_ref_core.upper()}:0:0:0:\n#DESCRIPTION {provider} PID{pid} FEED")

        plps = ask(f"PLPs for PID {pid}", "0", "Physical Layer Pipe IDs (e.g., 0, 1). Multiple allowed.", "📺")
        for plp in [pl.strip() for pl in plps.split(",")]:
            # --- ASTRA STYLE: LOCKED ---
            var_name = f"f{freq}{pol.lower()}{provider.lower()[:2]}plp{plp}"
            metadata_comment = f"-- {provider} {freq}{pol} {sr} {sat_pos}{sat_dir} {pid}"
            label_full = f"{provider} {freq}{pol} PID{pid} PLP{plp}"
            
            # Restored: PLP Header Label in Bouquet
            bouquet.append(f"#SERVICE 1:64:0:0:0:0:0:0:0:0:\n#DESCRIPTION --- {provider} {freq}{pol} PLP{plp} ---")

            # Astra config block with pnr=0
            block = f"{metadata_comment}\n{var_name} = make_t2mi_decap({{\n"
            block += f"    name = \"{freq}{pol} T2-MI PLP{plp}\",\n"
            block += f"    input = \"http://127.0.0.1:8001/1:0:1:{sid_hex.upper()}:{TSID.upper()}:{ONID.upper()}:{ns_hex.upper()}:0:0:0:\",\n"
            block += f"    plp = {plp},\n    pnr = 0,\n    pid = {pid},\n}})\n"
            block += f"make_channel({{\n    name = \"{label_full}\",\n"
            block += f"    input = {{ \"t2mi://{var_name}\", }},\n"
            block += f"    output = {{ \"http://0.0.0.0:9999/{path}/a{1280 + marker_count}\", }},\n}})\n"
            astra_blocks.append(block)


        # --- Decorated Channel File Selection with Path Completion ---
            print(f"\n{Color.YELLOW}┌── {Color.BOLD}SUB-CHANNEL MAPPING{Color.END}{Color.YELLOW} " + "─" * 57 + "┐")
            print(f"│ {Color.BLUE}📁 CSV File (SID,NAME,TYPE) for sub-channel mapping.                     {Color.END}{Color.YELLOW} │")
            print(f"│ {Color.BLUE}ℹ  Use TAB to browse files. Leave blank to skip mapping.                 {Color.END}{Color.YELLOW} │")
            print(f"└" + "─" * 78 + "┘" + Color.END)

            ch_file = pt_prompt(
                f"  Channel file for PLP {plp}: ",
                completer=path_completer,
                history=history
            ).strip()
            if ch_file and os.path.exists(ch_file):
                sub_url = f"http://0.0.0.0:9999/{path}/a{1280 + marker_count}".replace(":", "%3a")
                with open(ch_file, "r", encoding="utf8") as f:
                    for line in f:
                        if "," not in line: continue
                        csid, name, stype = line.strip().split(",")
                        c_ref = f"1:0:{stype}:{format(int(csid),'x').upper()}:{TSID.upper()}:{ONID.upper()}:{ns_hex.upper()}:0:0:0:{sub_url}:{name}"
                        bouquet.append(f"#SERVICE {c_ref}\n#DESCRIPTION {name}")
            
            marker_count += 1

    if ask("Add another?", "n", "y = Add transponder | n = Finalize file generation.", "❓") != "y": break

# --- Header-Relative Merger ---
for i in range(0, 101, 20): draw_progress(i, task="Merging Database")
if os.path.exists(merge_path):
    with open(merge_path, 'r', encoding='utf-8', errors='ignore') as f:
        lines = f.readlines()
    old_content = "".join(lines)
    try:
        tp_idx = [i for i, l in enumerate(lines) if l.strip() == "transponders"][0]
        for k, v in new_tps.items():
            if k not in old_content: lines.insert(tp_idx + 1, v)
    except: pass
    try:
        srv_idx = [i for i, l in enumerate(lines) if l.strip() == "services"][0]
        for k, v in new_srvs.items():
            if k not in old_content: lines.insert(srv_idx + 1, v)
    except: pass
    with open("lamedb", "w", encoding='utf-8') as f: f.writelines(lines)
else:
    with open("lamedb", "w", encoding='utf-8') as f:
        f.write("eDVB services /4/\ntransponders\n" + "".join(new_tps.values()) + "end\nservices\n" + "".join(new_srvs.values()) + "end\n")

# Bouquet and Astra
with open(bouquet_file, "w") as f: f.write(f"#NAME {bouquet_name}\n" + "\n".join(bouquet) + "\n")
if not os.path.exists("astra"): os.makedirs("astra")
with open("astra/astra.conf", "w") as f: f.write("\n".join(astra_blocks))

draw_progress(100, task="Complete")
print(f"\n\n{Color.GREEN}{Color.BOLD}✅ v9.7 ENCYCLOPEDIA ARCHITECT LOCKED!{Color.END}")
