import os
import sys
import shutil
import time

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

# ----------------------------------------------------------------------
# Ensure prompt_toolkit is available
# ----------------------------------------------------------------------
def ensure_dependencies():
    try:
        from prompt_toolkit import prompt as pt_prompt
        from prompt_toolkit.history import FileHistory
        from prompt_toolkit.shortcuts import radiolist_dialog
        from prompt_toolkit.completion import PathCompleter
        return pt_prompt, FileHistory, radiolist_dialog, PathCompleter
    except ImportError:
        import subprocess
        import sys
        import os

        # If we are in the wrong alias (like /usr/bin/py), try to find the pyenv/user python
        # and re-run the script with it.
        if "pyenv" not in sys.executable and os.path.exists(os.path.expanduser("~/.pyenv")):
            print(f"{Color.YELLOW}⚠ System Python detected. Switching to environment shim...{Color.END}")
            os.execvp("python", ["python"] + sys.argv)

        print(f"\n{Color.YELLOW}⚠ Module 'prompt_toolkit' not found.{Color.END}")
        print(f"{Color.CYAN}⚙ Attempting installation...{Color.END}")
        
        # Try multiple common pip access methods
        commands = [
            [sys.executable, "-m", "pip", "install", "prompt_toolkit"],
            ["python", "-m", "pip", "install", "prompt_toolkit"],
            ["pip", "install", "prompt_toolkit"]
        ]
        
        for cmd in commands:
            try:
                if "--break-system-packages" not in cmd and sys.version_info >= (3, 11):
                    cmd.append("--break-system-packages")
                subprocess.check_call(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
                
                from prompt_toolkit import prompt as pt_prompt
                from prompt_toolkit.history import FileHistory
                from prompt_toolkit.shortcuts import radiolist_dialog
                from prompt_toolkit.completion import PathCompleter
                print(f"{Color.GREEN}✅ Success!{Color.END}\n")
                return pt_prompt, FileHistory, radiolist_dialog, PathCompleter
            except:
                continue
        
        print(f"{Color.RED}❌ Failed to initialize environment.{Color.END}")
        print(f"Please run: {Color.BOLD}python -m pip install prompt_toolkit{Color.END}")
        sys.exit(1)

# Initialize the toolkit
pt_prompt, FileHistory, radiolist_dialog, PathCompleter = ensure_dependencies()

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
                cleanup = ask("Clean workspace?", "n", "Wipe existing files to avoid conflicts.\ny = Yes (Delete lamedb/astra/bouquets) | n = No (Safe Merge).", "🧹", allow_back=False)
                if cleanup.lower() == 'y':
                    for i in range(0, 101, 10): draw_progress(i, task="Wiping Data")
                    for f in os.listdir('.'):
                        if (f.startswith('userbouquet.') and f.endswith('.tv')) or f == 'lamedb':
                            try: os.remove(f)
                            except: pass
                    if os.path.exists('astra'): shutil.rmtree('astra')
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
                print(f"║ {Color.BOLD}DETAILED PARAMETER CONFIGURATION{Color.END}{Color.CYAN}".center(88) + "║")
                print(f"╚" + "═"*78 + "╝" + Color.END)
                freq = int(ask("Frequency MHz", "4014", "Downlink Frequency (e.g., 4014, 3665, 11495).", "📡"))
                step = 5

            elif step == 5:
                sr = int(ask("Symbol Rate", "15284", "Transponder Symbol Rate (e.g., 15284, 30000, 7325).", "📶"))
                step = 6

            elif step == 6:
                pol = choose_option("Polarization", "Select antenna polarization:", 
                                    [("H", "Horizontal"), ("V", "Vertical"), ("L", "Left Circular"), ("R", "Right Circular")], "L")
                if pol is None: step = 5; continue
                step = 7

            elif step == 7:
                sat_pos = float(ask("Satellite position", "18.1", "Orbital position (e.g., 18.1, 40.0, 4.8).", "🌍"))
                step = 8

            elif step == 8:
                sat_dir = ask("Direction (E/W)", "W", "Orbital direction:\nE = East | W = West.", "🧭").upper()

                # --- Original Calculation Logic ---
                raw_sat, ns_sat = int(sat_pos * 10), 0
                ns_sat = (3600 - raw_sat) if sat_dir == "W" else raw_sat
                disp_sat = -raw_sat if sat_dir == "W" else raw_sat
                ns_hex = format((ns_sat << 16) | freq, '08x').lower()
                step = 9

            elif step == 9:
                inv = ask("Inversion", "2", "Spectral Inversion settings:\n0 = Off | 1 = On | 2 = Auto.", "🛠️")
                step = 10

            elif step == 10:
                fec = choose_option("FEC", "Forward Error Correction:", 
                                    [("1","1/2"), ("2","2/3"), ("3","3/4"), ("4","5/6"), ("5","7/8"), ("6","8/9"), ("7","3/5"), ("8","4/5"), ("9","Auto")], "9")
                if fec is None: step = 9; continue
                step = 11

            elif step == 11:
                sys_type = ask("System", "1", "DVB Delivery System:\n0 = DVB-S (Legacy) | 1 = DVB-S2 (Modern,required for T2-MI).", "🛠️")
                step = 12

            elif step == 12:
                mod = ask("Modulation", "2", "Constellation: 1=QPSK | 2=8PSK | 3=16APSK | 4=32APSK.", "🛠️")
                step = 13

            elif step == 13:
                roll = ask("RollOff", "0", "Pulse Shaping Factor: 0=0.35 | 1=0.25 | 2=0.20.", "🛠️")
                step = 14

            elif step == 14:
                pilot = ask("Pilot", "2", "DVB-S2 Pilot Tones: 0=Off | 1=On | 2=Auto.", "🛠️")
                step = 15

            elif step == 15:
                # Map Polarization for lamedb
                p_digit = {"H":"0","V":"1","L":"2","R":"3"}.get(pol, "0")
                tp_key = f"{ns_hex}:{TSID}:{ONID}"
                new_tps[tp_key] = f"{tp_key}\n\ts {freq*1000}:{sr*1000}:{p_digit}:{fec}:{disp_sat}:{inv}:0:{sys_type}:{mod}:{roll}:{pilot}\n/\n"

                sid = int(ask("Feed SID", "800", "Service ID (Decimal) for the raw T2-MI PID carrier.", "🆔"))
                sid_hex = format(sid, '04x').lower()
                step = 16

            elif step == 16:
                provider = ask("Provider name", "ORTM", "Provider label for service metadata.", "🏢")
                step = 17

            elif step == 17:
                pid_input = ask("T2-MI PIDs", "4096", "PIDs carrying T2-MI data (e.g., 4096,4097).", "🔢")
                step = 18

            elif step == 18:
                path = ask("Astra path", "ortm", "URL segment for Astra-SM (e.g., http://0.0.0.0:9999/path/...).", "🔗")

                # --- RESTORING FEED DESCRIPTION AND PLP LABELS ---
                for pid in [p.strip() for p in pid_input.split(",")]:
                # Service Ref: No leading zeros for SID/TSID/ONID
                    sid_no_lead = format(sid, 'x').lower()
                    tsid_no_lead = format(int(TSID, 16), 'x').lower()
                    onid_no_lead = format(int(ONID, 16), 'x').lower()

                    s_ref_core = f"{sid_no_lead}:{tsid_no_lead}:{onid_no_lead}:{ns_hex}"
                    srv_key = f"{sid_hex}:{ns_hex}:{TSID}:{ONID}"

                    # Update lamedb storage
                    new_srvs[srv_key] = f"{srv_key}:1:0\n{provider} PID{pid} FEED\np:{provider},c:15{format(int(pid),'04x')},f:01\n"

                    # 1. RESTORED: FEED SERVICE WITH DESCRIPTION
                    bouquet.append(f"#SERVICE 1:0:1:{s_ref_core}:0:0:0:\n#DESCRIPTION {provider} PID{pid} FEED")

                    plps_input = ask(f"PLPs for PID {pid}", "0", "Physical Layer Pipe IDs.", "📺")
                    for plp in [pl.strip() for pl in plps_input.split(",")]:
                        # Variable names and labels
                        var_name = f"f{freq}{pol.lower()}{provider.lower()[:2]}p{pid}plp{plp}"
                        label_full = f"{provider} {freq}{pol} PID{pid} PLP{plp}"

                        # 2. PLP LABEL CHANNEL IN BOUQUET
                        bouquet.append(f"#SERVICE 1:64:0:0:0:0:0:0:0:0:\n#DESCRIPTION --- {label_full} ---")

                        # 3. ASTRA CONFIG BLOCK (Preserving pnr=0 and decap_ naming)
                        block = f"-- {label_full}\n{var_name} = make_t2mi_decap({{\n"
                        block += f"    name = \"decap_{var_name}\",\n"
                        block += f"    input = \"http://127.0.0.1:8001/1:0:1:{sid_no_lead}:{tsid_no_lead}:{onid_no_lead}:{ns_hex}:0:0:0:\",\n"
                        block += f"    plp = {plp},\n    pnr = 0,\n    pid = {pid},\n}})\n"
                        block += f"make_channel({{\n    name = \"{label_full}\",\n"
                        block += f"    input = {{ \"t2mi://{var_name}\", }},\n"
                        block += f"    output = {{ \"http://0.0.0.0:9999/{path}/{freq}_{sat_pos}{sat_dir.lower()}_plp{plp}\", }},\n}})\n"
                        astra_blocks.append(block)

                        # ---- Sub‑channel CSV mapping (Encyclopedia Architect v9.7 Style) ----
                        orbital_folder = f"{sat_pos}{sat_dir.upper()}"
                        csv_dir = os.path.join("channellist", orbital_folder)
                        
                        suggestions = []
                        if os.path.isdir(csv_dir):
                            suggestions = [f for f in os.listdir(csv_dir) if f.lower().endswith('.csv')]

                        print(f"\n{Color.YELLOW}┌── {Color.BOLD}SUB-CHANNEL MAPPING: PID {pid} PLP {plp}{Color.END}{Color.YELLOW} " + "─" * (76 - 28 - len(str(pid)) - len(str(plp))) + "┐")
                        csv_help = (
                            f"{Color.BOLD}SUB‑CHANNEL MAPPING PROTOCOL{Color.END}\n"
                            f"Import virtual services for PID {pid} / PLP {plp}\n"
                            f"Auto‑scan found {len(suggestions)} CSV file(s) in ./{csv_dir}"
                        )
                        for line in csv_help.split("\n"):
                            print(f"│ {Color.BLUE}📂 {line.ljust(74)}{Color.END}{Color.YELLOW} │")
                        
                        if suggestions:
                            print(f"┠" + "─" * 78 + "┨")
                            for idx, fname in enumerate(suggestions, 1):
                                print(f"│ {Color.CYAN} [{idx}] {fname.ljust(72)}{Color.END}{Color.YELLOW} │")
                        print(f"└" + "─" * 78 + "┘" + Color.END)

                        prompt_text = f"  Select file [#] or path for {orbital_folder} PLP {plp}: "
                        ch_choice = pt_prompt(prompt_text, completer=path_completer, history=history).strip()

                        if ch_choice.lower() == "back":
                            raise GoBack()

                        # Resolve numeric shortcut or raw path
                        if ch_choice.isdigit() and 1 <= int(ch_choice) <= len(suggestions):
                            ch_file = os.path.join(csv_dir, suggestions[int(ch_choice) - 1])
                        else:
                            ch_file = ch_choice

                        if ch_file and os.path.isfile(ch_file):
                            print(f"  {Color.CYAN}⚙️  Parsing {os.path.basename(ch_file)}...{Color.END}")
                            sub_url = f"http://0.0.0.0:9999/{path}/{freq}_{sat_pos}{sat_dir.lower()}_plp{plp}".replace(":", "%3a")

                            with open(ch_file, "r", encoding="utf8") as f:
                                for line in f:
                                    if "," not in line: continue
                                    try:
                                        csid, name, stype = [x.strip() for x in line.strip().split(",")]
                                        csid_hex = format(int(csid), 'x').lower()
                                        c_ref = f"1:0:{stype}:{csid_hex}:{tsid_no_lead}:{onid_no_lead}:{ns_hex}:0:0:0:{sub_url}:{name}"
                                        bouquet.append(f"#SERVICE {c_ref}\n#DESCRIPTION {name}")
                                        print(f"    {Color.GREEN}✔ Added: {name}{Color.END}")
                                    except Exception as exc:
                                        print(f"    {Color.RED}✖ Error: {exc}{Color.END}")

                        marker_count += 1

                if ask("Add another transponder?", "n", "y = Add transponder | n = Finalize generation.", "❓") == "y":
                    step = 4
                    continue
                break

        except GoBack:
            step = max(1, step - 1)
            clear_screen()
            print_header()
            print(f"\n{Color.RED}↩ REVERTING TO PREVIOUS STEP...{Color.END}")

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

except KeyboardInterrupt:
    exit_gracefully()
