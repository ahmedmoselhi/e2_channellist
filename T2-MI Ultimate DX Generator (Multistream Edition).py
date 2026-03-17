import os
import sys
import shutil
import time
import csv
import re
import subprocess

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
    UNDERLINE = '\033[4m'
    END = '\033[0m'

# ----------------------------------------------------------------------
# Environment Initialization
# ----------------------------------------------------------------------
def ensure_dependencies():
    # Attempt to initialize colorama for cross-platform ANSI support
    try:
        import colorama
        colorama.init()
    except ImportError:
        try:
            subprocess.check_call([sys.executable, "-m", "pip", "install", "colorama"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            import colorama
            colorama.init()
        except: pass

    try:
        from prompt_toolkit import prompt as pt_prompt
        from prompt_toolkit.history import FileHistory
        from prompt_toolkit.shortcuts import radiolist_dialog
        from prompt_toolkit.completion import PathCompleter
        from prompt_toolkit.formatted_text import ANSI
        return pt_prompt, FileHistory, radiolist_dialog, PathCompleter, ANSI
    except ImportError:
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
            from prompt_toolkit.formatted_text import ANSI
            print(f"{Color.GREEN}✅ Success! Environment Prepared.{Color.END}\n")
            return pt_prompt, FileHistory, radiolist_dialog, PathCompleter, ANSI
        except Exception:
            print(f"{Color.RED}❌ Failed to initialize environment.{Color.END}")
            print(f"Please run: {Color.BOLD}python -m pip install prompt_toolkit colorama{Color.END}")
            sys.exit(1)

# Initialize the toolkit
pt_prompt, FileHistory, radiolist_dialog, PathCompleter, ANSI = ensure_dependencies()
history = FileHistory(".dx_history")

# ----------------------------------------------------------------------
# UI Helper Functions
# ----------------------------------------------------------------------
def clear_screen():
    os.system('cls' if os.name == 'nt' else 'clear')

def exit_gracefully():
    print(f"\n\n{Color.RED}⚠ PROCESS ABORTED BY OPERATOR (Ctrl+C).{Color.END}")
    print(f"{Color.YELLOW}System state preserved. Exiting The Encyclopedia Architect...{Color.END}")
    sys.exit(0)

def print_header():
    print(f"{Color.BLUE}{Color.BOLD}" + "═"*80)
    print(r"""
  _______ ___       __  __ ___   _   _ _   _ _   _ __  __  _   _____ _____ 
 |__   __|__ \     |  \/  |_ _| | | | | | | | | | |  \/  |/ \ |_   _| ____|
    | |     ) |____| |\/| || |  | | | | | | | | | | |\/| / _ \  | | |  _|  
    | |    / /|____| |  | || |  | |_| | |_| | |_| | |  |/ ___ \ | | | |___ 
    |_|   |___|    |_|  |_|___|  \___/ \___/ \___/|_|  /_/   \_\|_| |_____|
                                                                           
               v9.7 - [ THE ENCYCLOPEDIA ARCHITECT ]
               RESTORED VERSION: HELPER TEXTS ENABLED
    """)
    print("═"*80 + f"{Color.END}")

def draw_progress(percent, width=40, task="Processing"):
    filled = int(width * percent / 100)
    bar = "█" * filled + "▒" * (width - filled)
    sys.stdout.write(f"\r  {Color.CYAN}{task.ljust(22)}: {Color.BOLD}[{bar}]{Color.END} {percent}%")
    sys.stdout.flush()
    time.sleep(0.01)

def ask(prompt_text, default=None, help_text="", icon="", allow_back=True):
    while True:
        print(f"\n{Color.YELLOW}╭──────────────────────────────────────────────────────────────────────────────╮")
        
        # Format Help Text
        lines = help_text.strip().split('\n')
        for line in lines:
            print(f"│ {Color.BLUE}{icon} {line.ljust(74)}{Color.END}{Color.YELLOW} │")
            
        if allow_back:
            back_info = "󰌍  Type 'back' to return to the previous configuration step."
            print(f"│ {Color.CYAN}{back_info.ljust(76)}{Color.END}{Color.YELLOW} │")
        
        # Status Line
        status = f"[ DEFAULT: {default} ]" if default is not None else "[ ACTION REQUIRED ]"
        print(f"├──────────────────────────────────────────────────────────────────────────────┤")
        print(f"│ {Color.GREEN}STATUS: {status.ljust(68)}{Color.END}{Color.YELLOW} │")
        print(f"╰──────────────────────────────────────────────────────────────────────────────╯{Color.END}")
        
        # Wrapping prompt with ANSI class prevents escape codes appearing as text
        val = pt_prompt(ANSI(f"  {Color.BOLD}{prompt_text}{Color.END}: "), history=history).strip()

        if val.lower() == "back" and allow_back:
            raise GoBack()
        if val == "" and default is not None: return default
        if val != "": return val
        print(f"  {Color.RED}❌ ERROR: This field cannot be empty. Database integrity at risk.{Color.END}")

def choose_option(title, text, options, default=None):
    result = radiolist_dialog(
        title=f" ARCHITECT SELECTION: {title} ",
        text=f"\n{text}\n\nNavigation: [Tab] Move | [Space/Enter] Select\n",
        values=options,
        default=default
    ).run()
    if result is None: raise GoBack()
    return result

# ----------------------------------------------------------------------
# Main Execution Logic
# ----------------------------------------------------------------------
try:
    clear_screen()
    print_header()

    path_completer = PathCompleter(expanduser=True)
    new_tps, new_srvs, bouquet, astra_blocks = {}, {}, [], []
    used_csv, ONID = False, "0001"
    step = 1

    while True:
        try:
            if step == 1:
                cleanup = ask(
                    "Clean workspace?", "n", 
                    "Choose whether to wipe existing generated files to prevent data mixing.\n"
                    "y = YES (Deletes lamedb, astra folder, and userbouquets)\n"
                    "n = NO (Performs a safe merge with existing data)", 
                    "🧹", allow_back=False
                )
                if cleanup.lower() == 'y':
                    for i in range(0, 101, 10): draw_progress(i, task="Wiping Environment")
                    for f in os.listdir('.'):
                        if (f.startswith('userbouquet.') and f.endswith('.tv')) or f == 'lamedb':
                            try: os.remove(f)
                            except: pass
                    if os.path.exists('astra'): shutil.rmtree('astra')
                step = 2

            elif step == 2:
                print(f"\n{Color.YELLOW}┌── {Color.BOLD}DATABASE SOURCE SELECTION{Color.END}{Color.YELLOW} " + "─" * 47 + "┐")
                print(f"│ {Color.BLUE}📂 Provide path to your existing lamedb for merging.                      {Color.END}{Color.YELLOW} │")
                print(f"│ {Color.BLUE}💡 Press [ENTER] to create a fresh './lamedb' in this folder.             {Color.END}{Color.YELLOW} │")
                print(f"│ {Color.BLUE}⬅️  Type 'back' to return to Workspace Cleanup.                            {Color.END}{Color.YELLOW} │")
                print(f"└" + "─" * 78 + "┘" + Color.END)
                merge_path = pt_prompt(ANSI("  Source lamedb path: "), completer=path_completer, history=history).strip() or "./lamedb"
                if merge_path.lower() == "back": step = 1; continue
                step = 3

            elif step == 3:
                bouquet_name = ask(
                    "Bouquet Name", "T2MI DX", 
                    "The label that will appear in your Enigma2 Favorites list.\n"
                    "Spaces will be converted to underscores for the filename.", 
                    "🏷️"
                )
                bouquet_file = f"userbouquet.{bouquet_name.lower().replace(' ', '_')}.tv"
                step = 4

            elif step == 4:
                freq_dir = "frequencies"
                csv_files = [f for f in os.listdir(freq_dir) if f.endswith('.csv')] if os.path.exists(freq_dir) else []
                
                if csv_files:
                    options = [("manual", ">> MANUAL ENTRY (Input parameters by hand)")] + [(f, f"📄 {f}") for f in csv_files]
                    choice = choose_option(
                        "Frequency Database", 
                        "Select a pre-configured CSV for automatic transponder parameter loading:", 
                        options, "manual"
                    )
                    
                    if choice != "manual" and choice is not None:
                        with open(os.path.join(freq_dir, choice), 'r', encoding='utf-8') as f:
                            reader = list(csv.DictReader(f))
                        
                        print(f"\n{Color.YELLOW}┌── {Color.BOLD}SELECT TRANSPONDER FROM DATABASE{Color.END}{Color.YELLOW} " + "─"*40 + "┐")
                        for idx, r in enumerate(reader):
                            label = f"{r['Freq']} {r['Pol']} ({r['Pos']}{r['Dir']}) SR:{r['SR']}"
                            print(f"│ {Color.CYAN} [{idx}] {label.ljust(72)}{Color.END}{Color.YELLOW} │")
                        print(f"└" + "─" * 78 + "┘" + Color.END)
                        
                        tp_idx_str = ask("Select TP Index [#]", "0", "Enter the numeric index from the list above.", "📡")
                        row = reader[int(tp_idx_str)]
                        
                        freq = int(row['Freq'])
                        raw_pol = row['Pol'].upper()
                        pol = {"2": "L", "3": "R", "0": "H", "1": "V"}.get(raw_pol, raw_pol)
                        sr = int(row['SR'])
                        sat_pos, sat_dir = float(row['Pos']), row['Dir'].upper()
                        inv, fec, sys_type, mod = row['Inv'], row['FEC'], row['Sys'], row['Mod']
                        roll, pilot = row['RO'], row['Pilot']
                        
                        raw_sat = int(sat_pos * 10)
                        ns_sat = (3600 - raw_sat) if sat_dir == "W" else raw_sat
                        disp_sat = -raw_sat if sat_dir == "W" else raw_sat
                        ns_hex = format((ns_sat << 16) | freq, '08x').lower()

                        print(f"\n{Color.GREEN}✅ LOADED: {freq} {pol} {sat_pos}{sat_dir} (Hex: {ns_hex}){Color.END}")
                        used_csv = True
                        step = 15; continue

                freq = int(ask(
                    "Frequency (MHz)", "4014", 
                    "Enter Downlink Frequency.\n"
                    "Common Examples: 4014 (C-Band), 11495 (Ku-Band).", 
                    "📡"
                ))
                step = 5

            elif step == 5:
                sr = int(ask(
                    "Symbol Rate", "15284", 
                    "Enter the Symbol Rate (SR) of the carrier.\n"
                    "Common: 15284, 30000, 45000.", 
                    "📶"
                ))
                step = 6

            elif step == 6:
                pol = choose_option(
                    "Polarization", 
                    "Select the physical antenna orientation for this transponder:", 
                    [("H", "Horizontal"), ("V", "Vertical"), ("L", "Left Circular"), ("R", "Right Circular")], "L"
                )
                step = 7

            elif step == 7:
                sat_pos = float(ask(
                    "Satellite Position", "18.1", 
                    "Orbital degree of the satellite.\n"
                    "Example: 18.1 (Intelsat), 4.9 (SES), 36.0 (Eutelsat).", 
                    "🌍"
                ))
                step = 8

            elif step == 8:
                sat_dir = ask(
                    "Direction (E/W)", "W", 
                    "Orbital hemisphere.\n"
                    "E = East | W = West.", 
                    "🧭"
                ).upper()
                raw_sat = int(sat_pos * 10)
                ns_sat = (3600 - raw_sat) if sat_dir == "W" else raw_sat
                disp_sat = -raw_sat if sat_dir == "W" else raw_sat
                ns_hex = format((ns_sat << 16) | freq, '08x').lower()
                step = 9

            elif step == 9:
                inv = ask(
                    "Inversion", "2", 
                    "Spectral inversion setting.\n"
                    "0 = OFF | 1 = ON | 2 = AUTO.", 
                    "🛠️"
                )
                step = 10

            elif step == 10:
                fec = choose_option(
                    "FEC", 
                    "Forward Error Correction ratio:", 
                    [("1","1/2"), ("2","2/3"), ("3","3/4"), ("4","5/6"), ("5","7/8"), ("6","8/9"), ("7","3/5"), ("8","4/5"), ("9","Auto")], "9"
                )
                step = 11

            elif step == 11:
                sys_type = ask(
                    "Transmission System", "1", 
                    "Standard used for the transponder.\n"
                    "0 = DVB-S (Old) | 1 = DVB-S2 (Modern).", 
                    "🛠️"
                )
                step = 12

            elif step == 12:
                mod = ask(
                    "Modulation", "2", 
                    "Signal modulation type.\n"
                    "1 = QPSK | 2 = 8PSK | 3 = 16APSK | 4 = 32APSK.", 
                    "🛠️"
                )
                step = 13

            elif step == 13:
                roll = ask(
                    "Roll-Off Factor", "0", 
                    "Filter slope width.\n"
                    "0 = 0.35 | 1 = 0.25 | 2 = 0.20.", 
                    "🛠️"
                )
                step = 14

            elif step == 14:
                pilot = ask(
                    "Pilot Mode", "2", 
                    "Pilot symbols for synchronization.\n"
                    "0 = OFF | 1 = ON | 2 = AUTO.", 
                    "🛠️"
                )
                step = 15

            elif step == 15:
                is_mis = ask(
                    "Enable Multistream?", "n", 
                    "Does this transponder carry multiple Input Streams (ISI)?\n"
                    "y = YES (Multi-ISI mode) | n = NO (Single Stream mode).", 
                    "🌊"
                )
                isi_input = ask(
                    "Stream IDs (ISIs)", "171", 
                    "Enter numeric IDs separated by commas.\n"
                    "Example: 171, 172, 173.", 
                    "🆔"
                ) if is_mis.lower() == 'y' else "-1"
                step = 16

            elif step == 16:
                sid = int(ask(
                    "Base Service ID (SID)", "800", 
                    "The starting virtual Service ID.\n"
                    "The script will auto-increment this for each stream/PID added.", 
                    "🆔"
                ))
                step = 17

            elif step == 17:
                provider = ask(
                    "Provider Label", "ORTM", 
                    "Corporate/Channel branding used in metadata.\n"
                    "Example: BBC, Canal+, Globecast.", 
                    "🏢"
                )
                step = 18

            elif step == 18:
                path = ask(
                    "Astra-SM Path", "ortm", 
                    "The URL slug for your Astra relay.\n"
                    "Result: http://0.0.0.0:9999/[path]/...", 
                    "🔗"
                )
                step = 19

            elif step == 19:
                b_len, a_len = len(bouquet), len(astra_blocks)
                tps_keys, srvs_keys = set(new_tps.keys()), set(new_srvs.keys())
                
                try:
                    p_digit = {"H":"0","V":"1","L":"2","R":"3"}.get(pol, "0")
                    current_sid = sid

                    for isi in [i.strip() for i in isi_input.split(",")]:
                        dyn_tsid = format(int(isi), '04x') if isi != "-1" else "0001"
                        tp_key = f"{ns_hex}:{dyn_tsid}:{ONID}"
                        new_tps[tp_key] = f"{tp_key}\n\ts {freq*1000}:{sr*1000}:{p_digit}:{fec}:{disp_sat}:{inv}:0:{sys_type}:{mod}:{roll}:{pilot}:{isi}\n/\n"
                        
                        pid_target = f"Stream {isi}" if isi != "-1" else "Transponder"
                        pid_help = f"Enter T2-MI Packet IDs for {pid_target}.\nComma-separated list (e.g. 4096, 4097)."
                        pid_input = ask(f"T2-MI PIDs for {pid_target}", "4096", pid_help, "🔢")
                        
                        for pid in [p.strip() for p in pid_input.split(",")]:
                            sid_hex, sid_no_lead = format(current_sid, '04x').lower(), format(current_sid, 'x').lower()
                            tsid_no_lead = format(int(dyn_tsid, 16), 'x').lower()
                            onid_no_lead = format(int(ONID, 16), 'x').lower()

                            s_ref_core = f"{sid_no_lead}:{tsid_no_lead}:{onid_no_lead}:{ns_hex}"
                            srv_key = f"{sid_hex}:{ns_hex}:{dyn_tsid}:{ONID}"

                            new_srvs[srv_key] = f"{srv_key}:1:0\n{provider} PID{pid} FEED\np:{provider},c:15{format(int(pid),'04x')},f:01\n"
                            bouquet.append(f"#SERVICE 1:0:1:{s_ref_core}:0:0:0:\n#DESCRIPTION {provider} PID{pid} FEED")

                            plp_target = f"ISI {isi} PID {pid}" if isi != "-1" else f"PID {pid}"
                            plps_input = ask(
                                f"PLPs for {plp_target}", "0", 
                                "Physical Layer Pipe IDs.\nComma-separated (e.g. 0, 1, 2).", 
                                "📺"
                            )
                            
                            for plp in [pl.strip() for pl in plps_input.split(",")]:
                                var_name = f"f{freq}{pol.lower()}{provider.lower()[:2]}p{pid}plp{plp}"
                                if isi != "-1": var_name += f"isi{isi}"
                                label_full = f"{provider} {freq}{pol} " + (f"ISI{isi} " if isi != "-1" else "") + f"PID{pid} PLP{plp}"
                                
                                bouquet.append(f"#SERVICE 1:64:0:0:0:0:0:0:0:0:\n#DESCRIPTION --- {label_full} ---")

                                block = (f"-- {label_full}\n{var_name} = make_t2mi_decap({{\n"
                                         f"    name = \"decap_{var_name}\",\n"
                                         f"    input = \"http://127.0.0.1:8001/1:0:1:{s_ref_core}:0:0:0:\",\n"
                                         f"    plp = {plp},\n    pnr = 0,\n    pid = {pid},\n}})\n"
                                         f"make_channel({{\n    name = \"{label_full}\",\n"
                                         f"    input = {{ \"t2mi://{var_name}\", }},\n"
                                         f"    output = {{ \"http://0.0.0.0:9999/{path}/{freq}_{sat_pos}{sat_dir.lower()}_plp{plp}\", }},\n}})\n")
                                astra_blocks.append(block)

                                orbital_folder = f"{sat_pos}{sat_dir.upper()}"
                                csv_dir = os.path.join("channellist", orbital_folder)
                                suggestions = sorted([f for f in os.listdir(csv_dir) if f.lower().endswith('.csv')]) if os.path.isdir(csv_dir) else []

                                title_text = f" SUB-CHANNEL MAPPING: PLP {plp} "
                                print(f"\n{Color.YELLOW}┌── {Color.BOLD}{title_text}{Color.END}{Color.YELLOW} " + "─" * (76-len(title_text)) + "┐")
                                if suggestions:
                                    for idx, fname in enumerate(suggestions, 1):
                                        print(f"│ {Color.CYAN} [{idx}] {fname.ljust(72)}{Color.END}{Color.YELLOW} │")
                                else:
                                    print(f"│ {Color.RED} ❌ No channel mapping CSVs found in {csv_dir.ljust(50)}{Color.END}{Color.YELLOW} │")
                                print(f"└" + "─" * 78 + "┘" + Color.END)

                                ch_choice = pt_prompt(ANSI(f"  Select Mapping File [#] or Path: "), completer=path_completer, history=history).strip()
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
                                                print(f"    {Color.GREEN}✔ Added Sub-Channel: {name}{Color.END}")
                                            except: continue
                            current_sid += 1

                    if ask("Add another Transponder?", "n", "y = Add more data | n = Finalize and Save.", "❓") == "y":
                        step = 4; continue
                    break
                    
                except GoBack:
                    bouquet = bouquet[:b_len]
                    astra_blocks = astra_blocks[:a_len]
                    for k in list(new_tps.keys()):
                        if k not in tps_keys: del new_tps[k]
                    for k in list(new_srvs.keys()):
                        if k not in srvs_keys: del new_srvs[k]
                    raise

        except GoBack:
            step = 4 if used_csv and step == 15 else max(1, step - 1)
            used_csv = False
            clear_screen(); print_header()
            print(f"\n{Color.RED}↩ REVERTING TO PREVIOUS CONFIGURATION STEP...{Color.END}")

    # --- Finalization Phase ---
    for i in range(0, 101, 20): draw_progress(i, task="Syncing Database")
    
    if os.path.exists(merge_path):
        with open(merge_path, 'r', encoding='utf-8', errors='ignore') as f:
            lines = f.readlines()
        
        content_str = "".join(lines)
        def insert_data(marker, data_dict):
            try:
                idx = next(i for i, l in enumerate(lines) if l.strip() == marker)
                for k, v in data_dict.items():
                    if k not in content_str: lines.insert(idx + 1, v)
            except StopIteration: pass

        insert_data("transponders", new_tps)
        insert_data("services", new_srvs)
        with open("lamedb", "w", encoding='utf-8') as f: f.writelines(lines)
    else:
        with open("lamedb", "w", encoding='utf-8') as f:
            f.write("eDVB services /4/\ntransponders\n" + "".join(new_tps.values()) + "end\nservices\n" + "".join(new_srvs.values()) + "end\n")

    with open(bouquet_file, "w") as f: 
        f.write(f"#NAME {bouquet_name}\n" + "\n".join(bouquet) + "\n")
    
    if not os.path.exists("astra"): os.makedirs("astra")
    with open("astra/astra.conf", "w") as f: 
        f.write("-- [ THE ENCYCLOPEDIA ARCHITECT GENERATED CONFIG ] --\n" + "\n".join(astra_blocks))

    draw_progress(100, task="Architecture Locked")
    print(f"\n\n{Color.GREEN}{Color.BOLD}✅ v9.7 ENCYCLOPEDIA ARCHITECT SUCCESSFUL!{Color.END}")
    print(f"{Color.CYAN}📂 Bouquet: {bouquet_file}")
    print(f"📂 Astra:   ./astra/astra.conf")
    print(f"📂 DB:      ./lamedb{Color.END}\n")

except KeyboardInterrupt:
    exit_gracefully()
