import os
import sys
import shutil
import time

# ----------------------------------------------------------------------
# Core Exceptions & Styling
# ----------------------------------------------------------------------
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
# Environment Initialization
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
        
        if "pyenv" not in sys.executable and os.path.exists(os.path.expanduser("~/.pyenv")):
            print(f"{Color.YELLOW}⚠ System Python detected. Switching to environment shim...{Color.END}")
            os.execvp("python", ["python"] + sys.argv)

        print(f"\n{Color.YELLOW}⚠ Module 'prompt_toolkit' not found.{Color.END}")
        print(f"{Color.CYAN}⚙ Attempting installation...{Color.END}")
        
        pip_cmd = [sys.executable, "-m", "pip", "install", "prompt_toolkit"]
        if sys.version_info >= (3, 11):
            pip_cmd.append("--break-system-packages")
            
        try:
            subprocess.check_call(pip_cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            from prompt_toolkit import prompt as pt_prompt
            from prompt_toolkit.history import FileHistory
            from prompt_toolkit.shortcuts import radiolist_dialog
            from prompt_toolkit.completion import PathCompleter
            print(f"{Color.GREEN}✅ Success!{Color.END}\n")
            return pt_prompt, FileHistory, radiolist_dialog, PathCompleter
        except Exception:
            print(f"{Color.RED}❌ Failed to initialize environment.{Color.END}")
            print(f"Please run: {Color.BOLD}python -m pip install prompt_toolkit{Color.END}")
            sys.exit(1)

# Initialize the toolkit
pt_prompt, FileHistory, radiolist_dialog, PathCompleter = ensure_dependencies()

# --- CATEGORY-SPECIFIC HISTORY ---
history_files = {
    "default": FileHistory(".dx_history_default"),
    "paths": FileHistory(".dx_history_paths"),
    "bouquet": FileHistory(".dx_history_bouquet"),
    "freq": FileHistory(".dx_history_freq"),
    "pid": FileHistory(".dx_history_pid"),
    "sid": FileHistory(".dx_history_sid"),
    "provider": FileHistory(".dx_history_provider")
}

# ----------------------------------------------------------------------
# UI Helper Functions
# ----------------------------------------------------------------------
def file_browser(start_path="."):
    """Visual file manager for target selection."""
    current_dir = os.path.abspath(start_path)
    while True:
        try:
            items = sorted(os.listdir(current_dir))
            options = [("..", "[ .. Parent Directory ]")]
            for item in items:
                path = os.path.join(current_dir, item)
                if os.path.isdir(path):
                    options.append((path, f"📁 {item}/"))
                elif item == "lamedb" or item.endswith(".bak"):
                    options.append((path, f"📄 {item}"))

            selection = radiolist_dialog(
                title="FILE MANAGER: SELECT TARGET",
                text=f"Current Directory: {current_dir}\n\nSelect a file. Cancel to use './lamedb'.",
                values=options
            ).run()

            if selection is None: 
                print(f"  {Color.YELLOW}ℹ Cancelled. Using default: ./lamedb{Color.END}")
                return "./lamedb" 
            if selection == "..":
                current_dir = os.path.dirname(current_dir)
            elif os.path.isdir(selection):
                current_dir = selection
            else: return selection
        except Exception as e:
            print(f"  {Color.RED}⚠ Error: {e}. Using default.{Color.END}")
            return "./lamedb"

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

def ask(prompt, default=None, help_text="", icon="ℹ", allow_back=True, category="default"):
    while True:
        print(f"\n{Color.YELLOW}┌── {Color.BOLD}INPUT FIELD{Color.END}{Color.YELLOW} " + "─"*65 + "┐")
        full_help = help_text + ("\n[ Type 'back' to return to the previous question ]" if allow_back else "")
        full_help += f"\n[ DEFAULT CHOICE: {default} ]" if default is not None else "\n[ REQUIRED FIELD ]"
        for line in full_help.strip().split('\n'):
            print(f"│ {Color.BLUE}{icon} {line.ljust(74)}{Color.END}{Color.YELLOW} │")
        print(f"└" + "─"*78 + "┘" + Color.END)
        
        cat_history = history_files.get(category, history_files["default"])
        val = pt_prompt(f"  {prompt}: ", history=cat_history).strip()

        if val.lower() == "back" and allow_back: raise GoBack()
        if val == "" and default is not None: return default
        if val != "": return val
        print(f"  {Color.RED}⚠ ALERT: Value required.{Color.END}")

def choose_option(title, text, options, default=None):
    result = radiolist_dialog(title=title, text=text, values=options, default=default).run()
    if result is None: raise GoBack()
    return result

# ----------------------------------------------------------------------
# Main Logic
# ----------------------------------------------------------------------
try:
    clear_screen()
    print_header()

    path_completer = PathCompleter(expanduser=True)
    new_tps, new_srvs, bouquet, astra_blocks = {}, {}, [], []
    ONID, TSID = "0001", "0001"
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
                print(f"│ {Color.BLUE}📂 Opening File Manager...{' ' * 47}{Color.END}{Color.YELLOW}│")
                print(f"│ {Color.BLUE}ℹ Cancelling will automatically select local ./lamedb.{' ' * 23}{Color.END}{Color.YELLOW}│")
                print(f"└" + "─" * 78 + "┘" + Color.END)
                merge_path = file_browser(".")
                print(f"  {Color.GREEN}✅ Target Active: {Color.BOLD}{merge_path}{Color.END}")
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
                step = 7

            elif step == 7:
                sat_pos = float(ask("Satellite position", "18.1", "Orbital position (e.g., 18.1, 40.0, 4.8).", "🌍"))
                step = 8

            elif step == 8:
                sat_dir = ask("Direction (E/W)", "W", "Orbital direction:\nE = East | W = West.", "🧭").upper()
                raw_sat = int(sat_pos * 10)
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
                p_digit = {"H":"0","V":"1","L":"2","R":"3"}.get(pol, "0")
                tp_key = f"{ns_hex}:{TSID}:{ONID}"
                new_tps[tp_key] = f"{tp_key}\n\ts {freq*1000}:{sr*1000}:{p_digit}:{fec}:{disp_sat}:{inv}:0:{sys_type}:{mod}:{roll}:{pilot}\n/\n"

                sid = int(ask("Feed SID", "800", "Service ID (Decimal) for the raw T2-MI PID carrier.", "🆔"))
                sid_hex, sid_no_lead = format(sid, '04x').lower(), format(sid, 'x').lower()
                tsid_no_lead = format(int(TSID, 16), 'x').lower()
                onid_no_lead = format(int(ONID, 16), 'x').lower()
                step = 16

            elif step == 16:
                provider = ask("Provider name", "ORTM", "Provider label for service metadata.", "🏢")
                step = 17

            elif step == 17:
                pid_input = ask("T2-MI PIDs", "4096", "PIDs carrying T2-MI data (e.g., 4096,4097).", "🔢")
                step = 18

            elif step == 18:
                path = ask("Astra path", "ortm", "URL segment for Astra-SM.", "🔗")

                for pid in [p.strip() for p in pid_input.split(",")]:
                    s_ref_core = f"{sid_no_lead}:{tsid_no_lead}:{onid_no_lead}:{ns_hex}"
                    srv_key = f"{sid_hex}:{ns_hex}:{TSID}:{ONID}"

                    new_srvs[srv_key] = f"{srv_key}:1:0\n{provider} PID{pid} FEED\np:{provider},c:15{format(int(pid),'04x')},f:01\n"
                    bouquet.append(f"#SERVICE 1:0:1:{s_ref_core}:0:0:0:\n#DESCRIPTION {provider} PID{pid} FEED")

                    plps_input = ask(f"PLPs for PID {pid}", "0", "Physical Layer Pipe IDs.", "📺")
                    for plp in [pl.strip() for pl in plps_input.split(",")]:
                        var_name = f"f{freq}{pol.lower()}{provider.lower()[:2]}p{pid}plp{plp}"
                        label_full = f"{provider} {freq}{pol} PID{pid} PLP{plp}"
                        
                        bouquet.append(f"#SERVICE 1:64:0:0:0:0:0:0:0:0:\n#DESCRIPTION --- {label_full} ---")

                        block = (f"-- {label_full}\n{var_name} = make_t2mi_decap({{\n"
                                 f"    name = \"decap_{var_name}\",\n"
                                 f"    input = \"http://127.0.0.1:8001/1:0:1:{s_ref_core}:0:0:0:\",\n"
                                 f"    plp = {plp},\n    pnr = 0,\n    pid = {pid},\n}})\n"
                                 f"make_channel({{\n    name = \"{label_full}\",\n"
                                 f"    input = {{ \"t2mi://decap_{var_name}\", }},\n"
                                 f"    output = {{ \"http://0.0.0.0:9999/{path}/{freq}_{sat_pos}{sat_dir.lower()}_plp{plp}\", }},\n}})\n")
                        astra_blocks.append(block)

                        # CSV Logic
                        orbital_folder = f"{sat_pos}{sat_dir.upper()}"
                        csv_dir = os.path.join("channellist", orbital_folder)
                        suggestions = sorted([f for f in os.listdir(csv_dir) if f.lower().endswith('.csv')]) if os.path.isdir(csv_dir) else []

                        print(f"\n{Color.YELLOW}┌── {Color.BOLD}SUB-CHANNEL MAPPING: PID {pid} PLP {plp}{Color.END}{Color.YELLOW} " + "─" * 40 + "┐")
                        if suggestions:
                            for idx, fname in enumerate(suggestions, 1):
                                print(f"│ {Color.CYAN} [{idx}] {fname.ljust(72)}{Color.END}{Color.YELLOW} │")
                        print(f"└" + "─" * 78 + "┘" + Color.END)

                        ch_choice = pt_prompt(f"  Select file [#] or path for {orbital_folder} PLP {plp}: ", completer=path_completer, history=history).strip()
                        if ch_choice.lower() == "back": raise GoBack()

                        ch_file = os.path.join(csv_dir, suggestions[int(ch_choice) - 1]) if ch_choice.isdigit() and 1 <= int(ch_choice) <= len(suggestions) else ch_choice

                        if ch_file and os.path.isfile(ch_file):
                            sub_url = f"http://0.0.0.0:9999/{path}/{freq}_{sat_pos}{sat_dir.lower()}_plp{plp}".replace(":", "%3a")
                            with open(ch_file, "r", encoding="utf8") as f:
                                for line in f:
                                    if "," not in line: continue
                                    try:
                                        csid, name, stype = [x.strip() for x in line.split(",")]
                                        c_ref = f"1:0:{stype}:{format(int(csid), 'x').lower()}:{tsid_no_lead}:{onid_no_lead}:{ns_hex}:0:0:0:{sub_url}:{name}"
                                        bouquet.append(f"#SERVICE {c_ref}\n#DESCRIPTION {name}")
                                        print(f"    {Color.GREEN}✔ Added: {name}{Color.END}")
                                    except: continue

                if ask("Add another transponder?", "n", "y = Add transponder | n = Finalize generation.", "❓") == "y":
                    step = 4
                    continue
                break

        except GoBack:
            step = max(1, step - 1)
            clear_screen()
            print_header()
            print(f"\n{Color.RED}↩ REVERTING TO PREVIOUS STEP...{Color.END}")

    # ==================================================================
    # FINAL COMPILATION: SURGICAL MERGE & BACKUP
    # ==================================================================
    for i in range(0, 101, 20): draw_progress(i, task="Syncing Database")

    # 1. Backup Protocol
    if os.path.isfile(merge_path):
        try:
            timestamp = time.strftime("%Y%m%d_%H%M%S")
            backup_name = f"{merge_path}_{timestamp}.bak"
            shutil.copy2(merge_path, backup_name)
            print(f"\n  {Color.GREEN}💾 BACKUP CREATED: {backup_name}{Color.END}")
        except Exception as e:
            print(f"\n  {Color.RED}⚠ BACKUP FAILED: {str(e)}{Color.END}")

    # 2. Load DB Lines
    if os.path.isfile(merge_path):
        with open(merge_path, "r", encoding="utf-8", errors="ignore") as f:
            db_lines = [line.rstrip() for line in f.readlines()]
    else:
        db_lines = ["eDVB services /4/", "transponders", "end", "services", "end"]

    # 3. Surgical Transponder Merge
    try:
        tp_idx = db_lines.index("transponders")
        for key, block in new_tps.items():
            for idx, line in enumerate(db_lines):
                if line.startswith(key):
                    del db_lines[idx:idx+3]
                    break
            db_lines.insert(tp_idx + 1, block.strip())
    except ValueError: pass

    # 4. Surgical Services Merge
    try:
        srv_idx = db_lines.index("services")
        for key, block in new_srvs.items():
            for idx, line in enumerate(db_lines):
                if line.startswith(key):
                    del db_lines[idx:idx+3]
                    break
            db_lines.insert(srv_idx + 1, block.strip())
    except ValueError: pass

    # 5. Local Save
    with open("lamedb", "w", encoding="utf-8", newline='\n') as f:
        f.write("\n".join(db_lines) + "\n")

    # 6. Live Swap Protocol
    swap_applied = False
    if os.path.abspath(merge_path) != os.path.abspath("./lamedb"):
        print(f"\n{Color.YELLOW}┌── {Color.BOLD}LIVE DATABASE SWAP{Color.END}{Color.YELLOW} " + "─" * 57 + "┐")
        print(f"│ {Color.CYAN}Apply these edits to the source file now?{' ' * 36}{Color.END}{Color.YELLOW}│")
        b_disp = os.path.basename(backup_name) if 'backup_name' in locals() else "N/A"
        print(f"│ {Color.BLUE}ℹ Verified Backup: {b_disp.ljust(53)}{Color.END}{Color.YELLOW} │")
        print(f"└" + "─" * 78 + "┘" + Color.END)
        
        swap_choice = ask("Update source lamedb?", "n", "y = Overwrite original file | n = Keep edits locally", "🔄")
        if swap_choice.lower() == "y":
            try:
                shutil.copy2("lamedb", merge_path)
                swap_applied = True
                print(f"  {Color.GREEN}✨ SUCCESS: {merge_path} updated.{Color.END}")
            except Exception as e:
                print(f"  {Color.RED}✖ SWAP FAILED: {str(e)}{Color.END}")

    # 7. Bouquet & Astra Save
    with open(bouquet_file, "w") as f: f.write(f"#NAME {bouquet_name}\n" + "\n".join(bouquet) + "\n")
    if not os.path.exists("astra"): os.makedirs("astra")
    with open("astra/astra.conf", "w") as f: f.write("-- [ ARCHITECT GENERATED CONFIG ] --\n" + "\n".join(astra_blocks))

    # 8. Completion UI
    draw_progress(100, task="Architecture Locked")
    print(f"\n\n{Color.GREEN}{Color.BOLD}✅ v9.7 ENCYCLOPEDIA ARCHITECT SUCCESSFUL!{Color.END}")
    print(f"{Color.CYAN}📂 LOCAL WORKSPACE : ./lamedb")
    if 'backup_name' in locals(): print(f"📂 SOURCE BACKUP   : {backup_name}")
    if swap_applied: print(f"📂 LIVE DATABASE   : {merge_path} {Color.BOLD}(UPDATED){Color.END}")
    else: print(f"📂 SOURCE TARGET   : {merge_path} {Color.BOLD}(UNTOUCHED){Color.END}")
    print(f"📂 BOUQUET         : ./{bouquet_file}")
    print(f"📂 ASTRA           : ./astra/astra.conf{Color.END}\n")

except KeyboardInterrupt:
    exit_gracefully()
