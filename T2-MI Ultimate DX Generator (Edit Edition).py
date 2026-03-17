import re
import os
import sys
import shutil
import time
import csv

# ----------------------------------------------------------------------
# Single GoBack exception definition (duplicate removed)
# ----------------------------------------------------------------------
class GoBack(Exception):
    """Raised when the user wants to return to the previous step."""
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

# --- CATEGORY-SPECIFIC HISTORY INITIALIZATION ---
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
# History & path completer initialised BEFORE ask() so the global
# reference is always available when the function is called.
# ----------------------------------------------------------------------
path_completer = PathCompleter(expanduser=True)
history = FileHistory(".dx_history")


# ----------------------------------------------------------------------
# Helper functions
# ----------------------------------------------------------------------
def parse_astra_configs():
    """Extract PLP and PID metadata from an existing astra.conf."""
    configs = {}
    conf_path = "astra/astra.conf"
    if os.path.exists(conf_path):
        with open(conf_path, "r", encoding="utf-8") as fh:
            content = fh.read()
            pattern = (
                r'(\w+)\s*=\s*make_t2mi_decap\({\s*.*?'
                r'plp\s*=\s*(\d+),.*?pid\s*=\s*(\d+),'
            )
            for var_name, plp, pid in re.findall(pattern, content, re.DOTALL):
                configs[var_name] = {"plp": plp, "pid": pid}
    return configs


def get_current_params(freq, pol, existing_astra):
    """Return stored PLP/PID for a given frequency+polarisation, or None."""
    key = f"f{freq}{pol.lower()}"
    for k, v in existing_astra.items():
        if k.startswith(key):
            return v
    return None


def clear_screen():
    os.system('cls' if os.name == 'nt' else 'clear')


def exit_gracefully():
    print(f"\n\n{Color.RED}⚠ Process interrupted by user (Ctrl+C).{Color.END}")
    print(f"{Color.YELLOW}Exiting The Encyclopedia Architect...{Color.END}")
    sys.exit(0)


def print_header():
    print(f"{Color.BLUE}{Color.BOLD}" + "=" * 80)
    print(r"""
  _______ ___       __  __ ___   _   _ _   _ _   _ __  __  _   _____ _____ 
 |__   __|__ \     |  \/  |_ _| | | | | | | | | | |  \/  |/ \ |_   _| ____|
    | |     ) |____| |\/| || |  | | | | | | | | | | |\/| / _ \  | | |  _|  
    | |    / /|____| |  | || |  | |_| | |_| | |_| | |  |/ ___ \ | | | |___ 
    |_|   |___|    |_|  |_|___|  \___/ \___/ \___/|_|  /_/   \_\|_| |_____|
                                                                           
               v9.7 - [ THE ENCYCLOPEDIA ARCHITECT ]
    """)
    print("=" * 80 + f"{Color.END}")


def draw_progress(percent, width=40, task="Processing"):
    filled = int(width * percent / 100)
    bar = "█" * filled + "░" * (width - filled)
    sys.stdout.write(
        f"\r  {Color.CYAN}{task.ljust(20)}: {Color.BOLD}[{bar}]{Color.END} {percent}%"
    )
    sys.stdout.flush()
    time.sleep(0.01)

def ask(prompt_text, default=None, help_text="", icon="ℹ", allow_back=True, category="default"):
    """Prompt the user with category-specific history from global dictionary."""
    while True:
        print(
            f"\n{Color.YELLOW}┌── {Color.BOLD}INPUT FIELD{Color.END}"
            f"{Color.YELLOW} " + "─" * 65 + "┐"
        )
        full_help = help_text
        if allow_back:
            full_help += "\n[ Type 'back' to return to the previous question ]"
        if default is not None:
            full_help += f"\n[ DEFAULT CHOICE: {default} ] (Press Enter to use default)"
        else:
            full_help += "\n[ REQUIRED FIELD: Manual entry necessary ]"

        for line in full_help.strip().split("\n"):
            print(
                f"│ {Color.BLUE}{icon} {line.ljust(74)}{Color.END}{Color.YELLOW} │"
            )
        print(f"└" + "─" * 78 + "┘" + Color.END)

        # Retrieve the pre-initialized history object for this category
        cat_history = history_files.get(category, history_files["default"])
        val = pt_prompt(f"  {prompt_text}: ", history=cat_history).strip()

        if val.lower() == "back" and allow_back:
            raise GoBack()
        if val == "" and default is not None:
            return default
        if val != "":
            return val
        print(
            f"  {Color.RED}⚠ ALERT: Value required for database integrity.{Color.END}"
        )

def choose_option(title, text, options, default=None):
    """Radiolist dialog shortcut."""
    return radiolist_dialog(
        title=title,
        text=text,
        values=options,
        default=default,
    ).run()

POL_MAP = {"H": 0, "V": 1, "L": 2, "R": 3}

# ======================================================================
# Main program
# ======================================================================
try:
    clear_screen()
    print_header()

    # Storage containers for generated data
    new_tps, new_srvs, bouquet, astra_blocks = {}, {}, [], []
    ONID, TSID = "0001", "0001"

    # ------------------------------------------------------------------
    # Pre-initialise every variable that later steps depend on so that
    # navigating backwards with "back" never triggers a NameError.
    # ------------------------------------------------------------------
    mode = "modify"
    existing_astra = {}
    merge_path = "./lamedb"
    bouquet_name = "T2MI DX"
    bouquet_file = "userbouquet.t2mi_dx.tv"
    freq = 4014
    pol = "L"
    current_cfg = None
    sr = 7325
    sat_pos = 18.1
    sat_dir = "W"
    inv = "2"
    fec = "9"
    sys_type = "1"
    mod = "2"
    roll = "0"
    pilot = "2"
    raw_sat = int(sat_pos * 10)
    ns_sat = (3600 - raw_sat) if sat_dir == "W" else raw_sat
    disp_sat = -raw_sat if sat_dir == "W" else raw_sat
    ns_hex = format((ns_sat << 16) | freq, '08x').lower()
    pid_input = "4096"
    plps_input = "0"
    sid = 800
    provider = "ORTM"
    path = "ortm"

    # ------------------------------------------------------------------
    # State machine
    # ------------------------------------------------------------------
    step = 1
    while True:
        try:
            # ==========================================================
            # STEP 1 – Session initialisation & mode selection
            # ==========================================================
            if step == 1:
                print(f"\n{Color.CYAN}╔" + "═" * 78 + "╗")
                print(
                    f"║ {Color.BOLD}ARCHITECT SESSION INITIALIZATION"
                    f"{Color.END}{Color.CYAN}".center(88) + "║"
                )
                print(f"╚" + "═" * 78 + "╝" + Color.END)

                mode = radiolist_dialog(
                    title="OPERATION MODE",
                    text="How should existing database files be handled?",
                    values=[
                        (
                            "modify",
                            "MODIFY/APPEND – read existing files and update matches.",
                        ),
                        (
                            "fresh",
                            "FRESH START – wipe everything and start a new database.",
                        ),
                    ],
                    default="modify",
                ).run()

                if mode is None:
                    sys.exit(0)

                if mode == "fresh":
                    print(
                        f"\n{Color.RED}⚠ WARNING: EXECUTING FULL WORKSPACE WIPE..."
                        f"{Color.END}"
                    )
                    for i in range(0, 101, 10):
                        draw_progress(i, task="Purging Data")
                    for filename in os.listdir('.'):
                        if (
                            filename.startswith('userbouquet.')
                            and filename.endswith('.tv')
                        ) or filename == 'lamedb':
                            try:
                                os.remove(filename)
                            except OSError:
                                pass
                    if os.path.isdir('astra'):
                        shutil.rmtree('astra')
                    print(
                        f"\n  {Color.GREEN}✨ Workspace cleaned successfully."
                        f"{Color.END}"
                    )
                else:
                    for i in range(0, 101, 20):
                        draw_progress(i, task="Parsing Files")
                    print(
                        f"\n  {Color.GREEN}📂 Existing database loaded into memory."
                        f"{Color.END}"
                    )

                existing_astra = (
                    parse_astra_configs() if mode == "modify" else {}
                )
                step = 2

            # ==========================================================
            # STEP 2 – Source lamedb path (LIVE EDIT ENABLED)
            # ==========================================================
            elif step == 2:
                print(
                    f"\n{Color.YELLOW}┌── {Color.BOLD}DATABASE SOURCE"
                    f"{Color.END}{Color.YELLOW} " + "─" * 61 + "┐"
                )
                print(
                    f"│ {Color.BLUE}📂 Path to existing lamedb for live editing."
                    f"{' ' * 31}{Color.END}{Color.YELLOW}│"
                )
                print(
                    f"│ {Color.BLUE}Press Enter to use the local ./lamedb workspace."
                    f"{' ' * 24}{Color.END}{Color.YELLOW}│"
                )
                print(
                    f"│ {Color.BLUE}ℹ Type 'back' to return to cleanup settings."
                    f"{' ' * 24}{Color.END}{Color.YELLOW}│"
                )
                print(f"└" + "─" * 78 + "┘" + Color.END)

                merge_input = pt_prompt(
                    "  Target lamedb path: ",
                    completer=path_completer,
                    history=history_files["paths"],
                ).strip()
                if merge_input.lower() == "back":
                    step = 1
                    continue
                merge_path = merge_input or "./lamedb"
                step = 3

            # ==========================================================
            # STEP 3 – Bouquet name
            # ==========================================================
            elif step == 3:
                bouquet_name = ask(
                    "Bouquet name",
                    "T2MI DX",
                    "Name of the favourites group in your channel list.",
                    "🏷️",
                    category="bouquet",
                )
                bouquet_file = (
                    f"userbouquet.{bouquet_name.lower().replace(' ', '_')}.tv"
                )
                step = 4

            # ==========================================================
            # STEP 4 – Frequency
            # ==========================================================
            elif step == 4:
                print(f"\n{Color.CYAN}╔" + "═" * 78 + "╗")
                print(
                    f"║ {Color.BOLD}THE ARCHITECT: SELECTIVE PARAMETER "
                    f"SYNCHRONIZATION{Color.END}{Color.CYAN}".center(88) + "║"
                )
                print(
                    f"║ {Color.BLUE}v10.0 'Elite Edit' Protocol Active"
                    .center(86) + f"{Color.CYAN} ║"
                )
                print(f"╚" + "═" * 78 + "╝" + Color.END)

                freq_help = (
                    f"{Color.BOLD}PRIMARY DATABASE KEY{Color.END}\n"
                    "Enter the transponder frequency in MHz.\n"
                    "───────────────────────┬──────────────────────\n"
                    " Range                │ 2000–13000 MHz\n"
                    " Standard (C‑Band)   │ 3400–4200 MHz\n"
                    " Standard (Ku‑Band)  │ 10700–12700 MHz\n"
                    "───────────────────────┴──────────────────────"
                )
                # --- v9.9 EDIT EDITION CSV IMPORT LOGIC ---
                freq_dir = "frequencies"
                csv_files = [f for f in os.listdir(freq_dir) if f.endswith('.csv')] if os.path.exists(freq_dir) else []

                if csv_files:
                    print(f"\n{Color.CYAN}📂 Frequency Database Browser{Color.END}")
                    options = [("manual", "Manual Entry")] + [(f, f) for f in csv_files]
                    choice = choose_option("Import Source", "Select a CSV file or proceed Manually:", options, "manual")
                    
                    if choice != "manual" and choice is not None:
                        with open(os.path.join(freq_dir, choice), 'r', encoding='utf-8') as f:
                            reader = list(csv.DictReader(f))
                        
                        print(f"\n{Color.YELLOW}┌── {Color.BOLD}SELECT TRANSPONDER FROM CSV{Color.END}{Color.YELLOW} " + "─"*45 + "┐")
                        for idx, r in enumerate(reader):
                            label = f"{r['Freq']} {r['Pol']} ({r['Pos']}{r['Dir']}) SR:{r['SR']}"
                            print(f"│ {Color.CYAN} [{idx}] {label.ljust(72)}{Color.END}{Color.YELLOW} │")
                        print(f"└" + "─" * 78 + "┘" + Color.END)
                        
                        tp_idx_str = ask("Select TP Index [#]", "0", "Choose a transponder to load parameters.", "📡")
                        selected_row = reader[int(tp_idx_str)]
                        
                        # --- AUTO-FILL MAPPING ---
                        freq     = int(selected_row['Freq'])
                        # FIX: Map CSV numeric Pol to Character for POL_MAP compatibility
                        raw_pol  = selected_row['Pol'].upper()
                        pol      = {"2": "L", "3": "R", "0": "H", "1": "V"}.get(raw_pol, raw_pol)
                        
                        sr       = int(selected_row['SR'])
                        sat_pos  = float(selected_row['Pos'])
                        sat_dir  = selected_row['Dir'].upper()
                        inv      = selected_row['Inv']
                        fec      = selected_row['FEC']
                        sys_type = selected_row['Sys']
                        mod      = selected_row['Mod']
                        roll     = selected_row['RO']
                        pilot    = selected_row['Pilot']

                        # --- NEW: PID/PLP SYNC FIX ---
                        # This ensures the script has the values needed for Step 10
                        pid_input  = selected_row.get('PID', '4096')
                        plps_input = selected_row.get('PLP', '0')
                        
                        # --- CALCULATION FIX ---
                        raw_sat = int(sat_pos * 10)
                        ns_sat = (3600 - raw_sat) if sat_dir == "W" else raw_sat
                        disp_sat = -raw_sat if sat_dir == "W" else raw_sat
                        ns_hex = format((ns_sat << 16) | freq, '08x').lower()

                        # NEW: Trigger Elite Edit detection for CSV imports
                        current_cfg = get_current_params(freq, pol, existing_astra)

                        print(f"\n{Color.GREEN}✅ Tuning Data Loaded: {freq} {pol} {sat_pos}{sat_dir}{Color.END}")
                        print(f"{Color.YELLOW}🛰️ Jumping to T2-MI PID Configuration...{Color.END}")
                        
                        # CHANGE THIS: Jump to Step 7 (PID selection) instead of Step 9
                        step = 7
                        continue

                freq = int(ask("Target Frequency", "4014", freq_help, "📡", category="freq"))
                step = 5

            # ==========================================================
            # STEP 5 – Polarisation
            # ==========================================================
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
                pol = choose_option(
                    "Polarization",
                    pol_text,
                    [
                        ("H", "Horizontal (18V)"),
                        ("V", "Vertical (13V)"),
                        ("L", "Left Circular"),
                        ("R", "Right Circular"),
                    ],
                    default="L",
                )
                if pol is None:
                    step = 4
                    continue

                current_cfg = get_current_params(freq, pol, existing_astra)
                if current_cfg:
                    print(f"\n{Color.GREEN}┏" + "━" * 76 + "┓")
                    print(
                        f"┃ {Color.BOLD}RECOGNIZED SIGNATURE FOUND IN ASTRA.CONF"
                        f"{Color.END}{Color.GREEN} ".ljust(85) + "┃"
                    )
                    print(f"┠" + "─" * 76 + "┨")
                    print(
                        f"┃ {Color.CYAN}💠 FREQUENCY : {freq} MHz"
                        .ljust(85) + f"{Color.GREEN}┃"
                    )
                    print(
                        f"┃ {Color.CYAN}💠 T2‑MI PID : {current_cfg['pid']}"
                        .ljust(85) + f"{Color.GREEN}┃"
                    )
                    print(
                        f"┃ {Color.CYAN}💠 PLP ID    : {current_cfg['plp']}"
                        .ljust(85) + f"{Color.GREEN}┃"
                    )
                    print(f"┗" + "━" * 76 + "┛" + Color.END)
                else:
                    print(
                        f"\n{Color.YELLOW}⚡ [ NEW DISCOVERY ] No matching "
                        f"parameters found. Initialising…{Color.END}"
                    )
                step = 6

            # ==========================================================
            # STEP 6 – Physical layer (RF) parameters
            # ==========================================================
            elif step == 6:
                tp_help = (
                    f"{Color.BOLD}PHYSICAL LAYER GATEWAY{Color.END}\n"
                    "Edit the RF parameters of the transponder?\n"
                    "y – edit Symbol Rate, Satellite Position, FEC, etc.\n"
                    "n – keep system defaults."
                )
                edit_tp = ask("Modify Physical Layer?", "n", tp_help, "⚙️")

                if edit_tp.lower() == "y":
                    sr = int(
                        ask(
                            "Symbol Rate (kS/s)",
                            "7325",
                            "Typical values: 27500, 30000, 7325.",
                            "📶",
                        )
                    )
                    sat_pos = float(
                        ask(
                            "Orbital Position",
                            "18.1",
                            "Satellite longitude (e.g. 4.9, 18.1, 36.0).",
                            "🌍",
                        )
                    )
                    sat_dir = ask(
                        "Direction (E/W)", "W", "E – East, W – West.", "🧭"
                    ).upper()
                    inv = ask(
                        "Inversion",
                        "2",
                        "0 = Off | 1 = On | 2 = Auto‑Detect.",
                        "🛠️",
                    )

                    fec_help = (
                        f"{Color.BOLD}FEC (FORWARD ERROR CORRECTION){Color.END}\n"
                        "Choose redundancy level.\n"
                        "1/2  2/3  3/4  5/6  7/8  8/9  3/5  4/5  Auto"
                    )
                    fec = choose_option(
                        "FEC Ratio",
                        fec_help,
                        [
                            ("1", "1/2"), ("2", "2/3"), ("3", "3/4"),
                            ("4", "5/6"), ("5", "7/8"), ("6", "8/9"),
                            ("7", "3/5"), ("8", "4/5"), ("9", "Auto"),
                        ],
                        default="9",
                    )

                    sys_type = ask(
                        "Delivery System",
                        "1",
                        "0 = DVB‑S (Legacy) | 1 = DVB‑S2 (T2‑MI).",
                        "🏗️",
                    )
                    mod = ask(
                        "Modulation Type",
                        "2",
                        "1 = QPSK | 2 = 8PSK | 3 = 16APSK | 4 = 32APSK",
                        "💠",
                    )
                    roll = ask(
                        "Roll‑Off Factor",
                        "0",
                        "0 = 0.35 (DVB‑S) | 1 = 0.25 | 2 = 0.20 (DVB‑S2).",
                        "🌊",
                    )
                    pilot = ask(
                        "Pilot Tones",
                        "2",
                        "0 = Off | 1 = On | 2 = Auto.",
                        "🔦",
                    )
                else:
                    (sr, sat_pos, sat_dir, inv, fec,
                     sys_type, mod, roll, pilot) = (
                        7325, 18.1, "W", "2", "9", "1", "2", "0", "2"
                    )

                raw_sat = int(sat_pos * 10)
                ns_sat = (3600 - raw_sat) if sat_dir == "W" else raw_sat
                disp_sat = -raw_sat if sat_dir == "W" else raw_sat
                ns_hex = format((ns_sat << 16) | freq, '08x').lower()
                step = 7

            # ==========================================================
            # STEP 7 – Transport layer (PID)
            # ==========================================================
            elif step == 7:
                # Prioritize existing config, otherwise trust the variable in memory (CSV or default)
                cur_pid = (
                    current_cfg['pid'] if current_cfg else pid_input
                )
                pid_gate_help = (
                    f"{Color.BOLD}TRANSPORT LAYER GATEWAY{Color.END}\n"
                    f"Current PID: {Color.YELLOW}{cur_pid}{Color.END}\n"
                    "y – change the T2‑MI PID\n"
                    "n – keep the current value"
                )
                edit_pid = ask(
                    "Modify T2‑MI PID?", "n", pid_gate_help, "∆¶×"
                )
                pid_input = (
                    ask(
                        "Enter T2‑MI PID",
                        cur_pid,
                        "Packet Identifier for the T2‑MI stream "
                        "(e.g. 4096, 500, 1000).",
                        "∆¶×",
                        category="pid",
                    )
                    if edit_pid.lower() == "y"
                    else cur_pid
                )
                step = 9

            # ==========================================================
            # STEP 8 – Data layer (PLP)
            # ==========================================================
            #elif step == 8:
                #cur_plp = (
                    #current_cfg['plp'] if current_cfg else "0"
                #)
                #plp_gate_help = (
                    #f"{Color.BOLD}DATA PIPE GATEWAY{Color.END}\n"
                    #f"Current PLP: {Color.YELLOW}{cur_plp}{Color.END}\n"
                    #"y – edit PLP IDs\n"
                    #"n – keep the current mapping"
                #)
                #edit_plp = ask(
                    #"Modify PLP Pipe?", "n", plp_gate_help, "📺"
                #)
                #plps_input = (
                    #ask(
                        #"Enter PLP IDs",
                        #cur_plp,
                        #"Pipe IDs (0–255). Single (0) or comma‑separated "
                        #"list (0,1,2).",
                        #"📺",
                    #)
                    #if edit_plp.lower() == "y"
                    #else cur_plp
                #)
                #step = 9

            # ==========================================================
            # STEP 9 – Service metadata
            # ==========================================================
            elif step == 9:
                print(
                    f"\n{Color.CYAN}┌── {Color.BOLD}FINALIZING IDENTITY "
                    f"ARCHITECTURE{Color.END}{Color.CYAN} " + "─" * 45 + "┐"
                )
                sid = int(
                    ask(
                        "Feed SID",
                        "800",
                        "Service ID (decimal) used by Enigma2.",
                        "🆔",
                        category="sid",
                    )
                )
                provider = ask(
                    "Provider Name",
                    "ORTM",
                    "Broadcaster name (e.g. ORTM, TNT).",
                    "🏢",
                    category="provider",
                )
                path = ask(
                    "Relay Path",
                    "ortm",
                    "URL segment for streaming (affects m3u).",
                    "🔗",
                )
                print(f"└" + "─" * 78 + "┘" + Color.END)
                step = 10

            # ==========================================================
            # STEP 10 – Build transponder, services, bouquet & Astra
            # ==========================================================
            elif step == 10:
                # ---- Transponder entry ----
                tp_key = f"{ns_hex}:{TSID}:{ONID}"
                new_tps[tp_key] = (
                    f"{ns_hex}:{TSID}:{ONID}\n"
                    f"\ts {freq}000:{sr}000:{POL_MAP[pol]}:{fec}:"
                    f"{disp_sat}:{inv}:{sys_type}:{mod}:{roll}:{pilot}:0\n"
                    "/\n"
                )

                pids = [
                    p.strip() for p in pid_input.split(",") if p.strip()
                ]

                print(f"\n{Color.CYAN}╔" + "═" * 78 + "╗")
                print(
                    f"║ {Color.BOLD}TRANSPORT LAYER DE‑ENCAPSULATION: "
                    f"{len(pids)} PID(s) DETECTED{Color.END}{Color.CYAN}"
                    .center(88) + "║"
                )
                print(
                    f"║ {Color.BLUE}Initializing routing protocols for "
                    f"T2‑MI streams…{Color.END}".center(86) + "║"
                )
                print(f"╚" + "═" * 78 + "╝" + Color.END)

                sid_hex = format(sid, 'x').lower()
                tsid_hex = format(int(TSID, 16), 'x').lower()
                onid_hex = format(int(ONID, 16), 'x').lower()

                for pid in pids:
                    pid_hex = format(int(pid), '04x')
                    srv_key = f"{sid_hex}:{ns_hex}:{TSID}:{ONID}"
                    s_ref_core = (
                        f"{sid_hex}:{tsid_hex}:{onid_hex}:{ns_hex}"
                    )

                    # ---- Service entry ----
                    new_srvs[srv_key] = (
                        f"{srv_key}:1:0\n"
                        f"{provider} PID{pid} FEED\n"
                        f"p:{provider},c:15{pid_hex},f:01\n"
                    )

                    # ---- Master feed in bouquet ----
                    bouquet.append(
                        f"#SERVICE 1:0:1:{s_ref_core}:0:0:0:\n"
                        f"#DESCRIPTION {provider} PID{pid} FEED"
                    )

                    # ---- Find existing PLP for this PID ----
                    found_plp = "0"
                    search_stub = f"f{freq}{pol.lower()}"
                    for k, v in existing_astra.items():
                        if k.startswith(search_stub) and f"p{pid}" in k:
                            found_plp = v.get('plp', "0")
                            break

                    # ---- PLP configuration UI ----
                    plp_help = (
                        f"{Color.BOLD}PHYSICAL LAYER PIPE (PLP) "
                        f"ASSIGNMENT{Color.END}\n"
                        f"Targeting PID: {Color.GREEN}{pid}{Color.END}\n"
                        "Enter PLP IDs (comma‑separated, 0–255)."
                    )
                    print(
                        f"\n{Color.YELLOW}┌── {Color.BOLD}DATA PIPE "
                        f"ARCHITECTURE: PID {pid}{Color.END}{Color.YELLOW} "
                        + "─" * (76 - len(str(pid)) - 23) + "┐"
                    )
                    plps_input = ask(
                        f"PLPs for PID {pid}", found_plp, plp_help, "📺"
                    )

                    for plp in [
                        p.strip()
                        for p in plps_input.split(",")
                        if p.strip()
                    ]:
                        var_name = (
                            f"f{freq}{pol.lower()}"
                            f"{provider.lower()[:2]}p{pid}plp{plp}"
                        )
                        label = (
                            f"{provider} {freq}{pol} PID{pid} PLP{plp}"
                        )

                        # Visual separator in bouquet
                        bouquet.append(
                            f"#SERVICE 1:64:0:0:0:0:0:0:0:0:\n"
                            f"#DESCRIPTION --- {label} ---"
                        )

                        # ---- Astra configuration block ----
                        # NOTE: {{ / }} inside f-strings produce literal
                        # { / } in the output – this is intentional for
                        # the Lua config syntax that Astra expects.
                        block = (
                            f"-- {label}\n"
                            f"{var_name} = make_t2mi_decap({{\n"
                            f"    name = \"decap_{var_name}\",\n"
                            f"    input = \"http://127.0.0.1:8001/"
                            f"1:0:1:{sid_hex}:{tsid_hex}:{onid_hex}:"
                            f"{ns_hex}:0:0:0:\",\n"
                            f"    plp = {plp},\n"
                            f"    pnr = 0,\n"
                            f"    pid = {pid},\n"
                            f"}})\n"
                            f"make_channel({{\n"
                            f"    name = \"{label}\",\n"
                            f"    input = {{ \"t2mi://{var_name}\" }},\n"
                            f"    output = {{ \"http://0.0.0.0:9999/"
                            f"{path}/{freq}_{sat_pos}{sat_dir.lower()}_plp{plp}\" }},\n"
                            f"}})\n"
                        )
                        astra_blocks.append(block)

                        # ---- Sub‑channel CSV mapping ----
                        # Search for files in sub folder in channellist folder corresponding to orbital position
                        orbital_folder = f"{sat_pos}{sat_dir.upper()}"
                        csv_dir = os.path.join("channellist", orbital_folder)
                        
                        suggestions = []
                        if os.path.isdir(csv_dir):
                            # Added sorted() to ensure alphabetical order
                            suggestions = sorted([
                                fname
                                for fname in os.listdir(csv_dir)
                                if fname.lower().endswith('.csv')
                            ], key=lambda x: x.lower())

                        csv_help = (
                            f"{Color.BOLD}SUB‑CHANNEL MAPPING PROTOCOL"
                            f"{Color.END}\n"
                            f"Import virtual services for PID {pid} / "
                            f"PLP {plp}\n"
                            f"Auto‑scan found {len(suggestions)} CSV "
                            f"file(s) in ./{csv_dir}"
                        )
                        print(
                            f"\n{Color.YELLOW}┌── {Color.BOLD}SUB‑CHANNEL "
                            f"MAPPING: PID {pid} PLP {plp}{Color.END}"
                            f"{Color.YELLOW} "
                            + "─" * (
                                76 - 28
                                - len(str(pid))
                                - len(str(plp))
                            )
                            + "┐"
                        )
                        for line in csv_help.split("\n"):
                            # Helper texts preserved with exact ljust spacing from v5.0
                            print(
                                f"│ {Color.BLUE}📂 {line.ljust(74)}"
                                f"{Color.END}{Color.YELLOW} │"
                            )
                        if suggestions:
                            print(f"┠" + "─" * 78 + "┨")
                            for idx, fname in enumerate(suggestions, 1):
                                print(
                                    f"│ {Color.CYAN} [{idx}] "
                                    f"{fname.ljust(72)}{Color.END}"
                                    f"{Color.YELLOW} │"
                                )
                        print(f"└" + "─" * 78 + "┘" + Color.END)

                        ch_choice = pt_prompt(
                            f"  Select file [#] or path for {orbital_folder} PLP {plp}: ",
                            completer=path_completer,
                            history=history_files["paths"],
                        ).strip()

                        if ch_choice.lower() == "back":
                            raise GoBack()

                        # Resolve numeric shortcut within the orbital sub-folder
                        if (
                            ch_choice.isdigit()
                            and 1 <= int(ch_choice) <= len(suggestions)
                        ):
                            ch_file = os.path.join(
                                csv_dir,
                                suggestions[int(ch_choice) - 1],
                            )
                        else:
                            ch_file = ch_choice

                        if ch_file and os.path.isfile(ch_file):
                            sub_url = (
                                f"http://0.0.0.0:9999/{path}/"
                                f"{freq}_{sat_pos}{sat_dir.lower()}_plp{plp}"
                            ).replace(":", "%3a")
                            print(
                                f"  {Color.CYAN}⚙️  Parsing "
                                f"{os.path.basename(ch_file)}…{Color.END}"
                            )
                            with open(
                                ch_file, "r", encoding="utf8"
                            ) as fh:
                                for csv_line in fh:
                                    if "," not in csv_line:
                                        continue
                                    try:
                                        csid, name, stype = [
                                            x.strip()
                                            for x in csv_line.strip()
                                            .split(",")
                                        ]
                                        csid_hex = format(
                                            int(csid), 'x'
                                        ).lower()
                                        c_ref = (
                                            f"1:0:{stype}:{csid_hex}:"
                                            f"{tsid_hex}:{onid_hex}:"
                                            f"{ns_hex}:0:0:0:"
                                            f"{sub_url}:{name}"
                                        )
                                        bouquet.append(
                                            f"#SERVICE {c_ref}\n"
                                            f"#DESCRIPTION {name}"
                                        )
                                        print(
                                            f"    {Color.GREEN}✔ Added: "
                                            f"{name}{Color.END}"
                                        )
                                    except Exception as exc:
                                        print(
                                            f"    {Color.RED}✖ Error "
                                            f"parsing line: "
                                            f"{csv_line.strip()} "
                                            f"({exc}){Color.END}"
                                        )
                        else:
                            if ch_file:
                                print(
                                    f"  {Color.RED}⚠ File not found: "
                                    f"{ch_file}{Color.END}"
                                )
                            else:
                                print(
                                    f"  {Color.BLUE}ℹ No CSV import for "
                                    f"this pipe.{Color.END}"
                                )

                # ---- Ask whether to add another transponder ----
                print(
                    f"\n{Color.BLUE}└" + "─" * 78 + "┘" + Color.END
                )
                if (
                    ask(
                        "Add another transponder?",
                        "n",
                        "y = return to Step 4 | n = compile database.",
                        "❓",
                    )
                    == "y"
                ):
                    step = 4
                    continue
                break  # exit the state machine

        except GoBack:
            step = max(1, step - 1)
            continue

    # ==================================================================
    # FINAL COMPILATION – write lamedb, bouquet and astra.conf
    # ==================================================================
    print(f"\n{Color.CYAN}╔" + "═" * 78 + "╗")
    print(
        f"║ {Color.BOLD}COMPILING ARCHITECTURAL BLUEPRINTS"
        f"{Color.END}{Color.CYAN}".center(88) + "║"
    )
    print(f"╚" + "═" * 78 + "╝" + Color.END)

    for i in range(0, 101, 20):
        draw_progress(i, task="Consolidating lamedb")

    # ---- lamedb SURGICAL LIVE MERGE ----
    for i in range(0, 101, 25):
        draw_progress(i, task="Consolidating lamedb")

    # 1. Read the destination file into memory as a list of strings
    if os.path.isfile(merge_path):
        with open(merge_path, "r", encoding="utf-8", errors="ignore") as fh:
            db_lines = [line.rstrip() for line in fh.readlines()]
    else:
        # Standard Enigma2 lamedb template if file is missing
        db_lines = ["eDVB services /4/", "transponders", "end", "services", "end"]

    # 2. Inject Transponders under the 'transponders' line
    try:
        tp_header_idx = db_lines.index("transponders")
        for tp_key, tp_block in new_tps.items():
            # Deduplicate: Remove old matching transponder block (3 lines)
            for idx, line in enumerate(db_lines):
                if line.startswith(tp_key):
                    del db_lines[idx : idx + 3]
                    break
            # Insert the new block immediately under the header
            db_lines.insert(tp_header_idx + 1, tp_block.strip())
    except ValueError:
        print(f"{Color.RED}✖ Error: 'transponders' section not found!{Color.END}")

    # 3. Inject Services under the 'services' line
    try:
        # Re-find index because the list size changed after TP insertion
        srv_header_idx = db_lines.index("services")
        for srv_key, srv_block in new_srvs.items():
            # Deduplicate: Remove old matching service block (3 lines)
            for idx, line in enumerate(db_lines):
                if line.startswith(srv_key):
                    del db_lines[idx : idx + 3]
                    break
            # Insert the new service entry immediately under the header
            db_lines.insert(srv_header_idx + 1, srv_block.strip())
    except ValueError:
        print(f"{Color.RED}✖ Error: 'services' section not found!{Color.END}")

    # 4. Save the result back to the workspace
    with open("lamedb", "w", encoding="utf-8", newline='\n') as fh:
        fh.write("\n".join(db_lines) + "\n")

    # ---- Bouquet ----
    for i in range(0, 101, 50):
        draw_progress(i, task="Syncing Bouquet")

    final_bouquet = []
    if mode == "modify" and os.path.isfile(bouquet_file):
        with open(bouquet_file, "r", encoding="utf-8") as fh:
            existing = fh.readlines()

        new_refs = [
            line.split(":")[-5:-1]
            for line in bouquet
            if line.startswith("#SERVICE")
        ]
        skip_next = False
        for existing_line in existing:
            if skip_next:
                skip_next = False
                continue
            if existing_line.startswith("#NAME"):
                final_bouquet.append(existing_line.strip())
                continue
            duplicate = any(
                all(part in existing_line for part in ref)
                for ref in new_refs
                if ":" in existing_line
            )
            if duplicate:
                skip_next = True
                continue
            if existing_line.strip():
                final_bouquet.append(existing_line.strip())

    if not any(l.startswith("#NAME") for l in final_bouquet):
        final_bouquet.insert(0, f"#NAME {bouquet_name}")
    final_bouquet.extend(bouquet)

    with open(bouquet_file, "w", encoding="utf-8") as fh:
        fh.write("\n".join(final_bouquet) + "\n")

    # ---- Astra config ----
    for i in range(0, 101, 25):
        draw_progress(i, task="Writing Astra")

    if not os.path.isdir("astra"):
        os.makedirs("astra")
    astra_path = "astra/astra.conf"

    if mode == "modify" and os.path.isfile(astra_path):
        with open(astra_path, "r", encoding="utf-8") as fh:
            old_conf = fh.read()
        for block in astra_blocks:
            v_name = block.split("=")[0].strip()
            pattern = (
                rf"-- .*?\n{re.escape(v_name)} = .*?}}\)\n"
                rf"make_channel.*?}}\)\n"
            )
            old_conf = re.sub(pattern, "", old_conf, flags=re.DOTALL)
        final_astra = (
            old_conf.strip()
            + "\n\n-- [ ARCHITECT MODIFIED ENTRIES ] --\n"
        )
    else:
        final_astra = "-- [ ARCHITECT GENERATED CONFIG ] --\n"

    final_astra += "\n".join(astra_blocks)
    with open(astra_path, "w", encoding="utf-8") as fh:
        fh.write(final_astra.strip() + "\n")

    # ==================================================================
    # Completion
    # ==================================================================
    print(
        f"\n{Color.GREEN}✅ ALL FILES SYNCHRONIZED SUCCESSFULLY.{Color.END}"
    )
    print(f"{Color.CYAN}📂 DATABASE: ./lamedb")
    print(f"📂 BOUQUET : ./{bouquet_file}")
    print(f"📂 ASTRA   : ./{astra_path}{Color.END}")
    print(
        f"\n{Color.GREEN}{Color.BOLD}"
        f"✨ v9.7 ENCYCLOPEDIA ARCHITECT LOCKED!{Color.END}"
    )

except KeyboardInterrupt:
    exit_gracefully()
