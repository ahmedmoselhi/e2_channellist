import re
import os
import sys
import shutil
import time
import csv
from typing import Dict, List, Optional, Tuple, Any

# ----------------------------------------------------------------------
# Exceptions & Constants
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


POL_MAP = {"H": 0, "V": 1, "L": 2, "R": 3}

# ----------------------------------------------------------------------
# UI Manager: Handles all user interaction and display
# ----------------------------------------------------------------------


class UIManager:
    def __init__(self):
        self.pt_prompt = None
        self.FileHistory = None
        self.radiolist_dialog = None
        self.PathCompleter = None
        self.history_files = {}
        self.path_completer = None
        self._initialize_dependencies()
        self._init_history()

    def _initialize_dependencies(self):
        try:
            from prompt_toolkit import prompt as pt_prompt
            from prompt_toolkit.history import FileHistory
            from prompt_toolkit.shortcuts import radiolist_dialog
            from prompt_toolkit.completion import PathCompleter

            self.pt_prompt = pt_prompt
            self.FileHistory = FileHistory
            self.radiolist_dialog = radiolist_dialog
            self.PathCompleter = PathCompleter

        except ImportError:
            self._install_dependencies()
            # Retry import after installation
            try:
                from prompt_toolkit import prompt as pt_prompt
                from prompt_toolkit.history import FileHistory
                from prompt_toolkit.shortcuts import radiolist_dialog
                from prompt_toolkit.completion import PathCompleter

                self.pt_prompt = pt_prompt
                self.FileHistory = FileHistory
                self.radiolist_dialog = radiolist_dialog
                self.PathCompleter = PathCompleter
            except ImportError:
                print(f"{Color.RED}❌ Failed to initialize environment.{Color.END}")
                sys.exit(1)

    def _install_dependencies(self):
        import subprocess

        # Check for pyenv shim
        if "pyenv" not in sys.executable and os.path.exists(
                os.path.expanduser("~/.pyenv")):
            print(f"{Color.YELLOW}⚠ System Python detected. Switching to environment shim...{Color.END}")
            os.execvp("python", ["python"] + sys.argv)

        print(
            f"\n{Color.YELLOW}⚠ Module 'prompt_toolkit' not found.{Color.END}")
        print(f"{Color.CYAN}⚙ Attempting installation...{Color.END}")

        commands = [
            [sys.executable, "-m", "pip", "install", "prompt_toolkit"],
            ["python", "-m", "pip", "install", "prompt_toolkit"],
            ["pip", "install", "prompt_toolkit"]
        ]

        for cmd in commands:
            try:
                if "--break-system-packages" not in cmd and sys.version_info >= (
                        3, 11):
                    cmd.append("--break-system-packages")
                subprocess.check_call(
                    cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
                print(f"{Color.GREEN}✅ Success!{Color.END}\n")
                return
            except BaseException:
                continue

        print(f"{Color.RED}❌ Failed to install prompt_toolkit.{Color.END}")
        sys.exit(1)

    def _init_history(self):
        self.history_files = { "default": self.FileHistory(".dx_history_default"), "paths": self.FileHistory(".dx_history_paths"), "bouquet": self.FileHistory(".dx_history_bouquet"), "freq": self.FileHistory(".dx_history_freq"), "pid": self.FileHistory(".dx_history_pid"), "sid": self.FileHistory(".dx_history_sid"), "provider": self.FileHistory(".dx_history_provider") }
        self.path_completer = self.PathCompleter(expanduser=True)

    def clear_screen(self):
        os.system('cls' if os.name == 'nt' else 'clear')

    def print_header(self):
        print(f"{Color.BLUE}{Color.BOLD}" + "=" * 80)
        print(r"""
  _______ ___       __  __ ___   _   _ _   _ _   _ __  __  _   _____ _____
 |__   __|__ \     |  \/  |_ _| | | | | | | | | | |  \/  |/ \ |_   _| ____|
    | |     ) |____| |\/| || |  | | | | | | | | | | |\/| / _ \  | | |  _|
    | |    / /|____| |  | || |  | |_| | |_| | |_| | |  |/ ___ \ | | | |___
    |_|   |___|    |_|  |_|___|  \___/ \___/ \___/|_|  /_/   \_\|_| |_____|

               v10.3 - [ THE ENCYCLOPEDIA ARCHITECT ]
    """)
        print("=" * 80 + f"{Color.END}")

    def exit_gracefully(self):
        print(
            f"\n\n{Color.RED}⚠ Process interrupted by user (Ctrl+C).{Color.END}")
        print(f"{Color.YELLOW}Exiting The Encyclopedia Architect...{Color.END}")
        sys.exit(0)

    def draw_progress(self, percent, width=40, task="Processing"):
        filled = int(width * percent / 100)
        bar = "█" * filled + "░" * (width - filled)
        sys.stdout.write(f"\r  {Color.CYAN}{task.ljust(20)}: {Color.BOLD}[{bar}]{Color.END} {percent}%")
        sys.stdout.flush()
        time.sleep(0.01)

    def ask(
            self,
            prompt_text,
            default=None,
            help_text="",
            icon="ℹ",
            allow_back=True,
            category="default"):
        while True:
            print(
                f"\n{Color.YELLOW}┌── {Color.BOLD}INPUT FIELD{Color.END}{Color.YELLOW} " +
                "─" *
                65 +
                "┐")
            full_help = help_text
            if allow_back:
                full_help += "\n[ Type 'back' to return to the previous question ]"
            if default is not None:
                full_help += f"\n[ DEFAULT CHOICE: {default} ] (Press Enter to use default)"
            else:
                full_help += "\n[ REQUIRED FIELD: Manual entry necessary ]"

            for line in full_help.strip().split("\n"):
                print(
                    f"│ {Color.BLUE}{icon} {line.ljust(74)}{Color.END}{Color.YELLOW} │")
            print(f"└" + "─" * 78 + "┘" + Color.END)

            cat_history = self.history_files.get(
                category, self.history_files["default"])
            val = self.pt_prompt(
                f"  {prompt_text}: ",
                history=cat_history).strip()

            if val.lower() == "back" and allow_back:
                raise GoBack()
            if val == "" and default is not None:
                return default
            if val != "":
                return val
            print(
                f"  {Color.RED}⚠ ALERT: Value required for database integrity.{Color.END}")

    def choose_option(self, title, text, options, default=None):
        return self.radiolist_dialog(
            title=title,
            text=text,
            values=options,
            default=default,
        ).run()

    def file_browser(self, start_path="."):
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

                selection = self.radiolist_dialog(
                    title="FILE MANAGER: SELECT LAMEDB",
                    text=f"Current Directory: {current_dir}\n\nSelect a 'lamedb' file. If you Cancel, './lamedb' will be used.",
                    values=options
                ).run()

                if selection is None:
                    print(f"  {Color.YELLOW}ℹ Selection cancelled. Reverting to default: ./lamedb{Color.END}")
                    return "./lamedb"

                if selection == "..":
                    current_dir = os.path.dirname(current_dir)
                elif os.path.isdir(selection):
                    current_dir = selection
                else:
                    return selection
            except Exception as e:
                print(
                    f"  {Color.RED}⚠ Error accessing directory: {e}. Using default.{Color.END}")
                return "./lamedb"

    def path_prompt(self, text, history_key="paths"):
        return self.pt_prompt(
            text,
            completer=self.path_completer,
            history=self.history_files.get(
                history_key,
                self.history_files["paths"])).strip()


# ----------------------------------------------------------------------
# Config Manager: Handles file I/O and parsing
# ----------------------------------------------------------------------
class ConfigManager:
    def __init__(self, ui: UIManager):
        self.ui = ui

    def parse_astra_configs(self) -> Dict[str, Dict[str, str]]:
        configs = {}
        conf_path = "astra/astra.conf"
        if os.path.exists(conf_path):
            with open(conf_path, "r", encoding="utf-8") as fh:
                content = fh.read()
                pattern = (
                    r'(\w+)\s*=\s*make_t2mi_decap\({\s*.*?'
                    r'plp\s*=\s*(\d+),.*?pid\s*=\s*(\d+),'
                )
                for var_name, plp, pid in re.findall(
                        pattern, content, re.DOTALL):
                    configs[var_name] = {"plp": plp, "pid": pid}
        return configs

    def get_current_params(self, freq, pol, existing_astra):
        key = f"f{freq}{pol.lower()}"
        for k, v in existing_astra.items():
            if k.startswith(key):
                return v
        return None

    def wipe_workspace(self):
        print(
            f"\n{Color.RED}⚠ WARNING: EXECUTING FULL WORKSPACE WIPE...{Color.END}")
        for i in range(0, 101, 10):
            self.ui.draw_progress(i, task="Purging Data")
        for filename in os.listdir('.'):
            if (filename.startswith('userbouquet.')
                    and filename.endswith('.tv')) or filename == 'lamedb':
                try:
                    os.remove(filename)
                except OSError:
                    pass
        if os.path.isdir('astra'):
            shutil.rmtree('astra')
        print(f"\n  {Color.GREEN}✨ Workspace cleaned successfully.{Color.END}")

    def load_frequency_csvs(self, freq_dir="frequencies"):
        return [f for f in os.listdir(freq_dir) if f.endswith(
            '.csv')] if os.path.exists(freq_dir) else []

    def read_csv(self, filepath):
        with open(filepath, 'r', encoding='utf-8') as f:
            return list(csv.DictReader(f))

    def backup_file(self, path):
        if os.path.isfile(path):
            try:
                timestamp = time.strftime("%Y%m%d_%H%M%S")
                backup_name = f"{path}_{timestamp}.bak"
                shutil.copy2(path, backup_name)
                print(
                    f"\n  {Color.GREEN}💾 BACKUP CREATED: {backup_name}{Color.END}")
                return backup_name
            except Exception as e:
                print(f"\n  {Color.RED}⚠ BACKUP FAILED: {str(e)}{Color.END}")
        else:
            print(
                f"\n  {Color.CYAN}ℹ INFO: No existing database found to backup.{Color.END}")
        return None

    def compile_lamedb(self, merge_path, new_tps, new_srvs):
        for i in range(0, 101, 25):
            self.ui.draw_progress(i, task="Consolidating lamedb")

        if os.path.isfile(merge_path):
            with open(merge_path, "r", encoding="utf-8", errors="ignore") as fh:
                db_lines = [line.rstrip() for line in fh.readlines()]
        else:
            db_lines = [
                "eDVB services /4/",
                "transponders",
                "end",
                "services",
                "end"]

        # Inject Transponders
        try:
            tp_header_idx = db_lines.index("transponders")
            for tp_key, tp_block in new_tps.items():
                for idx, line in enumerate(db_lines):
                    if line.startswith(tp_key):
                        del db_lines[idx: idx + 3]
                        break
                db_lines.insert(tp_header_idx + 1, tp_block.strip())
        except ValueError:
            print(f"{Color.RED}✖ Error: 'transponders' section not found!{Color.END}")

        # Inject Services
        try:
            srv_header_idx = db_lines.index("services")
            for srv_key, srv_block in new_srvs.items():
                for idx, line in enumerate(db_lines):
                    if line.startswith(srv_key):
                        del db_lines[idx: idx + 3]
                        break
                db_lines.insert(srv_header_idx + 1, srv_block.strip())
        except ValueError:
            print(f"{Color.RED}✖ Error: 'services' section not found!{Color.END}")

        # Save locally
        with open("lamedb", "w", encoding="utf-8", newline='\n') as fh:
            fh.write("\n".join(db_lines) + "\n")

    def perform_live_swap(self, merge_path):
        if os.path.abspath(merge_path) != os.path.abspath("./lamedb"):
            try:
                shutil.copy2("lamedb", merge_path)
                print(
                    f"  {Color.GREEN}✨ SUCCESS: {merge_path} updated.{Color.END}")
                return True
            except Exception as e:
                print(f"  {Color.RED}✖ SWAP FAILED: {str(e)}{Color.END}")
        return False

    def sync_bouquet(self, mode, bouquet_file, bouquet_lines, bouquet_name):
        for i in range(0, 101, 50):
            self.ui.draw_progress(i, task="Syncing Bouquet")

        final_bouquet = []
        # Note: In the new logic, if the file exists, we save to a new name. 
        # So we only merge if we are explicitly modifying an existing file that we are targeting.
        # Since we now auto-increment the filename, 'bouquet_file' will point to a non-existing file
        # if a previous one existed. Thus, we effectively start a fresh list for the new file
        # unless the user explicitly selected a specific existing file (not implemented in this flow).
        # Effectively, this logic creates a new bouquet file for the new entries.
        
        if mode == "modify" and os.path.isfile(bouquet_file):
            with open(bouquet_file, "r", encoding="utf-8") as fh:
                existing = fh.readlines()

            new_refs = [
                line.split(":")[-5:-1]
                for line in bouquet_lines
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
        final_bouquet.extend(bouquet_lines)

        with open(bouquet_file, "w", encoding="utf-8") as fh:
            fh.write("\n".join(final_bouquet) + "\n")

    def write_astra_conf(self, mode, astra_blocks):
        for i in range(0, 101, 25):
            self.ui.draw_progress(i, task="Writing Astra")

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
        return astra_path

# ----------------------------------------------------------------------
# Satellite Architect: Main Application Logic
# ----------------------------------------------------------------------


class SatelliteArchitect:
    def __init__(self):
        self.ui = UIManager()
        self.config = ConfigManager(self.ui)

        # State
        self.step = 1
        self.mode = "modify"
        self.existing_astra = {}
        self.merge_path = "./lamedb"

        # Data containers
        self.new_tps = {}
        self.new_srvs = {}
        self.bouquet = []
        self.astra_blocks = []

        # Defaults
        self.bouquet_name = "T2MI DX"
        self.bouquet_file = "userbouquet.t2mi_dx.tv"
        self.ONID = "0001"
        self.TSID = "0001"

        # Transponder Parameters
        self.freq = 4014
        self.pol = "L"
        self.current_cfg = None
        self.sr = 7325
        self.sat_pos = 18.1
        self.sat_dir = "W"
        self.inv = "2"
        self.fec = "9"
        self.sys_type = "1"
        self.mod = "2"
        self.roll = "0"
        self.pilot = "2"

        # Service Parameters
        self.pid_input = "4096"
        self.plps_input = "0"
        self.sid = 800
        self.provider = "ORTM"
        self.path = "ortm"
        
        # Auto-Import State
        self.auto_pairs = [] # List of (pid, plp) tuples

    def run(self):
        try:
            self.ui.clear_screen()
            self.ui.print_header()

            while True:
                try:
                    if self.step == 1:
                        self.step_init()
                    elif self.step == 2:
                        self.step_source()
                    elif self.step == 3:
                        self.step_bouquet()
                    elif self.step == 4:
                        self.step_frequency()
                    elif self.step == 5:
                        self.step_polarization()
                    elif self.step == 6:
                        self.step_physical_layer()
                    elif self.step == 7:
                        self.step_transport_layer()
                    elif self.step == 9:
                        self.step_service_metadata()
                    elif self.step == 10:
                        self.step_build()
                except GoBack:
                    self.step = max(1, self.step - 1)
        except KeyboardInterrupt:
            self.ui.exit_gracefully()

    def step_init(self):
        print(f"\n{Color.CYAN}╔" + "═" * 78 + "╗")
        print(
            f"║ {Color.BOLD}ARCHITECT SESSION INITIALIZATION{Color.END}{Color.CYAN}".center(88) +
            "║")
        print(f"╚" + "═" * 78 + "╝" + Color.END)

        self.mode = self.ui.choose_option(
            "OPERATION MODE",
            "How should existing database files be handled?",
            [
                ("modify", "MODIFY/APPEND – read existing files and update matches."),
                ("fresh", "FRESH START – wipe everything and start a new database."),
            ],
            default="modify"
        )
        if self.mode is None:
            sys.exit(0)

        if self.mode == "fresh":
            self.config.wipe_workspace()
        else:
            for i in range(0, 101, 20):
                self.ui.draw_progress(i, task="Parsing Files")
            print(
                f"\n  {Color.GREEN}📂 Existing database loaded into memory.{Color.END}")

        self.existing_astra = self.config.parse_astra_configs() if self.mode == "modify" else {}
        self.step = 2

    def step_source(self):
        print(
            f"\n{Color.YELLOW}┌── {Color.BOLD}DATABASE SOURCE{Color.END}{Color.YELLOW} " +
            "─" *
            61 +
            "┐")
        print(f"│ {Color.BLUE}📂 Opening File Manager...{' ' * 47}{Color.END}{Color.YELLOW}│")
        print(f"│ {Color.BLUE}ℹ Cancelling will automatically select local ./lamedb.{' ' * 23}{Color.END}{Color.YELLOW}│")
        print(f"└" + "─" * 78 + "┘" + Color.END)

        self.merge_path = self.ui.file_browser(".")
        print(
            f"  {Color.GREEN}✅ Target Active: {Color.BOLD}{self.merge_path}{Color.END}")
        self.step = 3

    def step_bouquet(self):
        self.bouquet_name = self.ui.ask(
            "Bouquet name",
            "T2MI DX",
            "Name of the favourites group in your channel list.",
            "🏷️",
            category="bouquet")
        
        # Generate base filename
        sanitized_name = self.bouquet_name.lower().replace(' ', '_')
        base_filename = f"userbouquet.{sanitized_name}.tv"
        
        # Auto-increment logic in MODIFY mode
        if self.mode == "modify":
            if os.path.exists(base_filename):
                counter = 1
                while True:
                    new_filename = f"userbouquet.{sanitized_name}-{counter}.tv"
                    if not os.path.exists(new_filename):
                        self.bouquet_file = new_filename
                        print(f"\n  {Color.YELLOW}ℹ Existing bouquet found. Incrementing filename to: {Color.BOLD}{self.bouquet_file}{Color.END}")
                        break
                    counter += 1
            else:
                self.bouquet_file = base_filename
        else:
            # Fresh mode, just use the base name (files were wiped)
            self.bouquet_file = base_filename

        self.step = 4

    def step_frequency(self):
        print(f"\n{Color.CYAN}╔" + "═" * 78 + "╗")
        print(
            f"║ {Color.BOLD}THE ARCHITECT: SELECTIVE PARAMETER SYNCHRONIZATION{Color.END}{Color.CYAN}".center(88) +
            "║")
        print(f"║ {Color.BLUE}v10.3 'Elite Edit' Protocol Active".center(
            86) + f"{Color.CYAN} ║")
        print(f"╚" + "═" * 78 + "╝" + Color.END)

        csv_files = self.config.load_frequency_csvs()
        if csv_files:
            print(f"\n{Color.CYAN}📂 Frequency Database Browser{Color.END}")
            options = [("manual", "Manual Entry")] + [(f, f)
                                                      for f in csv_files]
            choice = self.ui.choose_option(
                "Import Source",
                "Select a CSV file or proceed Manually:",
                options,
                "manual")

            if choice != "manual" and choice is not None:
                self._load_from_csv(choice)
                self.step = 7
                return

        freq_help = (f"{Color.BOLD}PRIMARY DATABASE KEY{Color.END}\nEnter the transponder frequency in MHz.\n"
                     "───────────────────────┬──────────────────────\n Range                │ 2000–13000 MHz\n"
                     " Standard (C‑Band)   │ 3400–4200 MHz\n Standard (Ku‑Band)  │ 10700–12700 MHz\n"
                     "───────────────────────┴──────────────────────")
        self.freq = int(
            self.ui.ask(
                "Target Frequency",
                "4014",
                freq_help,
                "📡",
                category="freq"))
        self.step = 5

    def _load_from_csv(self, filename):
        reader = self.config.read_csv(os.path.join("frequencies", filename))

        print(
            f"\n{Color.YELLOW}┌── {Color.BOLD}SELECT TRANSPONDER FROM CSV{Color.END}{Color.YELLOW} " +
            "─" *
            45 +
            "┐")
        for idx, r in enumerate(reader):
            label = f"{r['Freq']} {r['Pol']} ({r['Pos']}{r['Dir']}) SR:{r['SR']}"
            print(
                f"│ {Color.CYAN} [{idx}] {label.ljust(72)}{Color.END}{Color.YELLOW} │")
        print(f"└" + "─" * 78 + "┘" + Color.END)

        tp_idx_str = self.ui.ask(
            "Select TP Index [#]",
            "0",
            "Choose a transponder to load parameters.",
            "📡")
        selected_row = reader[int(tp_idx_str)]

        self.freq = int(selected_row['Freq'])
        raw_pol = selected_row['Pol'].upper()
        self.pol = { "2": "L", "3": "R", "0": "H", "1": "V"}.get(
            raw_pol,
            raw_pol)
        self.sr = int(selected_row['SR'])
        self.sat_pos = float(selected_row['Pos'])
        self.sat_dir = selected_row['Dir'].upper()
        self.inv = selected_row['Inv']
        self.fec = selected_row['FEC']
        self.sys_type = selected_row['Sys']
        self.mod = selected_row['Mod']
        self.roll = selected_row['RO']
        self.pilot = selected_row['Pilot']
        
        # Parse new pids-plps column
        raw_pairs = selected_row.get('pids-plps', '').strip()
        self.auto_pairs = []
        
        if raw_pairs:
            # Remove braces if present
            clean_pairs = raw_pairs.strip('{}')
            if clean_pairs:
                pairs_list = clean_pairs.split(';')
                for pair in pairs_list:
                    if ',' in pair:
                        p, l = pair.split(',', 1)
                        self.auto_pairs.append((p.strip(), l.strip()))
        
        if self.auto_pairs:
            self.pid_input = ",".join(list(set([p[0] for p in self.auto_pairs])))
            self.plps_input = ",".join(list(set([p[1] for p in self.auto_pairs])))
            print(f"\n{Color.GREEN}✅ Auto-detected PID/PLP pairs: {len(self.auto_pairs)}{Color.END}")
        else:
            # Fallback to old columns if new column is missing
            self.pid_input = selected_row.get('PID', '4096')
            self.plps_input = selected_row.get('PLP', '0')

        self.current_cfg = self.config.get_current_params(
            self.freq, self.pol, self.existing_astra)
        print(
            f"\n{Color.GREEN}✅ Tuning Data Loaded: {self.freq} {self.pol} {self.sat_pos}{self.sat_dir}{Color.END}")
        print(f"{Color.YELLOW}🛰️ Jumping to T2-MI PID Configuration...{Color.END}")

    def step_polarization(self):
        pol_text = (f"{Color.BOLD}ELECTROMAGNETIC POLARITY{Color.END}\nSelect the signal orientation to trigger LNB voltage.\n"
                    "┌──────┬──────────────────────┬─────────┐\n│ CODE │ DESCRIPTION          │ VOLTAGE │\n"
                    "├──────┼──────────────────────┼─────────┤\n│ H/V  │ Linear (Standard)    │ 18V/13V │\n"
                    "│ L/R  │ Circular (Special)   │ LH/RH   │\n└──────┴──────────────────────┴─────────┘")
        self.pol = self.ui.choose_option("Polarization", pol_text, [("H", "Horizontal (18V)"), (
            "V", "Vertical (13V)"), ("L", "Left Circular"), ("R", "Right Circular")], default="L")
        if self.pol is None:
            self.step = 4
            return

        self.current_cfg = self.config.get_current_params(
            self.freq, self.pol, self.existing_astra)
        if self.current_cfg:
            print(f"\n{Color.GREEN}┏" + "━" * 76 + "┓")
            print(
                f"┃ {Color.BOLD}RECOGNIZED SIGNATURE FOUND IN ASTRA.CONF{Color.END}{Color.GREEN} ".ljust(85) +
                "┃")
            print(f"┠" + "─" * 76 + "┨")
            print(f"┃ {Color.CYAN}💠 FREQUENCY : {self.freq} MHz".ljust(85) + f"{Color.GREEN}┃")
            print(f"┃ {Color.CYAN}💠 T2‑MI PID : {self.current_cfg['pid']}".ljust(85) + f"{Color.GREEN}┃")
            print(f"┃ {Color.CYAN}💠 PLP ID    : {self.current_cfg['plp']}".ljust(85) + f"{Color.GREEN}┃")
            print(f"┗" + "━" * 76 + "┛" + Color.END)
        else:
            print(
                f"\n{Color.YELLOW}⚡ [ NEW DISCOVERY ] No matching parameters found. Initialising…{Color.END}")
        self.step = 6

    def step_physical_layer(self):
        tp_help = (f"{Color.BOLD}PHYSICAL LAYER GATEWAY{Color.END}\nEdit the RF parameters of the transponder?\n"
                   "y – edit Symbol Rate, Satellite Position, FEC, etc.\nn – keep system defaults.")
        edit_tp = self.ui.ask("Modify Physical Layer?", "n", tp_help, "⚙️")

        if edit_tp.lower() == "y":
            self.sr = int(
                self.ui.ask(
                    "Symbol Rate (kS/s)",
                    "7325",
                    "Typical values: 27500, 30000, 7325.",
                    "📶"))
            self.sat_pos = float(
                self.ui.ask(
                    "Orbital Position",
                    "18.1",
                    "Satellite longitude (e.g. 4.9, 18.1, 36.0).",
                    "🌍"))
            self.sat_dir = self.ui.ask(
                "Direction (E/W)",
                "W",
                "E – East, W – West.",
                "🧭").upper()
            self.inv = self.ui.ask(
                "Inversion",
                "2",
                "0 = Off | 1 = On | 2 = Auto‑Detect.",
                "🛠️")

            fec_help = f"{Color.BOLD}FEC (FORWARD ERROR CORRECTION){Color.END}\nChoose redundancy level.\n1/2  2/3  3/4  5/6  7/8  8/9  3/5  4/5  Auto"
            self.fec = self.ui.choose_option("FEC Ratio",
                                             fec_help,
                                             [("1",
                                               "1/2"),
                                              ("2",
                                               "2/3"),
                                                 ("3",
                                                  "3/4"),
                                                 ("4",
                                                  "5/6"),
                                                 ("5",
                                                  "7/8"),
                                                 ("6",
                                                  "8/9"),
                                                 ("7",
                                                  "3/5"),
                                                 ("8",
                                                  "4/5"),
                                                 ("9",
                                                  "Auto")],
                                             default="9")

            self.sys_type = self.ui.ask(
                "Delivery System",
                "1",
                "0 = DVB‑S (Legacy) | 1 = DVB‑S2 (T2‑MI).",
                "🏗️")
            self.mod = self.ui.ask(
                "Modulation Type",
                "2",
                "1 = QPSK | 2 = 8PSK | 3 = 16APSK | 4 = 32APSK",
                "💠")
            self.roll = self.ui.ask(
                "Roll‑Off Factor",
                "0",
                "0 = 0.35 (DVB‑S) | 1 = 0.25 | 2 = 0.20 (DVB‑S2).",
                "🌊")
            self.pilot = self.ui.ask(
                "Pilot Tones", "2", "0 = Off | 1 = On | 2 = Auto.", "🔦")
        else:
            self.sr, self.sat_pos, self.sat_dir, self.inv, self.fec, self.sys_type, self.mod, self.roll, self.pilot = 7325, 18.1, "W", "2", "9", "1", "2", "0", "2"
        self.step = 7

    def step_transport_layer(self):
        # If auto_pairs are loaded from CSV, skip manual PID input
        if self.auto_pairs:
            print(f"\n{Color.GREEN}✅ PID/PLP pairs loaded automatically from CSV ({len(self.auto_pairs)} pairs).{Color.END}")
            self.step = 9
            return

        cur_pid = self.current_cfg['pid'] if self.current_cfg else self.pid_input
        pid_gate_help = (f"{Color.BOLD}TRANSPORT LAYER GATEWAY{Color.END}\nCurrent PID: {Color.YELLOW}{cur_pid}{Color.END}\n" "y – change the T2‑MI PID\nn – keep the current value")
        edit_pid = self.ui.ask("Modify T2‑MI PID?", "n", pid_gate_help, "∆¶×")

        self.pid_input = (
            self.ui.ask(
                "Enter T2‑MI PID(s)",
                cur_pid,
                "Packet Identifier for the T2‑MI stream (e.g. 4096, 500, 1000).\nMultiple PIDs allowed (Seperated by commas)",
                "∆¶×",
                category="pid") if edit_pid.lower() == "y" else cur_pid)
        self.step = 9

    def step_service_metadata(self):
        print(
            f"\n{Color.CYAN}┌── {Color.BOLD}FINALIZING IDENTITY ARCHITECTURE{Color.END}{Color.CYAN} " +
            "─" *
            45 +
            "┐")
        self.sid = int(
            self.ui.ask(
                "Feed SID (Base)",
                "800",
                "Base Service ID (decimal). Will be incremented for multiple auto-pairs.",
                "🆔",
                category="sid"))
        self.provider = self.ui.ask(
            "Provider Name",
            "ORTM",
            "Broadcaster name (e.g. ORTM, TNT).",
            "🏢",
            category="provider")
        self.path = self.ui.ask(
            "Relay Path",
            "ortm",
            "URL segment for streaming (affects m3u).",
            "🔗")
        print(f"└" + "─" * 78 + "┘" + Color.END)
        self.step = 10

    def step_build(self):
        # Calc derived values
        raw_sat = int(self.sat_pos * 10)
        ns_sat = (3600 - raw_sat) if self.sat_dir == "W" else raw_sat
        disp_sat = -raw_sat if self.sat_dir == "W" else raw_sat
        ns_hex = format((ns_sat << 16) | self.freq, '08x').lower()
        tsid_hex = format(int(self.TSID, 16), 'x').lower()
        onid_hex = format(int(self.ONID, 16), 'x').lower()

        # Build Transponder Block
        tp_key = f"{ns_hex}:{self.TSID}:{self.ONID}"
        self.new_tps[tp_key] = (
            f"{ns_hex}:{self.TSID}:{self.ONID}\n\ts {self.freq}000:{self.sr}000:{ POL_MAP[ self.pol]}:{self.fec}:" f"{disp_sat}:{self.inv}:{self.sys_type}:{self.mod}:{self.roll}:{self.pilot}:0\n/\n")

        print(f"\n{Color.CYAN}╔" + "═" * 78 + "╗")
        
        if self.auto_pairs:
            # AUTOMATED FLOW
            print(
                f"║ {Color.BOLD}TRANSPORT LAYER DE‑ENCAPSULATION: AUTO-IMPORT MODE{Color.END}{Color.CYAN}".center(88) +
                "║")
            print(f"╚" + "═" * 78 + "╝" + Color.END)
            print(f"  {Color.GREEN}Processing {len(self.auto_pairs)} PID/PLP pairs...{Color.END}")

            for idx, (pid, plp) in enumerate(self.auto_pairs):
                # Increment SID for each pair to ensure unique service references
                current_sid = self.sid + idx
                sid_hex = format(current_sid, 'x').lower()
                pid_hex = format(int(pid), '04x')
                
                # 1. Create Service Entry in lamedb (The Feed Service)
                srv_key = f"{sid_hex}:{ns_hex}:{self.TSID}:{self.ONID}"
                self.new_srvs[srv_key] = (
                    f"{srv_key}:1:0\n{self.provider} PID{pid} PLP{plp}\np:{self.provider},c:15{pid_hex},f:01\n")

                # 2. Add Service to Bouquet
                s_ref_core = f"{sid_hex}:{tsid_hex}:{onid_hex}:{ns_hex}"
                self.bouquet.append(
                    f"#SERVICE 1:0:1:{s_ref_core}:0:0:0:\n#DESCRIPTION {self.provider} PID{pid} PLP{plp} FEED")

                # 3. Process Astra Config and Sub-channels
                print(f"\n{Color.CYAN}┌── {Color.BOLD}AUTO-CONFIGURING PAIR {idx+1}/{len(self.auto_pairs)}: PID {pid}, PLP {plp}{Color.END}{Color.CYAN} " + "─" * (76 - len(str(idx+1)) - len(str(len(self.auto_pairs))) - len(str(pid)) - len(str(plp)) - 40) + "┐")
                
                self._process_single_plp(pid, plp, ns_hex, sid_hex, tsid_hex, onid_hex, auto_import=True)
                print(f"└" + "─" * 78 + "┘" + Color.END)
        else:
            # MANUAL FLOW
            pids = [p.strip() for p in self.pid_input.split(",") if p.strip()]
            print(
                f"║ {Color.BOLD}TRANSPORT LAYER DE‑ENCAPSULATION: {len(pids)} PID(s) DETECTED{Color.END}{Color.CYAN}".center(88) +
                "║")
            print(
                f"║ {Color.BLUE}Initializing routing protocols for T2‑MI streams…{Color.END}".center(86) +
                "║")
            print(f"╚" + "═" * 78 + "╝" + Color.END)

            for pid in pids:
                self._process_single_pid(pid, ns_hex, format(self.sid, 'x'), tsid_hex, onid_hex)

        print(f"\n{Color.BLUE}└" + "─" * 78 + "┘" + Color.END)
        if self.ui.ask(
            "Add another transponder?",
            "n",
            "y = return to Step 4 | n = compile database.",
                "❓") == "y":
            self.step = 4
            # Reset auto pairs for next transponder
            self.auto_pairs = []
        else:
            self.finalize()
            sys.exit(0)

    def _process_single_pid(self, pid, ns_hex, sid_hex, tsid_hex, onid_hex):
        pid_hex = format(int(pid), '04x')
        srv_key = f"{sid_hex}:{ns_hex}:{self.TSID}:{self.ONID}"
        s_ref_core = f"{sid_hex}:{tsid_hex}:{onid_hex}:{ns_hex}"

        # Service Entry
        self.new_srvs[srv_key] = (
            f"{srv_key}:1:0\n{self.provider} PID{pid} FEED\np:{self.provider},c:15{pid_hex},f:01\n")

        # Master Feed
        self.bouquet.append(
            f"#SERVICE 1:0:1:{s_ref_core}:0:0:0:\n#DESCRIPTION {self.provider} PID{pid} FEED")

        # Find existing PLP
        found_plp = "0"
        search_stub = f"f{self.freq}{self.pol.lower()}"
        for k, v in self.existing_astra.items():
            if k.startswith(search_stub) and f"p{pid}" in k:
                found_plp = v.get('plp', "0")
                break

        # PLP UI
        plp_help = (f"{Color.BOLD}PHYSICAL LAYER PIPE (PLP) ASSIGNMENT{Color.END}\nTargeting PID: {Color.GREEN}{pid}{Color.END}\n" "Enter PLP IDs (comma‑separated, 0–255).")
        print(f"\n{Color.YELLOW}┌── {Color.BOLD}DATA PIPE ARCHITECTURE: PID {pid}{Color.END}{Color.YELLOW} " + "─" * (76 - len(str(pid)) - 23) + "┐")

        plps_input = self.ui.ask(
            f"PLPs for PID {pid}", found_plp, plp_help, "📺")

        for plp in [p.strip() for p in plps_input.split(",") if p.strip()]:
            self._process_single_plp(
                pid, plp, ns_hex, sid_hex, tsid_hex, onid_hex, auto_import=False)

    def _process_single_plp(
            self,
            pid,
            plp,
            ns_hex,
            sid_hex,
            tsid_hex,
            onid_hex,
            auto_import=False):
        var_name = f"f{self.freq}{self.pol.lower()}{ self.provider.lower()[ :2]}p{pid}plp{plp}"
        label = f"{self.provider} {self.freq}{self.pol} PID{pid} PLP{plp}"

        self.bouquet.append(
            f"#SERVICE 1:64:0:0:0:0:0:0:0:0:\n#DESCRIPTION --- {label} ---")

        # Astra Config
        block = (f"-- {label}\n{var_name} = make_t2mi_decap({{\n    name = \"decap_{var_name}\",\n"
                 f"    input = \"http://127.0.0.1:8001/1:0:1:{sid_hex}:{tsid_hex}:{onid_hex}:{ns_hex}:0:0:0:\",\n"
                 f"    plp = {plp},\n    pnr = 0,\n    pid = {pid},\n}})\n"
                 f"make_channel({{\n    name = \"{label}\",\n    input = {{ \"t2mi://{var_name}\" }},\n"
            f"    output = {{ \"http://0.0.0.0:9999/{self.path}/{self.freq}_{self.sat_pos}{self.sat_dir.lower()}_plp{plp}\" }},\n}})\n")
        self.astra_blocks.append(block)

        # Sub-channel CSV mapping
        self._map_csv_channels(pid, plp, ns_hex, tsid_hex, onid_hex, auto_import=auto_import)

    def _map_csv_channels(self, pid, plp, ns_hex, tsid_hex, onid_hex, auto_import=False):
        orbital_folder = f"{self.sat_pos}{self.sat_dir.upper()}"
        csv_dir = os.path.join("channellist", orbital_folder)

        ch_file = None
        
        if auto_import:
            # Logic 2: Automatic import based on filename convention
            # Format: freqpolsrPLPxPIDx.csv (e.g. 4014L7325PLP0PID4096.csv)
            filename = f"{self.freq}{self.pol}{self.sr}PLP{plp}PID{pid}.csv"
            target_path = os.path.join(csv_dir, filename)
            
            print(f"  {Color.CYAN}🔍 Searching for auto-import file: {filename}{Color.END}")
            
            if os.path.isfile(target_path):
                ch_file = target_path
                print(f"  {Color.GREEN}✔ Found channel map: {filename}{Color.END}")
            else:
                print(f"  {Color.YELLOW}ℹ No auto-map file found at: {target_path}{Color.END}")
        
        else:
            # Logic: Manual import (existing logic)
            suggestions = []
            if os.path.isdir(csv_dir):
                suggestions = sorted([f for f in os.listdir(
                    csv_dir) if f.lower().endswith('.csv')], key=lambda x: x.lower())

            csv_help = (f"{Color.BOLD}SUB‑CHANNEL MAPPING PROTOCOL{Color.END}\nImport virtual services for PID {pid} / PLP {plp}\n" f"Auto‑scan found {len(suggestions)} CSV file(s) in ./{csv_dir}")

            print(f"\n{Color.YELLOW}┌── {Color.BOLD}SUB‑CHANNEL MAPPING: PID {pid} PLP {plp}{Color.END}{Color.YELLOW} " + "─" * (76 - 28 - len(str(pid)) - len(str(plp))) + "┐")
            for line in csv_help.split("\n"):
                print(
                    f"│ {Color.BLUE}📂 {line.ljust(74)}{Color.END}{Color.YELLOW} │")
            if suggestions:
                print(f"┠" + "─" * 78 + "┨")
                for idx, fname in enumerate(suggestions, 1):
                    print(
                        f"│ {Color.CYAN} [{idx}] {fname.ljust(72)}{Color.END}{Color.YELLOW} │")
            print(f"└" + "─" * 78 + "┘" + Color.END)

            ch_choice = self.ui.path_prompt(f"  Select file [#] or path for {orbital_folder} PLP {plp}: ")

            if ch_choice.lower() == "back":
                raise GoBack()

            if ch_choice.isdigit() and 1 <= int(ch_choice) <= len(suggestions):
                ch_file = os.path.join(csv_dir, suggestions[int(ch_choice) - 1])
            else:
                ch_file = ch_choice

        # Common Processing
        if ch_file and os.path.isfile(ch_file):
            sub_url = f"http://0.0.0.0:9999/{self.path}/{self.freq}_{self.sat_pos}{self.sat_dir.lower()}_plp{plp}".replace(":", "%3a")
            print(
                f"  {Color.CYAN}⚙️  Parsing {os.path.basename(ch_file)}…{Color.END}")
            with open(ch_file, "r", encoding="utf8") as fh:
                for csv_line in fh:
                    if "," not in csv_line:
                        continue
                    try:
                        csid, name, stype = [
                            x.strip() for x in csv_line.strip().split(",")]
                        csid_hex = format(int(csid), 'x').lower()
                        c_ref = f"1:0:{stype}:{csid_hex}:{tsid_hex}:{onid_hex}:{ns_hex}:0:0:0:{sub_url}:{name}"
                        self.bouquet.append(
                            f"#SERVICE {c_ref}\n#DESCRIPTION {name}")
                        print(f"    {Color.GREEN}✔ Added: {name}{Color.END}")
                    except Exception as exc:
                        print(
                            f"    {Color.RED}✖ Error parsing line: {csv_line.strip()} ({exc}){Color.END}")
        else:
            if ch_file and not auto_import:
                print(f"  {Color.RED}⚠ File not found: {ch_file}{Color.END}")
            elif not ch_file and not auto_import:
                print(
                    f"  {Color.BLUE}ℹ No CSV import for this pipe.{Color.END}")

    def finalize(self):
        print(f"\n{Color.CYAN}╔" + "═" * 78 + "╗")
        print(
            f"║ {Color.BOLD}COMPILING ARCHITECTURAL BLUEPRINTS{Color.END}{Color.CYAN}".center(88) +
            "║")
        print(f"╚" + "═" * 78 + "╝" + Color.END)

        backup_name = self.config.backup_file(self.merge_path)
        self.config.compile_lamedb(
            self.merge_path, self.new_tps, self.new_srvs)

        # Live Swap
        swap_applied = False
        if os.path.abspath(self.merge_path) != os.path.abspath("./lamedb"):
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

            if self.ui.ask(
                "Update source lamedb?",
                "n",
                "y = Overwrite original file | n = Keep edits in ./lamedb only",
                    "🔄").lower() == "y":
                swap_applied = self.config.perform_live_swap(self.merge_path)

        # Bouquet
        self.config.sync_bouquet(
            self.mode,
            self.bouquet_file,
            self.bouquet,
            self.bouquet_name)

        # Astra
        astra_path = self.config.write_astra_conf(self.mode, self.astra_blocks)

        print(
            f"\n{Color.GREEN}✅ ALL FILES SYNCHRONIZED SUCCESSFULLY.{Color.END}")
        print(f"{Color.CYAN}📂 LOCAL WORKSPACE : ./lamedb")
        if backup_name:
            print(f"📂 SOURCE BACKUP  : {backup_name}")

        if swap_applied:
            print(
                f"📂 LIVE DATABASE  : {self.merge_path} {Color.BOLD}(UPDATED){Color.END}")
        else:
            print(
                f"📂 SOURCE TARGET  : {self.merge_path} {Color.BOLD}(UNTOUCHED){Color.END}")

        print(f"📂 BOUQUET        : ./{self.bouquet_file}")
        print(f"📂 ASTRA          : ./{astra_path}{Color.END}")
        print(
            f"\n{Color.GREEN}{Color.BOLD}✨ v10.3 ENCYCLOPEDIA ARCHITECT LOCKED!{Color.END}")


if __name__ == "__main__":
    app = SatelliteArchitect()
    app.run()
