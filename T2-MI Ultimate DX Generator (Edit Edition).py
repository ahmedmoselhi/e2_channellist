import re
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

class GoBack(Exception):
    """Custom exception to handle step reversion."""
    pass

class Color:
    BLUE = '\033[94m'
    CYAN = '\033[96m'
    GREEN = '\033[92m'
    YELLOW = '\033[93m'
    RED = '\033[91m'
    BOLD = '\033[1m'
    END = '\033[0m'

POL_MAP = {"H": 0, "V": 1, "L": 2, "R": 3}

def parse_astra_configs():
    """Extracts metadata from astra.conf to allow for parameter pre-loading."""
    configs = {}
    path = "astra/astra.conf"
    if os.path.exists(path):
        with open(path, "r", encoding="utf-8") as f:
            content = f.read()
            # Capture variable name (e.g., f4014lortmp4096plp0), plp, and pid
            pattern = r'(\w+)\s*=\s*make_t2mi_decap\({\s*.*?plp\s*=\s*(\d+),.*?pid\s*=\s*(\d+),'
            matches = re.findall(pattern, content, re.DOTALL)
            for var_name, plp, pid in matches:
                configs[var_name] = {'plp': plp, 'pid': pid}
    return configs

def get_current_params(freq, pol, existing_astra):
    """Searches parsed data for a specific transponder's current setup."""
    search_key = f"f{freq}{pol.lower()}"
    for k, v in existing_astra.items():
        if k.startswith(search_key):
            return v
    return None

def clear_screen():
    os.system('cls' if os.name == 'nt' else 'clear')

def exit_gracefully():
    print(f"\n\n{Color.RED}⚠ Process interrupted by user (Ctrl+C).{Color.END}")
    print(f"{Color.YELLOW}Exiting The Encyclopedia Architect...{Color.END}")
    sys.exit(0)

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

def ask(prompt, default=None, help_text="", icon="ℹ", allow_back=True):
    while True:
        print(f"\n{Color.YELLOW}┌── {Color.BOLD}INPUT FIELD{Color.END}{Color.YELLOW} " + "─"*65 + "┐")
        full_help = f"{help_text}"
        if allow_back:
            full_help += "\n[ Type 'back' to return to the previous question ]"
        if default is not None:
            full_help += f"\n[ DEFAULT CHOICE: {default} ] (Press Enter to use default)"
        else:
            full_help += f"\n[ REQUIRED FIELD: Manual entry necessary ]"

        for line in full_help.strip().split('\n'):
            print(f"│ {Color.BLUE}{icon} {line.ljust(74)}{Color.END}{Color.YELLOW} │")
        print(f"└" + "─"*78 + "┘" + Color.END)
        prompt_text = f"  {prompt}: "
        val = pt_prompt(prompt_text, history=history).strip()

        if val.lower() == "back" and allow_back:
            raise GoBack()
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
class GoBack(Exception):
    pass

try:
    clear_screen()
    print_header()

    path_completer = PathCompleter(expanduser=True)
    history = FileHistory(".dx_history")

    # Initialize storage for the generator
    new_tps, new_srvs, bouquet, astra_blocks = {}, {}, [], []
    ONID, TSID, marker_count = "0001", "0001", 1

    # --- State-Controlled Logic ---
    step = 1
    while True:
        try:
            if step == 1:
                print(f"\n{Color.CYAN}╔" + "═"*78 + "╗")
                print(f"║ {Color.BOLD}ARCHITECT SESSION INITIALIZATION{Color.END}{Color.CYAN}".center(88) + "║")
                print(f"╚" + "═"*78 + "╝" + Color.END)

                mode = radiolist_dialog(
                    title="OPERATION MODE", 
                    text="Choose how to handle existing database files:",
                    values=[
                        ("modify", "MODIFY/APPEND: Read existing files and update matches."), 
                        ("fresh", "FRESH START: Wipe everything and start a new database.")
                    ], 
                    default="modify").run()

                if mode is None: sys.exit(0)

                if mode == "fresh":
                    print(f"\n{Color.RED}⚠ WARNING: EXECUTING FULL WORKSPACE WIPE...{Color.END}")
                    for i in range(0, 101, 10): 
                        draw_progress(i, task="Purging Data")
                    for f in os.listdir('.'):
                        if (f.startswith('userbouquet.') and f.endswith('.tv')) or f == 'lamedb':
                            try: os.remove(f)
                            except: pass
                    if os.path.exists('astra'): shutil.rmtree('astra')
                    print(f"\n  {Color.GREEN}✨ Workspace cleaned successfully.{Color.END}")
                else:
                    for i in range(0, 101, 20): 
                        draw_progress(i, task="Parsing Files")
                    print(f"\n  {Color.GREEN}📂 Existing database loaded into memory.{Color.END}")

                # PRE-LOAD existing data for editing
                existing_astra = parse_astra_configs() if mode == "modify" else {}
                step = 2

            elif step == 2:
                print(f"\n{Color.YELLOW}┌── {Color.BOLD}DATABASE SOURCE{Color.END}{Color.YELLOW} " + "─" * 61 + "┐")
                print(f"│ {Color.BLUE}📂 Path to your existing lamedb for merging.                             {Color.END}{Color.YELLOW} │")
                print(f"│ {Color.BLUE}Press enter to create new empty ./lamedb file.                           {Color.END}{Color.YELLOW} │")
                print(f"│ {Color.BLUE}ℹ  Type 'back' to return to cleanup settings.                            {Color.END}{Color.YELLOW} │")
                print(f"└" + "─" * 78 + "┘" + Color.END)
                merge_path = pt_prompt("  Source lamedb path: ", completer=path_completer, history=history).strip() or "./lamedb"
                if merge_path.lower() == "back": step = 1; continue
                step = 3

            elif step == 3:
                bouquet_name = ask("Bouquet name", "T2MI DX", "The name of the favorites group in your channel list.", "🏷️")
                bouquet_file = f"userbouquet.{bouquet_name.lower().replace(' ', '_')}.tv"
                step = 4

            elif step == 4:
                print(f"\n{Color.CYAN}╔" + "═"*78 + "╗")
                print(f"║ {Color.BOLD}THE ARCHITECT: SELECTIVE PARAMETER SYNCHRONIZATION{Color.END}{Color.CYAN}".center(88) + "║")
                print(f"║ {Color.BLUE}v10.0 'Elite Edit' Protocol Active".center(86) + f"{Color.CYAN} ║")
                print(f"╚" + "═"*78 + "╝" + Color.END)

                freq_help = (
                    f"{Color.BOLD}PRIMARY DATABASE KEY{Color.END}\n"
                    "Enter the Transponder Frequency in MHz.\n"
                    "────────────┬────────────────────────────\n"
                    " Range      │ 2000 - 13000 MHz\n"
                    " Standard   │ C-Band (3.4-4.2) / Ku-Band (10.7-12.7)\n"
                    "────────────┴────────────────────────────"
                )
                freq = int(ask("Target Frequency", "4014", freq_help, "📡"))
                step = 5

            elif step == 5:
                pol_text = (
                    f"{Color.BOLD}ELECTROMAGNETIC POLARITY{Color.END}\n"
                    "Select the signal orientation to trigger LNB voltage.\n"
                    "┌──────┬──────────────────────┬─────────┐\n"
                    "│ CODE │ DESCRIPTION          │ VOLTAGE │\n"
                    "├──────┼──────────────────────┼─────────┤\n"
                    "│ H/V  │ Linear (Standard)    │ 18V/13V │\n"
                    "│ L/R  │ Circular (Special)   │ LH/RH   │\n"
                    "└──────┴──────────────────────┴─────────┘"
                )
                pol = choose_option("Polarization", pol_text, 
                                    [("H", "Horizontal (18V)"), 
                                     ("V", "Vertical (13V)"), 
                                     ("L", "Left Circular"), 
                                     ("R", "Right Circular")], "L")
                if pol is None: step = 4; continue

                # --- ARCHITECTURAL SUMMARY BOX ---
                current_cfg = get_current_params(freq, pol, existing_astra)
                if current_cfg:
                    print(f"\n{Color.GREEN}┏" + "━"*76 + "┓")
                    print(f"┃ {Color.BOLD}RECOGNIZED SIGNATURE FOUND IN ASTRA.CONF{Color.END}{Color.GREEN} ".ljust(85) + "┃")
                    print(f"┠" + "─"*76 + "┨")
                    print(f"┃ {Color.CYAN}💠 FREQUENCY : {freq} MHz".ljust(85) + f"{Color.GREEN}┃")
                    print(f"┃ {Color.CYAN}💠 T2-MI PID : {current_cfg['pid']}".ljust(85) + f"{Color.GREEN}┃")
                    print(f"┃ {Color.CYAN}💠 PLP ID    : {current_cfg['plp']}".ljust(85) + f"{Color.GREEN}┃")
                    print(f"┗" + "━"*76 + "┛" + Color.END)
                else:
                    print(f"\n{Color.YELLOW}⚡ [ NEW DISCOVERY ]: No matching parameters found. Architect Initializing...{Color.END}")

                step = 6

            elif step == 6:
                # --- GATE 1: Physical Layer (Transponder) ---
                tp_help = (
                    f"{Color.BOLD}PHYSICAL LAYER GATEWAY{Color.END}\n"
                    "Edit the 'RF' parameters of the transponder?\n"
                    "Select 'y' to access SR, Sat Pos, FEC, and Modulation.\n"
                    "Select 'n' to bypass and use system defaults."
                )
                edit_tp = ask("Modify Physical Layer?", "n", tp_help, "⚙️")

                if edit_tp.lower() == 'y':
                    sr = int(ask("Symbol Rate (kS/s)", "7325", "Flow rate of symbols. Standard values: 27500, 30000, 7325.", "📶"))
                    sat_pos = float(ask("Orbital Position", "18.1", "Satellite longitude (e.g., 4.9, 18.1, 36.0).", "🌍"))
                    sat_dir = ask("Direction (E/W)", "W", "Orbital Arc: [E]ast or [W]est.", "🧭").upper()
                    inv = ask("Inversion", "2", "Signal Phase: 0=Off | 1=On | 2=Auto-Detect.", "🛠️")

                    fec_help = (
                        f"{Color.BOLD}FEC (FORWARD ERROR CORRECTION){Color.END}\n"
                        "Redundancy bits to ensure data integrity.\n"
                        "Options: 1/2, 2/3, 3/4, 5/6, 7/8, 8/9, 3/5, 4/5, Auto."
                    )
                    fec = choose_option("FEC Ratio", fec_help, [("1","1/2"), ("2","2/3"), ("3","3/4"), ("4","5/6"), ("5","7/8"), ("6","8/9"), ("7","3/5"), ("8","4/5"), ("9","Auto")], "9")

                    sys_help = "Standard: 0=DVB-S (Legacy) | 1=DVB-S2 (T2-MI Standard)."
                    sys_type = ask("Delivery System", "1", sys_help, "🏗️")

                    mod_help = (
                        f"{Color.BOLD}MODULATION CONSTELLATION{Color.END}\n"
                        "1: QPSK   (Robust) | 2: 8PSK  (Balanced)\n"
                        "3: 16APSK (High)   | 4: 32APSK (Ultra)"
                    )
                    mod = ask("Modulation Type", "2", mod_help, "💠")
                    roll = ask("Roll-Off Factor", "0", "Shaping: 0=0.35 (DVB-S) | 1=0.25 | 2=0.20 (DVB-S2).", "🌊")
                    pilot = ask("Pilot Tones", "2", "Tracking: 0=Off | 1=On | 2=Auto.", "🔦")
                else:
                    sr, sat_pos, sat_dir, inv, fec, sys_type, mod, roll, pilot = 7325, 18.1, "W", "2", "9", "1", "2", "0", "2"

                # --- Essential Database Calculation ---
                raw_sat = int(sat_pos * 10)
                ns_sat = (3600 - raw_sat) if sat_dir == "W" else raw_sat
                disp_sat = -raw_sat if sat_dir == "W" else raw_sat
                ns_hex = format((ns_sat << 16) | freq, '08x').lower()
                step = 7

            elif step == 7:
                # --- GATE 2: Transport Layer (PIDs) ---
                cur_pid = current_cfg['pid'] if current_cfg else "4096"
                pid_gate_help = (
                    f"{Color.BOLD}TRANSPORT LAYER GATEWAY{Color.END}\n"
                    f"Current PID: {Color.YELLOW}{cur_pid}{Color.END}\n"
                    "Select 'y' to re-assign the T2-MI Packet ID.\n"
                    "Select 'n' to lock current routing."
                )
                edit_pid = ask("Modify T2-MI PID?", "n", pid_gate_help, "🔢")

                pid_input_help = "Packet Identifier for the T2-MI stream. Common: 4096, 500, 1000."
                pid_input = ask("Enter T2-MI PID", cur_pid, pid_input_help, "🔢") if edit_pid.lower() == 'y' else cur_pid
                step = 8

            elif step == 8:
                # --- GATE 3: Data Layer (PLPs) ---
                cur_plp = current_cfg['plp'] if current_cfg else "0"
                plp_gate_help = (
                    f"{Color.BOLD}DATA PIPE GATEWAY{Color.END}\n"
                    f"Current PLP: {Color.YELLOW}{cur_plp}{Color.END}\n"
                    "Select 'y' to edit Physical Layer Pipe IDs.\n"
                    "Select 'n' to maintain current stream map."
                )
                edit_plp = ask("Modify PLP Pipe?", "n", plp_gate_help, "📺")

                plp_input_help = "Pipe IDs (0-255). Format: Single (0) or List (0, 1, 2)."
                plps_input = ask("Enter PLP IDs", cur_plp, plp_input_help, "📺") if edit_plp.lower() == 'y' else cur_plp
                step = 9

            elif step == 9:
                # --- GATE 4: Identity Layer (Metadata) ---
                print(f"\n{Color.CYAN}┌── {Color.BOLD}FINALIZING IDENTITY ARCHITECTURE{Color.END}{Color.CYAN} " + "─" * 45 + "┐")
                sid_help = "Service ID (Decimal). Used by Enigma2 to identify the channel in lamedb."
                sid = int(ask("Feed SID", "800", sid_help, "🆔"))
                provider = ask("Provider Name", "ORTM", "Broadcaster Name (e.g., ORTM, TNT, Mali-T2MI).", "🏢")
                path_help = "Internal URL segment for streaming (e.g. 'mali'). Affects m3u output."
                path = ask("Relay Path", "ortm", path_help, "🔗")
                print(f"└" + "─" * 78 + "┘" + Color.END)
                step = 10

            # ==============================================================================
            # --- FINAL ARCHITECTURAL PHASE: DATA SYNTHESIS & IO OPERATIONS ---
            # ==============================================================================
            elif step == 10:
                # Calculate the core TP key for lamedb
                tp_key = f"{ns_hex}:{TSID}:{ONID}"
                new_tps[tp_key] = (
                    f"{ns_hex}:{TSID}:{ONID}\n"
                    f"\ts {freq}000:{sr}000:{POL_MAP[pol]}:{fec}:{disp_sat}:{inv}:{sys_type}:{mod}:{roll}:{pilot}:0\n"
                    f"/\n")

                pids_to_process = [p.strip() for p in pid_input.split(",") if p.strip()]
                
                print(f"\n{Color.CYAN}╔" + "═"*78 + "╗")
                print(f"║ {Color.BOLD}TRANSPORT LAYER DE-ENCAPSULATION: {len(pids_to_process)} PIDs DETECTED{Color.END}{Color.CYAN}".center(88) + "║")
                print(f"║ {Color.BLUE}Initializing Routing Protocols for T2-MI Streams...".center(86) + f"{Color.CYAN} ║")
                print(f"╚" + "═"*78 + "╝" + Color.END)

                # Hex versions for service reference construction
                sid_hex = format(sid, 'x').lower()
                tsid_hex = format(int(TSID, 16), 'x').lower()
                onid_hex = format(int(ONID, 16), 'x').lower()

                for pid in pids_to_process:
                    pid_hex_attr = format(int(pid), '04x')
                    srv_key = f"{sid_hex}:{ns_hex}:{TSID}:{ONID}"
                    s_ref_core = f"{sid_hex}:{tsid_hex}:{onid_hex}:{ns_hex}"

                    # Update lamedb service storage
                    new_srvs[srv_key] = (
                        f"{srv_key}:1:0\n"
                        f"{provider} PID{pid} FEED\n"
                        f"p:{provider},c:15{pid_hex_attr},f:01\n")

                    # 1. ADD MASTER FEED TO BOUQUET
                    bouquet.append(f"#SERVICE 1:0:1:{s_ref_core}:0:0:0:\n#DESCRIPTION {provider} PID{pid} FEED")
                    
                    # Search existing configs for this specific transponder/PID combo
                    found_plp = "0"
                    search_stub = f"f{freq}{pol.lower()}"
                    for k, v in existing_astra.items():
                        if k.startswith(search_stub) and f"p{pid}" in k:
                            found_plp = v.get('plp', "0")
                            break

                    # --- PLP CONFIGURATION UI ---
                    plp_help = (
                        f"{Color.BOLD}PHYSICAL LAYER PIPE (PLP) ASSIGNMENT{Color.END}\n"
                        f"Targeting PID: {Color.GREEN}{pid}{Color.END}\n"
                        "────────────┬────────────────────────────\n"
                        " Multi-PLP  │ Enter as comma-separated: 0, 1, 2\n"
                        " T2-MI Spec │ Standard range: 0 - 255\n"
                        "────────────┴────────────────────────────"
                    )
                    print(f"\n{Color.YELLOW}┌── {Color.BOLD}DATA PIPE ARCHITECTURE: PID {pid}{Color.END}{Color.YELLOW} " + "─" * (76 - len(str(pid)) - 23) + "┐")
                    plps_input = ask(f"PLPs for PID {pid}", found_plp, plp_help, "📺")
                    
                    for plp in [pl.strip() for pl in plps_input.split(",") if pl.strip()]:
                        # Generate unique variable name for Astra
                        var_name = f"f{freq}{pol.lower()}{provider.lower()[:2]}p{pid}plp{plp}"
                        label_full = f"{provider} {freq}{pol} PID{pid} PLP{plp}"

                        # Visual separator in the channel list
                        bouquet.append(f"#SERVICE 1:64:0:0:0:0:0:0:0:0:\n#DESCRIPTION --- {label_full} ---")

                        # ASTRA CONFIGURATION BLOCK GENERATION
                        block = f"-- {label_full}\n{var_name} = make_t2mi_decap({{\n"
                        block += f"    name = \"decap_{var_name}\",\n"
                        block += f"    input = \"http://127.0.0.1:8001/1:0:1:{sid_hex}:{tsid_hex}:{onid_hex}:{ns_hex}:0:0:0:\",\n"
                        block += f"    plp = {plp},\n    pnr = 0,\n    pid = {pid},\n}})\n"
                        block += f"make_channel({{\n    name = \"{label_full}\",\n"
                        block += f"    input = {{ \"t2mi://{var_name}\", }},\n"
                        block += f"    output = {{ \"http://0.0.0.0:9999/{path}/p{pid}_plp{plp}\", }},\n}})\n"
                        astra_blocks.append(block)

                        # --- GATE 5: SUB-CHANNEL MAPPING (CSV IMPORT) ---
                        csv_help = (
                            f"{Color.BOLD}SUB-CHANNEL MAPPING PROTOCOL{Color.END}\n"
                            f"Importing virtual services for {Color.GREEN}PID {pid} / PLP {plp}{Color.END}\n"
                            "────────────┬──────────────────────────────────────────\n"
                            " Purpose    │ Maps internal T2-MI streams to Enigma2 channels.\n"
                            " CSV Format │ ServiceID, Name, ServiceType (1=SD, 19=HD)\n"
                            " Example    │ 101,ORTM 1 HD,19\n"
                            "────────────┴──────────────────────────────────────────"
                        )
                        
                        print(f"\n{Color.YELLOW}┌── {Color.BOLD}SUB-CHANNEL MAPPING: PID {pid} PLP {plp}{Color.END}{Color.YELLOW} " + "─" * (76 - 28 - len(str(pid)) - len(str(plp))) + "┐")
                        for line in csv_help.strip().split('\n'):
                            print(f"│ {Color.BLUE}📂 {line.ljust(74)}{Color.END}{Color.YELLOW} │")
                        print(f"└" + "─" * 78 + "┘" + Color.END)
                        
                        ch_file = pt_prompt(
                            f"  Provide .csv path for PLP {plp} (or Enter to skip): ", 
                            completer=path_completer, 
                            history=history,
                            placeholder=" [Path/to/channels.csv]"
                        ).strip()

                        if ch_file.lower() == "back": raise GoBack()

                        if ch_file and os.path.exists(ch_file):
                            sub_url = f"http://0.0.0.0:9999/{path}/p{pid}_plp{plp}".replace(":", "%3a")
                            print(f"  {Color.CYAN}⚙️  Parsing stream map...{Color.END}")
                            
                            with open(ch_file, "r", encoding="utf8") as f:
                                for line in f:
                                    if "," not in line: continue
                                    try:
                                        csid, name, stype = [x.strip() for x in line.strip().split(",")]
                                        csid_hex = format(int(csid), 'x').lower()
                                        # Constructing the complex DVB-over-HTTP reference
                                        c_ref = f"1:0:{stype}:{csid_hex}:{tsid_hex}:{onid_hex}:{ns_hex}:0:0:0:{sub_url}:{name}"
                                        bouquet.append(f"#SERVICE {c_ref}\n#DESCRIPTION {name}")
                                        print(f"    {Color.GREEN}✔ Added: {name} (SID:{csid}){Color.END}")
                                    except Exception as e:
                                        print(f"    {Color.RED}✖ Error in line: {line.strip()} ({e}){Color.END}")
                        else:
                            if ch_file:
                                print(f"  {Color.RED}⚠ Path not found. Skipping CSV import for this pipe.{Color.END}")
                            else:
                                print(f"  {Color.BLUE}ℹ No CSV provided. Using Master Feed only.{Color.END}")

                # RE-ENTRY OR FINALIZATION
                print(f"\n{Color.BLUE}└" + "─" * 78 + "┘" + Color.END)
                if ask("Add another transponder?", "n", "y = Return to Step 4 | n = Compile Database.", "❓") == "y":
                    step = 4
                    continue
                break
        except GoBack:
            step = max(1, step - 1)
            continue

    # --- FINAL COMPILATION & DISK I/O ---
    print(f"\n{Color.CYAN}╔" + "═"*78 + "╗")
    print(f"║ {Color.BOLD}COMPILING ARCHITECTURAL BLUEPRINTS{Color.END}{Color.CYAN}".center(88) + "║")
    print(f"╚" + "═"*78 + "╝" + Color.END)

    for i in range(0, 101, 20): draw_progress(i, task="Consolidating lamedb")

    # Handle lamedb Merging
    if os.path.exists(merge_path):
        with open(merge_path, 'r', encoding='utf-8', errors='ignore') as f:
            lines = f.readlines()
        old_content = "".join(lines)

        try:
            # 1. Inject Transponders
            tp_idx = [i for i, l in enumerate(lines) if l.strip() == "transponders"][0]
            for k, v in new_tps.items():
                if k in old_content:
                    for idx, line in enumerate(lines):
                        if line.startswith(k):
                            lines[idx:idx+3] = [v]
                            break
                else: lines.insert(tp_idx + 1, v)

            # 2. Inject Services
            srv_idx = [i for i, l in enumerate(lines) if l.strip() == "services"][0]
            for k, v in new_srvs.items():
                if k in old_content:
                    for idx, line in enumerate(lines):
                        if line.startswith(k):
                            lines[idx:idx+3] = [v]
                            break
                else: lines.insert(srv_idx + 1, v)
        except Exception as e:
            print(f"{Color.RED}Error during merge: {e}{Color.END}")

        with open("lamedb", "w", encoding='utf-8') as f: f.writelines(lines)
    else:
        with open("lamedb", "w", encoding='utf-8') as f:
            f.write("eDVB services /4/\ntransponders\n" + "".join(new_tps.values()) + "end\nservices\n" + "".join(new_srvs.values()) + "end\n")

    # Handle Bouquet Reconstruction
    for i in range(0, 101, 50): draw_progress(i, task="Syncing Bouquet")
    final_bouquet_content = []
    if mode == "modify" and os.path.exists(bouquet_file):
        with open(bouquet_file, "r", encoding="utf-8") as f:
            existing_lines = f.readlines()
        
        # Filter duplicates based on unique reference parts
        new_refs = [line.split(':')[-5:-1] for line in bouquet if line.startswith("#SERVICE")]
        skip_next = False
        for line in existing_lines:
            if skip_next: {skip_next := False}; continue
            if line.startswith("#NAME"):
                final_bouquet_content.append(line.strip())
                continue
            is_duplicate = any(all(part in line for part in ref) for ref in new_refs if ":" in line)
            if is_duplicate: {skip_next := True}; continue
            if line.strip(): final_bouquet_content.append(line.strip())

    if not any(l.startswith("#NAME") for l in final_bouquet_content):
        final_bouquet_content.insert(0, f"#NAME {bouquet_name}")
    final_bouquet_content.extend(bouquet)

    with open(bouquet_file, "w", encoding="utf-8") as f:
        f.write("\n".join(final_bouquet_content) + "\n")

    # Handle Astra Reconstruction
    for i in range(0, 101, 25): draw_progress(i, task="Writing Astra")
    if not os.path.exists("astra"): os.makedirs("astra")
    astra_path = "astra/astra.conf"
    
    if mode == "modify" and os.path.exists(astra_path):
        with open(astra_path, "r", encoding="utf-8") as f: old_conf = f.read()
        for b in astra_blocks:
            v_name = b.split("=")[0].strip()
            # Remove old instances of this block to update them
            pattern = rf"-- .*?\n{v_name} = .*?}}\)\nmake_channel.*?}}\)\n"
            old_conf = re.sub(pattern, "", old_conf, flags=re.DOTALL)
        final_astra_content = old_conf.strip() + "\n\n-- [ ARCHITECT MODIFIED ENTRIES ] --\n"
    else:
        final_astra_content = "-- [ ARCHITECT GENERATED CONFIG ] --\n"

    final_astra_content += "\n".join(astra_blocks)
    with open(astra_path, "w", encoding="utf-8") as f:
        f.write(final_astra_content.strip() + "\n")

    print(f"\n{Color.GREEN}✅ ALL FILES SYNCHRONIZED SUCCESSFULLY.{Color.END}")
    print(f"{Color.CYAN}📂 DATABASE: ./lamedb")
    print(f"📂 BOUQUET : ./{bouquet_file}")
    print(f"📂 ASTRA   : ./{astra_path}{Color.END}")
    print(f"\n{Color.GREEN}{Color.BOLD}✨ v9.7 ENCYCLOPEDIA ARCHITECT LOCKED!{Color.END}")

except KeyboardInterrupt:
    exit_gracefully()
