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
            subprocess.check_call([sys.executable,
                                   "-m",
                                   "pip",
                                   "install",
                                   "colorama"],
                                  stdout=subprocess.DEVNULL,
                                  stderr=subprocess.DEVNULL)
            import colorama
            colorama.init()
        except BaseException:
            pass

    try:
        from prompt_toolkit import prompt as pt_prompt
        from prompt_toolkit.history import FileHistory
        from prompt_toolkit.shortcuts import radiolist_dialog
        from prompt_toolkit.completion import PathCompleter
        from prompt_toolkit.formatted_text import ANSI
        return pt_prompt, FileHistory, radiolist_dialog, PathCompleter, ANSI
    except ImportError:
        if "pyenv" not in sys.executable and os.path.exists(
                os.path.expanduser("~/.pyenv")):
            print(f"{Color.YELLOW}⚠ System Python detected. Switching to environment shim...{Color.END}")
            os.execvp("python", ["python"] + sys.argv)

        print(
            f"\n{Color.YELLOW}⚠ Module 'prompt_toolkit' not found.{Color.END}")
        print(f"{Color.CYAN}⚙ Attempting installation...{Color.END}")

        pip_cmd = [sys.executable, "-m", "pip", "install", "prompt_toolkit"]
        if sys.version_info >= (3, 11):
            pip_cmd.append("--break-system-packages")

        try:
            subprocess.check_call(
                pip_cmd,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL)
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


# Initialize toolkit globally
pt_prompt, FileHistory, radiolist_dialog, PathCompleter, ANSI = ensure_dependencies()

# ----------------------------------------------------------------------
# UI Controller
# ----------------------------------------------------------------------


class UIController:
    """Handles all user interaction, display, and input."""

    def __init__(self):
        self.history = { "default": FileHistory(".dx_history_default"), "paths": FileHistory(".dx_history_paths"), "bouquet": FileHistory(".dx_history_bouquet"), "freq": FileHistory(".dx_history_freq"), "pid": FileHistory(".dx_history_pid"), "sid": FileHistory(".dx_history_sid"), "provider": FileHistory(".dx_history_provider") }
        self.path_completer = PathCompleter(expanduser=True)

    @staticmethod
    def clear_screen():
        os.system('cls' if os.name == 'nt' else 'clear')

    @staticmethod
    def print_header():
        print(f"{Color.BLUE}{Color.BOLD}" + "═" * 80)
        print(r"""
  _______ ___       __  __ ___   _   _ _   _ _   _ __  __  _   _____ _____
 |__   __|__ \     |  \/  |_ _| | | | | | | | | | |  \/  |/ \ |_   _| ____|
    | |     ) |____| |\/| || |  | | | | | | | | | | |\/| / _ \  | | |  _|
    | |    / /|____| |  | || |  | |_| | |_| | |_| | |  |/ ___ \ | | | |___
    |_|   |___|    |_|  |_|___|  \___/ \___/ \___/|_|  /_/   \_\|_| |_____|

               v9.7 - [ THE ENCYCLOPEDIA ARCHITECT ]
               RESTORED VERSION: HELPER TEXTS ENABLED
        """)
        print("═" * 80 + f"{Color.END}")

    @staticmethod
    def draw_progress(percent, width=40, task="Processing"):
        filled = int(width * percent / 100)
        bar = "█" * filled + "▒" * (width - filled)
        sys.stdout.write(f"\r  {Color.CYAN}{task.ljust(22)}: {Color.BOLD}[{bar}]{Color.END} {percent}%")
        sys.stdout.flush()
        time.sleep(0.01)

    @staticmethod
    def exit_gracefully():
        print(
            f"\n\n{Color.RED}⚠ PROCESS ABORTED BY OPERATOR (Ctrl+C).{Color.END}")
        print(f"{Color.YELLOW}System state preserved. Exiting The Encyclopedia Architect...{Color.END}")
        sys.exit(0)

    def ask(
            self,
            prompt_text,
            default=None,
            help_text="",
            icon="📌",
            allow_back=True,
            category="default"):
        while True:
            print(
                f"\n{Color.YELLOW}╭──────────────────────────────────────────────────────────────────────────────╮")
            for line in help_text.strip().split('\n'):
                print(
                    f"│ {Color.BLUE}{icon} {line.ljust(74)}{Color.END}{Color.YELLOW} │")
            if allow_back:
                back_hint = "↩  Type 'back' to return to the previous configuration step."
                print(
                    f"│ {Color.CYAN}{back_hint.ljust(76)}{Color.END}{Color.YELLOW} │")

            status = f"[ DEFAULT: {default} ]" if default is not None else "[ ACTION REQUIRED ]"
            print(
                f"├──────────────────────────────────────────────────────────────────────────────┤")
            print(
                f"│ {Color.GREEN}STATUS: {status.ljust(68)}{Color.END}{Color.YELLOW} │")
            print(
                f"╰──────────────────────────────────────────────────────────────────────────────╯{Color.END}")

            cat_history = self.history.get(category, self.history["default"])
            val = pt_prompt(
                ANSI(
                    f"  {Color.BOLD}{prompt_text}{Color.END}: "),
                history=cat_history).strip()

            if val.lower() == "back" and allow_back:
                raise GoBack()
            if val == "" and default is not None:
                return default
            if val != "":
                return val
            print(
                f"  {Color.RED}❌ ERROR: This field cannot be empty.{Color.END}")

    def choose_option(self, title, text, options, default=None):
        result = radiolist_dialog(
            title=f" ARCHITECT SELECTION: {title} ",
            text=f"\n{text}\n\nNavigation: [Tab] Move | [Space/Enter] Select\n",
            values=options,
            default=default).run()
        if result is None:
            raise GoBack()
        return result

    def file_browser(self, start_path="."):
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
                    values=options).run()

                if selection is None:
                    print(
                        f"  {Color.YELLOW}ℹ Cancelled. Using default: ./lamedb{Color.END}")
                    return "./lamedb"
                if selection == "..":
                    current_dir = os.path.dirname(current_dir)
                elif os.path.isdir(selection):
                    current_dir = selection
                else:
                    return selection
            except Exception as e:
                print(f"  {Color.RED}⚠ Error: {e}. Using default.{Color.END}")
                return "./lamedb"

# ----------------------------------------------------------------------
# Config Builder
# ----------------------------------------------------------------------


class ConfigBuilder:
    """Generates configuration strings for lamedb, bouquets, and Astra."""

    @staticmethod
    def generate_tp_entry(
            ns_hex,
            tsid_hex,
            onid,
            freq,
            sr,
            pol,
            fec,
            disp_sat,
            inv,
            sys_type,
            mod,
            roll,
            pilot,
            isi):
        p_digit = {"H": "0", "V": "1", "L": "2", "R": "3"}.get(pol, "0")
        tp_key = f"{ns_hex}:{tsid_hex}:{onid}"
        content = f"{tp_key}\n\ts { freq * 1000}:{ sr * 1000}:{p_digit}:{fec}:{disp_sat}:{inv}:0:{sys_type}:{mod}:{roll}:{pilot}:{isi}\n/\n"
        return tp_key, content

    @staticmethod
    def generate_srv_entry(srv_key, provider, pid):
        return f"{srv_key}:1:0\n{provider} PID{pid} FEED\np:{provider},c:15{format(int(pid), '04x')},f:01\n"

    @staticmethod
    def generate_astra_block(
            var_name,
            label,
            s_ref_core,
            path,
            freq,
            sat_pos,
            sat_dir,
            plp,
            pid):
        block = (f"-- {label}\n{var_name} = make_t2mi_decap({{\n"
                 f"    name = \"decap_{var_name}\",\n"
                 f"    input = \"http://127.0.0.1:8001/1:0:1:{s_ref_core}:0:0:0:\",\n"
                 f"    plp = {plp},\n    pnr = 0,\n    pid = {pid},\n}})\n"
                 f"make_channel({{\n    name = \"{label}\",\n"
                 f"    input = {{ \"t2mi://decap_{var_name}\", }},\n"
                 f"    output = {{ \"http://0.0.0.0:9999/{path}/{freq}_{sat_pos}{sat_dir.lower()}_plp{plp}\", }},\n}})\n")
        return block

# ----------------------------------------------------------------------
# Database Manager
# ----------------------------------------------------------------------


class DatabaseManager:
    """Handles file I/O, merging, and surgical editing of lamedb."""

    def __init__(self, ui_controller):
        self.ui = ui_controller

    def backup_file(self, path):
        if os.path.isfile(path):
            try:
                timestamp = time.strftime("%Y%m%d_%H%M%S")
                backup_name = f"{path}_{timestamp}.bak"
                shutil.copy2(path, backup_name)
                self.ui.draw_progress(20, task="Creating Backup")
                print(
                    f"\n  {Color.GREEN}💾 BACKUP CREATED: {backup_name}{Color.END}")
                return backup_name
            except Exception as e:
                print(f"\n  {Color.RED}⚠ BACKUP FAILED: {str(e)}{Color.END}")
        return None

    def load_db_lines(self, path):
        if os.path.isfile(path):
            with open(path, "r", encoding="utf-8", errors="ignore") as f:
                return [line.rstrip() for line in f.readlines()]
        return ["eDVB services /4/", "transponders", "end", "services", "end"]

    def merge_and_save(self, path, new_tps, new_srvs, local_save=True):
        self.ui.draw_progress(40, task="Loading Database")
        db_lines = self.load_db_lines(path)

        # Surgical Transponder Merge
        try:
            tp_idx = db_lines.index("transponders")
            for key, block in new_tps.items():
                for idx, line in enumerate(db_lines):
                    if line.startswith(key):
                        del db_lines[idx:idx + 3]
                        break
                db_lines.insert(tp_idx + 1, block.strip())
        except ValueError:
            pass

        # Surgical Services Merge
        try:
            srv_idx = db_lines.index("services")
            for key, block in new_srvs.items():
                for idx, line in enumerate(db_lines):
                    if line.startswith(key):
                        del db_lines[idx:idx + 3]
                        break
                db_lines.insert(srv_idx + 1, block.strip())
        except ValueError:
            pass

        if local_save:
            with open("lamedb", "w", encoding="utf-8", newline='\n') as f:
                f.write("\n".join(db_lines) + "\n")

        return db_lines

    def save_bouquet(self, filename, name, bouquet_list):
        with open(filename, "w") as f:
            f.write(f"#NAME {name}\n" + "\n".join(bouquet_list) + "\n")

    def save_astra(self, blocks):
        if not os.path.exists("astra"):
            os.makedirs("astra")
        with open("astra/astra.conf", "w") as f:
            f.write(
                "-- [ ARCHITECT GENERATED CONFIG ] --\n" +
                "\n".join(blocks))

# ----------------------------------------------------------------------
# Main Application
# ----------------------------------------------------------------------


class ArchitectApp:
    """Main application controller managing workflow and state."""

    def __init__(self):
        self.ui = UIController()
        self.db = DatabaseManager(self.ui)
        self.builder = ConfigBuilder()

        # State variables
        self.new_tps = {}
        self.new_srvs = {}
        self.bouquet = []
        self.astra_blocks = []
        self.ONID = "0001"

        # Current Transponder Config
        self.config = {}

    def run(self):
        try:
            self.ui.clear_screen()
            self.ui.print_header()
            self.step = 1
            self.used_csv = False

            while True:
                try:
                    self.process_step()
                except GoBack:
                    self.handle_go_back()

        except KeyboardInterrupt:
            self.ui.exit_gracefully()

    def process_step(self):
        if self.step == 1:
            self.step_cleanup()
        elif self.step == 2:
            self.step_select_source()
        elif self.step == 3:
            self.step_bouquet_name()
        elif self.step == 4:
            self.step_frequency_source()
        elif self.step >= 5 and self.step <= 14:
            self.step_manual_params()
        elif self.step == 15:
            self.step_multistream()
        elif self.step == 16:
            self.step_sid()
        elif self.step == 17:
            self.step_provider()
        elif self.step == 18:
            self.step_astra_path()
        elif self.step == 19:
            self.step_process_transponder()

    def handle_go_back(self):
        self.step = 4 if self.used_csv and self.step == 15 else max(
            1, self.step - 1)
        self.used_csv = False
        self.ui.clear_screen()
        self.ui.print_header()
        print(
            f"\n{Color.RED}↩ REVERTING TO PREVIOUS CONFIGURATION STEP...{Color.END}")

    # --- Step Implementations ---

    def step_cleanup(self):
        cleanup = self.ui.ask(
            "Clean workspace?",
            "n",
            "Choose whether to wipe existing generated files to prevent data mixing.\n"
            "y = YES (Deletes lamedb, astra folder, and userbouquets)\n"
            "n = NO (Performs a safe merge with existing data)",
            "🧹",
            allow_back=False)
        if cleanup.lower() == 'y':
            for i in range(0, 101, 10):
                self.ui.draw_progress(i, task="Wiping Environment")
            for f in os.listdir('.'):
                if (f.startswith('userbouquet.')
                        and f.endswith('.tv')) or f == 'lamedb':
                    try:
                        os.remove(f)
                    except BaseException:
                        pass
            if os.path.exists('astra'):
                shutil.rmtree('astra')
        self.step = 2

    def step_select_source(self):
        print(
            f"\n{Color.YELLOW}┌── {Color.BOLD}DATABASE SOURCE SELECTION{Color.END}{Color.YELLOW} " +
            "─" *
            47 +
            "┐")
        print(
            f"│ {Color.BLUE}📂 Opening File Manager for target selection...                           {Color.END}{Color.YELLOW} │")
        print(
            f"│ {Color.BLUE}💡 Cancelling will automatically select local ./lamedb.                   {Color.END}{Color.YELLOW} │")
        print(f"└" + "─" * 78 + "┘" + Color.END)
        self.config['merge_path'] = self.ui.file_browser(".")
        print(
            f"  {Color.GREEN}✅ Target Active: {Color.BOLD}{self.config['merge_path']}{Color.END}")
        self.step = 3

    def step_bouquet_name(self):
        bouquet_name = self.ui.ask(
            "Bouquet Name", "T2MI DX",
            "The label that will appear in your Enigma2 Favorites list.\n"
            "Spaces will be converted to underscores for the filename.",
            "🏷️"
        )
        self.config['bouquet_name'] = bouquet_name
        self.config['bouquet_file'] = f"userbouquet.{bouquet_name.lower().replace(' ', '_')}.tv"
        self.step = 4

    def step_frequency_source(self):
        freq_dir = "frequencies"
        csv_files = [f for f in os.listdir(freq_dir) if f.endswith(
            '.csv')] if os.path.exists(freq_dir) else []

        if csv_files:
            options = [("manual",
                        ">> MANUAL ENTRY (Input parameters by hand)")] + [(f,
                                                                           f"📄 {f}") for f in csv_files]
            choice = self.ui.choose_option(
                "Frequency Database",
                "Select a pre-configured CSV for automatic transponder parameter loading:",
                options,
                "manual")

            if choice != "manual" and choice is not None:
                self.load_from_csv(choice)
                return

        self.config['freq'] = int(
            self.ui.ask(
                "Frequency (MHz)",
                "4014",
                "Enter Downlink Frequency.\nCommon Examples: 4014 (C-Band), 11495 (Ku-Band).",
                "📡"))
        self.step = 5

    def load_from_csv(self, choice):
        with open(os.path.join("frequencies", choice), 'r', encoding='utf-8') as f:
            reader = list(csv.DictReader(f))

        print(
            f"\n{Color.YELLOW}┌── {Color.BOLD}SELECT TRANSPONDER FROM DATABASE{Color.END}{Color.YELLOW} " +
            "─" *
            40 +
            "┐")
        for idx, r in enumerate(reader):
            label = f"{r['Freq']} {r['Pol']} ({r['Pos']}{r['Dir']}) SR:{r['SR']}"
            print(
                f"│ {Color.CYAN} [{idx}] {label.ljust(72)}{Color.END}{Color.YELLOW} │")
        print(f"└" + "─" * 78 + "┘" + Color.END)

        tp_idx_str = self.ui.ask(
            "Select TP Index [#]",
            "0",
            "Enter the numeric index from the list above.",
            "📡")
        row = reader[int(tp_idx_str)]

        self.config['freq'] = int(row['Freq'])
        raw_pol = row['Pol'].upper()
        self.config['pol'] = { "2": "L", "3": "R", "0": "H", "1": "V"}.get(
            raw_pol,
            raw_pol)
        self.config['sr'] = int(row['SR'])
        sat_pos, sat_dir = float(row['Pos']), row['Dir'].upper()

        # FIX: Changed row['Fec'] to row['FEC'] to match original CSV format
        self.config['inv'], self.config['fec'] = row['Inv'], row['FEC']
        self.config['sys_type'], self.config['mod'] = row['Sys'], row['Mod']
        self.config['roll'], self.config['pilot'] = row['RO'], row['Pilot']

        self.calculate_sat_data(sat_pos, sat_dir)
        print(
            f"\n{Color.GREEN}✅ LOADED: {self.config['freq']} {self.config['pol']} {sat_pos}{sat_dir} (Hex: {self.config['ns_hex']}){Color.END}")
        self.used_csv = True
        self.step = 15

    def calculate_sat_data(self, sat_pos, sat_dir):
        raw_sat = int(sat_pos * 10)
        ns_sat = (3600 - raw_sat) if sat_dir == "W" else raw_sat
        disp_sat = -raw_sat if sat_dir == "W" else raw_sat
        self.config['ns_hex'] = format(
            (ns_sat << 16) | self.config['freq'], '08x').lower()
        self.config['disp_sat'] = disp_sat
        self.config['sat_pos'] = sat_pos
        self.config['sat_dir'] = sat_dir

    def step_manual_params(self):
        if self.step == 5:
            self.config['sr'] = int(
                self.ui.ask(
                    "Symbol Rate",
                    "15284",
                    "Enter the Symbol Rate (SR) of the carrier.\nCommon: 15284, 30000, 45000.",
                    "📶"))
            self.step = 6
        elif self.step == 6:
            self.config['pol'] = self.ui.choose_option(
                "Polarization", "Select the physical antenna orientation for this transponder:", [
                    ("H", "Horizontal"), ("V", "Vertical"), ("L", "Left Circular"), ("R", "Right Circular")], "L")
            self.step = 7
        elif self.step == 7:
            self.config['sat_pos'] = float(
                self.ui.ask(
                    "Satellite Position",
                    "18.1",
                    "Orbital degree of the satellite.\nExample: 18.1 (Intelsat), 4.9 (SES), 36.0 (Eutelsat).",
                    "🌍"))
            self.step = 8
        elif self.step == 8:
            sat_dir = self.ui.ask(
                "Direction (E/W)",
                "W",
                "Orbital hemisphere.\nE = East | W = West.",
                "🧭").upper()
            self.calculate_sat_data(self.config['sat_pos'], sat_dir)
            self.step = 9
        elif self.step == 9:
            self.config['inv'] = self.ui.ask(
                "Inversion",
                "2",
                "Spectral inversion setting.\n0 = OFF | 1 = ON | 2 = AUTO.",
                "🛠️")
            self.step = 10
        elif self.step == 10:
            self.config['fec'] = self.ui.choose_option("FEC", "Forward Error Correction ratio:", [(
                "1", "1/2"), ("2", "2/3"), ("3", "3/4"), ("4", "5/6"), ("5", "7/8"), ("6", "8/9"), ("7", "3/5"), ("8", "4/5"), ("9", "Auto")], "9")
            self.step = 11
        elif self.step == 11:
            self.config['sys_type'] = self.ui.ask(
                "Transmission System",
                "1",
                "Standard used for the transponder.\n0 = DVB-S (Old) | 1 = DVB-S2 (Modern).",
                "🛠️")
            self.step = 12
        elif self.step == 12:
            self.config['mod'] = self.ui.ask(
                "Modulation",
                "2",
                "Signal modulation type.\n1 = QPSK | 2 = 8PSK | 3 = 16APSK | 4 = 32APSK.",
                "🛠️")
            self.step = 13
        elif self.step == 13:
            self.config['roll'] = self.ui.ask(
                "Roll-Off Factor",
                "0",
                "Filter slope width.\n0 = 0.35 | 1 = 0.25 | 2 = 0.20.",
                "🛠️")
            self.step = 14
        elif self.step == 14:
            self.config['pilot'] = self.ui.ask(
                "Pilot Mode",
                "2",
                "Pilot symbols for synchronization.\n0 = OFF | 1 = ON | 2 = AUTO.",
                "🛠️")
            self.step = 15

    def step_multistream(self):
        is_mis = self.ui.ask(
            "Enable Multistream?", "n",
            "Does this transponder carry multiple Input Streams (ISI)?\n"
            "y = YES (Multi-ISI mode) | n = NO (Single Stream mode).",
            "🌊"
        )
        self.config['isi_input'] = self.ui.ask(
            "Stream IDs (ISIs)", "171",
            "Enter numeric IDs separated by commas.\nExample: 171, 172, 173.",
            "🆔"
        ) if is_mis.lower() == 'y' else "-1"
        self.step = 16

    def step_sid(self):
        self.config['sid'] = int(self.ui.ask(
            "Base Service ID (SID)", "800",
            "The starting virtual Service ID.\n"
            "The script will auto-increment this for each stream/PID added.",
            "🆔"
        ))
        self.step = 17

    def step_provider(self):
        self.config['provider'] = self.ui.ask(
            "Provider Label",
            "ORTM",
            "Corporate/Channel branding used in metadata.\nExample: BBC, Canal+, Globecast.",
            "🏢")
        self.step = 18

    def step_astra_path(self):
        self.config['path'] = self.ui.ask(
            "Astra-SM Path",
            "ortm",
            "The URL slug for your Astra relay.\nResult: http://0.0.0.0:9999/[path]/...",
            "🔗")
        self.step = 19

    def step_process_transponder(self):
        # Snapshot state for rollback
        b_len, a_len = len(self.bouquet), len(self.astra_blocks)
        tps_keys, srvs_keys = set(
            self.new_tps.keys()), set(
            self.new_srvs.keys())

        try:
            current_sid = self.config['sid']

            for isi in [i.strip()
                        for i in self.config['isi_input'].split(",")]:
                dyn_tsid = format(int(isi), '04x') if isi != "-1" else "0001"

                # Generate TP Entry
                tp_key, tp_content = self.builder.generate_tp_entry(
                    self.config['ns_hex'], dyn_tsid, self.ONID,
                    self.config['freq'], self.config['sr'], self.config['pol'],
                    self.config['fec'], self.config['disp_sat'], self.config['inv'],
                    self.config['sys_type'], self.config['mod'], self.config['roll'],
                    self.config['pilot'], isi
                )
                self.new_tps[tp_key] = tp_content

                # Ask for PIDs
                pid_target = f"Stream {isi}" if isi != "-1" else "Transponder"
                pid_input = self.ui.ask(
                    f"T2-MI PIDs for {pid_target}",
                    "4096",
                    f"Enter T2-MI Packet IDs for {pid_target}.\nComma-separated list (e.g. 4096, 4097).",
                    "🔢")

                for pid in [p.strip() for p in pid_input.split(",")]:
                    sid_hex = format(current_sid, '04x').lower()
                    sid_no_lead = format(current_sid, 'x').lower()
                    tsid_no_lead = format(int(dyn_tsid, 16), 'x').lower()
                    onid_no_lead = format(int(self.ONID, 16), 'x').lower()
                    s_ref_core = f"{sid_no_lead}:{tsid_no_lead}:{onid_no_lead}:{self.config['ns_hex']}"
                    srv_key = f"{sid_hex}:{self.config['ns_hex']}:{dyn_tsid}:{self.ONID}"

                    # Generate Service Entry
                    self.new_srvs[srv_key] = self.builder.generate_srv_entry(
                        srv_key, self.config['provider'], pid)
                    self.bouquet.append(
                        f"#SERVICE 1:0:1:{s_ref_core}:0:0:0:\n#DESCRIPTION {self.config['provider']} PID{pid} FEED")

                    # Ask for PLPs
                    plp_target = f"ISI {isi} PID {pid}" if isi != "-1" else f"PID {pid}"
                    plps_input = self.ui.ask(
                        f"PLPs for {plp_target}",
                        "0",
                        "Physical Layer Pipe IDs.\nComma-separated (e.g. 0, 1, 2).",
                        "📺")

                    for plp in [pl.strip() for pl in plps_input.split(",")]:
                        # Generate Astra Block
                        var_name = f"f{self.config['freq']}{self.config['pol'].lower()}{ self.config['provider'].lower()[ :2]}p{pid}plp{plp}"
                        if isi != "-1":
                            var_name += f"isi{isi}"
                        label_full = f"{self.config['provider']} {self.config['freq']}{self.config['pol']} " + (f"ISI{isi} " if isi != "-1" else "") + f"PID{pid} PLP{plp}"

                        self.bouquet.append(
                            f"#SERVICE 1:64:0:0:0:0:0:0:0:0:\n#DESCRIPTION --- {label_full} ---")

                        block = self.builder.generate_astra_block(
                            var_name,
                            label_full,
                            s_ref_core,
                            self.config['path'],
                            self.config['freq'],
                            self.config['sat_pos'],
                            self.config['sat_dir'],
                            plp,
                            pid)
                        self.astra_blocks.append(block)

                        # Handle Sub-channels
                        self.process_sub_channels(
                            plp, tsid_no_lead, onid_no_lead, s_ref_core, label_full)

                    current_sid += 1

            if self.ui.ask(
                "Add another Transponder?",
                "n",
                "y = Add more data | n = Finalize and Save.",
                    "❓") == "y":
                self.step = 4
                return

            self.finalize()

        except GoBack:
            # Rollback state
            self.bouquet = self.bouquet[:b_len]
            self.astra_blocks = self.astra_blocks[:a_len]
            for k in list(self.new_tps.keys()):
                if k not in tps_keys:
                    del self.new_tps[k]
            for k in list(self.new_srvs.keys()):
                if k not in srvs_keys:
                    del self.new_srvs[k]
            raise

    def process_sub_channels(
            self,
            plp,
            tsid_no_lead,
            onid_no_lead,
            s_ref_core,
            label_full):
        orbital_folder = f"{self.config['sat_pos']}{self.config['sat_dir'].upper()}"
        csv_dir = os.path.join("channellist", orbital_folder)
        suggestions = sorted([f for f in os.listdir(csv_dir) if f.lower().endswith(
            '.csv')]) if os.path.isdir(csv_dir) else []

        title_text = f" SUB-CHANNEL MAPPING: PLP {plp} "
        print(f"\n{Color.YELLOW}┌── {Color.BOLD}{title_text}{Color.END}{Color.YELLOW} " + "─" * (76 - len(title_text)) + "┐")
        if suggestions:
            for idx, fname in enumerate(suggestions, 1):
                print(
                    f"│ {Color.CYAN} [{idx}] {fname.ljust(72)}{Color.END}{Color.YELLOW} │")
        else:
            print(
                f"│ {Color.RED} ❌ No channel mapping CSVs found in {csv_dir.ljust(50)}{Color.END}{Color.YELLOW} │")
        print(f"└" + "─" * 78 + "┘" + Color.END)

        ch_choice = pt_prompt(
            ANSI(
                f"  Select Mapping File [#] or Path: "),
            completer=self.ui.path_completer,
            history=self.ui.history['default']).strip()
        if ch_choice.lower() == "back":
            raise GoBack()

        ch_file = os.path.join(csv_dir, suggestions[int(
            ch_choice) - 1]) if ch_choice.isdigit() and 1 <= int(ch_choice) <= len(suggestions) else ch_choice

        if ch_file and os.path.isfile(ch_file):
            sub_url = f"http://0.0.0.0:9999/{self.config['path']}/{self.config['freq']}_{self.config['sat_pos']}{self.config['sat_dir'].lower()}_plp{plp}".replace(":", "%3a")
            with open(ch_file, "r", encoding="utf8") as f:
                for line in f:
                    if "," not in line:
                        continue
                    try:
                        csid, name, stype = [x.strip()
                                             for x in line.split(",")]
                        c_ref = f"1:0:{stype}:{format(int(csid), 'x').lower()}:{tsid_no_lead}:{onid_no_lead}:{self.config['ns_hex']}:0:0:0:{sub_url}:{name}"
                        self.bouquet.append(
                            f"#SERVICE {c_ref}\n#DESCRIPTION {name}")
                        print(
                            f"    {Color.GREEN}✔ Added Sub-Channel: {name}{Color.END}")
                    except BaseException:
                        continue

    def finalize(self):
        self.ui.draw_progress(0, task="Initiating Finalization")

        # 1. Backup
        backup_name = self.db.backup_file(self.config['merge_path'])

        # 2. Merge & Save Local
        self.db.merge_and_save(
            self.config['merge_path'],
            self.new_tps,
            self.new_srvs,
            local_save=True)
        self.ui.draw_progress(60, task="Merged Database")

        # 3. Live Swap
        swap_applied = False
        if os.path.abspath(
                self.config['merge_path']) != os.path.abspath("./lamedb"):
            print(
                f"\n{Color.YELLOW}┌── {Color.BOLD}LIVE DATABASE SWAP{Color.END}{Color.YELLOW} " +
                "─" *
                57 +
                "┐")
            print(f"│ {Color.CYAN}Apply these edits to the source file now?{' ' * 36}{Color.END}{Color.YELLOW}│")
            b_disp = os.path.basename(backup_name) if backup_name else "N/A"
            print(
                f"│ {Color.BLUE}ℹ Verified Backup: {b_disp.ljust(53)}{Color.END}{Color.YELLOW} │")
            print(f"└" + "─" * 78 + "┘" + Color.END)

            swap_choice = self.ui.ask(
                "Update source lamedb?",
                "n",
                "y = Overwrite original file | n = Keep edits locally",
                "🔄")
            if swap_choice.lower() == "y":
                try:
                    shutil.copy2("lamedb", self.config['merge_path'])
                    swap_applied = True
                    print(
                        f"  {Color.GREEN}✨ SUCCESS: {self.config['merge_path']} updated.{Color.END}")
                except Exception as e:
                    print(f"  {Color.RED}✖ SWAP FAILED: {str(e)}{Color.END}")

        # 4. Save Configs
        self.db.save_bouquet(
            self.config['bouquet_file'],
            self.config['bouquet_name'],
            self.bouquet)
        self.db.save_astra(self.astra_blocks)

        # 5. Final Report
        self.ui.draw_progress(100, task="Architecture Locked")
        print(
            f"\n\n{Color.GREEN}{Color.BOLD}✅ v9.7 ENCYCLOPEDIA ARCHITECT SUCCESSFUL!{Color.END}")
        print(f"{Color.CYAN}📂 LOCAL WORKSPACE : ./lamedb")
        if backup_name:
            print(f"📂 SOURCE BACKUP   : {backup_name}")
        if swap_applied:
            print(
                f"📂 LIVE DATABASE   : {self.config['merge_path']} {Color.BOLD}(UPDATED){Color.END}")
        else:
            print(
                f"📂 SOURCE TARGET   : {self.config['merge_path']} {Color.BOLD}(UNTOUCHED){Color.END}")
        print(f"📂 BOUQUET         : ./{self.config['bouquet_file']}")
        print(f"📂 ASTRA           : ./astra/astra.conf{Color.END}\n")
        sys.exit(0)


# ----------------------------------------------------------------------
# Entry Point
# ----------------------------------------------------------------------
if __name__ == "__main__":
    app = ArchitectApp()
    app.run()
