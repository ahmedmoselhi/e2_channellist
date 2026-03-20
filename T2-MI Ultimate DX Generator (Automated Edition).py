import re
import os
import sys
import shutil
import time
import csv
import logging
from typing import Dict, List, Optional, Tuple, Any, Set

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
    DIM = '\033[2m'
    MAGENTA = '\033[95m'
    END = '\033[0m'
    BG_BLUE = '\033[44m'
    BG_CYAN = '\033[46m'


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
        def _import_modules():
            from prompt_toolkit import prompt as pt_prompt
            from prompt_toolkit.history import FileHistory
            from prompt_toolkit.shortcuts import radiolist_dialog
            from prompt_toolkit.completion import PathCompleter
            return pt_prompt, FileHistory, radiolist_dialog, PathCompleter

        try:
            # Attempt initial import
            pt_prompt, FileHistory, radiolist_dialog, PathCompleter = _import_modules()
        except ImportError:
            # If missing, install and retry
            self._install_dependencies()
            try:
                pt_prompt, FileHistory, radiolist_dialog, PathCompleter = _import_modules()
            except ImportError:
                print(f"{Color.RED}❌ Failed to initialize environment.{Color.END}")
                sys.exit(1)

        # Assign to instance variables once
        self.pt_prompt = pt_prompt
        self.FileHistory = FileHistory
        self.radiolist_dialog = radiolist_dialog
        self.PathCompleter = PathCompleter

    def _install_dependencies(self):
        import subprocess
        if "pyenv" not in sys.executable and os.path.exists(os.path.expanduser("~/.pyenv")):
            print(f"{Color.YELLOW}⚠ System Python detected. Switching to environment shim...{Color.END}")
            os.execvp("python", ["python"] + sys.argv)

        print(f"\n{Color.YELLOW}⚠ Module 'prompt_toolkit' not found.{Color.END}")
        print(f"{Color.CYAN}⚙ Attempting installation...{Color.END}")

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
                print(f"{Color.GREEN}✅ Success!{Color.END}\n")
                return
            except BaseException:
                continue

        print(f"{Color.RED}❌ Failed to install prompt_toolkit.{Color.END}")
        sys.exit(1)

    def _init_history(self):
        if not os.path.exists("workspace"):
            os.makedirs("workspace")
            
        # Use absolute paths for history files
        ws_path = os.path.abspath("workspace")
        self.history_files = { 
            "default": self.FileHistory(os.path.join(ws_path, ".dx_history_default")), 
            "paths": self.FileHistory(os.path.join(ws_path, ".dx_history_paths")), 
            "bouquet": self.FileHistory(os.path.join(ws_path, ".dx_history_bouquet")), 
            "freq": self.FileHistory(os.path.join(ws_path, ".dx_history_freq")), 
            "pid": self.FileHistory(os.path.join(ws_path, ".dx_history_pid")), 
            "sid": self.FileHistory(os.path.join(ws_path, ".dx_history_sid")), 
            "provider": self.FileHistory(os.path.join(ws_path, ".dx_history_provider")) 
        }
        self.path_completer = self.PathCompleter(expanduser=True)

    def clear_screen(self):
        os.system('cls' if os.name == 'nt' else 'clear')

    def print_header(self):
        width = 80
        print(f"{Color.BLUE}{Color.BOLD}" + "═" * width)
        print(r"""
   ╦ ╦┌─┐┌┐ ╔╦╗┌─┐┬─┐┌┬┐┬┌┐┌┌─┐┬  
   ║║║├┤ ├┴┐ ║ ├┤ ├┬┘│││││││├─┤│  
  ╚╩╝└─┘└─┘ ╩ └─┘┴└─┴ ┴┴┘└┘┴ ┴┴─┘┘┤
                              ──┘   
        """.center(width))
        print("  [ UNIVERSAL ARCHITECT v15.6 - Verbose Edition ]".center(width))
        print("═" * width + f"{Color.END}")

    def exit_gracefully(self):
        print(f"\n\n{Color.RED}⚠ Process interrupted by user (Ctrl+C).{Color.END}")
        print(f"{Color.YELLOW}Exiting Universal Architect...{Color.END}")
        sys.exit(0)

    def draw_progress(self, percent, width=40, task="Processing"):
        filled = int(width * percent / 100)
        bar = "█" * filled + "░" * (width - filled)
        sys.stdout.write(f"\r  {Color.CYAN}{task.ljust(20)}: {Color.BOLD}[{bar}]{Color.END} {percent}%")
        sys.stdout.flush()
        time.sleep(0.01)

    def print_banner(self, text, icon="ℹ", color=Color.CYAN):
        width = 80
        print(f"\n{color}╔{'═' * (width - 2)}╗")
        
        clean_text = re.sub(r'\x1b\[[0-9;]*m', '', text)
        padding = (width - 2 - len(clean_text) - 2) // 2
        header_line = f"║ {' ' * padding}{text}{' ' * (width - 2 - len(clean_text) - padding - 2)} ║"
        print(header_line)
        
        print(f"╚{'═' * (width - 2)}╝{Color.END}")

    def ask(self, prompt_text, default=None, help_text="", icon="ℹ", allow_back=True, category="default"):
        width = 80
        while True:
            print(f"\n{Color.YELLOW}╔{'═' * (width - 2)}╗")
            
            # Header Alignment
            header_text = "📌 INPUT REQUIRED"
            visual_len = 18
            padding_len = width - 2 - visual_len
            print(f"║ {Color.BOLD}{header_text}{Color.END}{Color.YELLOW}{' ' * padding_len}║")
            
            print(f"╠{'═' * (width - 2)}╣")

            full_help = help_text
            if allow_back:
                full_help += "\n[ Type 'back' to return ]"
            if default is not None:
                full_help += f"\n[ DEFAULT: {default} ]"

            for line in full_help.strip().split("\n"):
                clean_len = len(re.sub(r'\x1b\[[0-9;]*m', '', line))
                vis_pad = width - 3 - clean_len 
                print(f"║ {line}{' ' * vis_pad}║")
            
            print(f"╚{'═' * (width - 2)}╝{Color.END}")

            cat_history = self.history_files.get(category, self.history_files["default"])
            val = self.pt_prompt(f"  ➤ {prompt_text}: ", history=cat_history).strip()

            if val.lower() == "back" and allow_back:
                raise GoBack()
            if val == "" and default is not None:
                return default
            if val != "":
                return val
            print(f"  {Color.RED}⚠ This field cannot be empty.{Color.END}")

    def choose_option(self, title, text, options, default=None):
        return self.radiolist_dialog(
            title=f" {title} ",
            text=text,
            values=options,
            default=default,
        ).run()

    def file_browser(self, start_path="."):
        current_dir = os.path.abspath(start_path)
        while True:
            try:
                items = sorted(os.listdir(current_dir))
                options = [("..", "⬆  .. Parent Directory")]

                for item in items:
                    path = os.path.join(current_dir, item)
                    if os.path.isdir(path):
                        options.append((path, f"📁 {item}/"))
                    elif item == "lamedb" or item.endswith(".bak"):
                        options.append((path, f"📄 {item}"))

                selection = self.radiolist_dialog(
                    title=" FILE MANAGER ",
                    text=f"Directory: {current_dir}\n\nSelect a file or Cancel for default.",
                    values=options
                ).run()

                if selection is None:
                    return os.path.join("workspace", "lamedb")
                if selection == "..":
                    current_dir = os.path.dirname(current_dir)
                elif os.path.isdir(selection):
                    current_dir = selection
                else:
                    return selection
            except Exception as e:
                print(f"  {Color.RED}⚠ Error: {e}.{Color.END}")
                return os.path.join("workspace", "lamedb")

    def path_prompt(self, text, history_key="paths"):
        return self.pt_prompt(
            text,
            completer=self.path_completer,
            history=self.history_files.get(history_key, self.history_files["paths"])).strip()


# ----------------------------------------------------------------------
# Config Manager: Handles file I/O and parsing
# ----------------------------------------------------------------------
class ConfigManager:
    timestamp = time.strftime("%Y-%m-%d_%H-%M-%S")
    def __init__(self, ui: UIManager):
        self.ui = ui

    def parse_astra_configs(self) -> Dict[str, Dict[str, str]]:
        configs = {}
        conf_path = "workspace/astra/astra.conf"
        if os.path.exists(conf_path):
            with open(conf_path, "r", encoding="utf-8") as fh:
                content = fh.read()
                pattern = (r'(\w+)\s*=\s*make_t2mi_decap\({\s*.*?plp\s*=\s*(\d+),.*?pid\s*=\s*(\d+),')
                for var_name, plp, pid in re.findall(pattern, content, re.DOTALL):
                    configs[var_name] = {"plp": plp, "pid": pid}
        return configs

    def get_current_params(self, freq, pol, existing_astra):
        key = f"f{freq}{pol.lower()}"
        for k, v in existing_astra.items():
            if k.startswith(key):
                return v
        return None

    def wipe_workspace(self):
        print(f"\n{Color.RED}⚠ WARNING: EXECUTING DATABASE WIPE (Preserving History)...{Color.END}")
        for i in range(0, 101, 10):
            self.ui.draw_progress(i, task="Purging Data")
        
        ws_path = "workspace"
        
        if not os.path.exists(ws_path):
            os.makedirs(ws_path)

        preserved_prefixes = ['.dx_history_', 'architect'] # Changed to prefix match
        preserved_names = [] # Removed specific name 'architect.log' as prefix covers it

        for item in os.listdir(ws_path):
            full_path = os.path.join(ws_path, item)
            should_preserve = False
            
            # Check specific names (if any remain in preserved_names)
            if item in preserved_names:
                should_preserve = True
            
            # Check prefixes
            if not should_preserve:
                for prefix in preserved_prefixes:
                    if item.startswith(prefix):
                        should_preserve = True
                        break
            
            if should_preserve:
                continue

            try:
                if os.path.isdir(full_path):
                    shutil.rmtree(full_path)
                elif os.path.isfile(full_path):
                    os.remove(full_path)
            except Exception as e:
                print(f"   ⚠ Error removing {item}: {e}")

        astra_path = os.path.join(ws_path, "astra")
        if not os.path.exists(astra_path):
            os.makedirs(astra_path)
            
        print(f"\n  {Color.GREEN}✨ Workspace initialized. History preserved.{Color.END}")

    def load_frequency_csvs(self, freq_dir="frequencies"):
        if not os.path.exists(freq_dir):
            return []
        
        files = [f for f in os.listdir(freq_dir) if f.endswith('.csv')]
        
        def sort_key(filename):
            try:
                parts = re.findall(r'(\d+\.?\d*)([WE])', filename)
                if parts:
                    pos_str, dir_char = parts[0]
                    pos = float(pos_str)
                    if dir_char == 'W':
                        return (0, -pos)
                    else:
                        return (1, pos)
            except:
                pass
            return (2, 0)

        return sorted(files, key=sort_key)

    def read_csv(self, filepath):
        with open(filepath, 'r', encoding='utf-8') as f:
            return list(csv.DictReader(f))

    def backup_file(self, path):
        if os.path.isfile(path):
            try:
                backup_name = f"{path}_{self.timestamp}.bak"
                shutil.copy2(path, backup_name)
                print(f"\n  {Color.GREEN}💾 BACKUP CREATED: {backup_name}{Color.END}")
                return backup_name
            except Exception as e:
                print(f"\n  {Color.RED}⚠ BACKUP FAILED: {str(e)}{Color.END}")
        else:
            print(f"\n  {Color.CYAN}ℹ INFO: No existing database found to backup.{Color.END}")
        return None

    def compile_lamedb(self, merge_path, new_tps, new_srvs):
        for i in range(0, 101, 25):
            self.ui.draw_progress(i, task="Consolidating lamedb")

        if os.path.isfile(merge_path):
            with open(merge_path, "r", encoding="utf-8", errors="ignore") as fh:
                db_lines = [line.rstrip() for line in fh.readlines()]
        else:
            db_lines = ["eDVB services /4/", "transponders", "end", "services", "end"]

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

        with open("workspace/lamedb", "w", encoding="utf-8", newline='\n') as fh:
            fh.write("\n".join(db_lines) + "\n")

    def perform_live_swap(self, merge_path):
        if os.path.abspath(merge_path) != os.path.abspath("workspace/lamedb"):
            try:
                shutil.copy2("workspace/lamedb", merge_path)
                print(f"  {Color.GREEN}✨ SUCCESS: {merge_path} updated.{Color.END}")
                return True
            except Exception as e:
                print(f"  {Color.RED}✖ SWAP FAILED: {str(e)}{Color.END}")
        return False

    def sync_bouquet(self, mode, bouquet_file, bouquet_lines, bouquet_name):
        for i in range(0, 101, 50):
            self.ui.draw_progress(i, task="Syncing Bouquet")

        final_bouquet = []
        if mode == "modify" and os.path.isfile(bouquet_file):
            with open(bouquet_file, "r", encoding="utf-8") as fh:
                existing = fh.readlines()

            new_refs = [line.split(":")[-5:-1] for line in bouquet_lines if line.startswith("#SERVICE")]
            skip_next = False
            for existing_line in existing:
                if skip_next:
                    skip_next = False
                    continue
                if existing_line.startswith("#NAME"):
                    final_bouquet.append(existing_line.strip())
                    continue
                duplicate = any(all(part in existing_line for part in ref) for ref in new_refs if ":" in existing_line)
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

        if not os.path.isdir("workspace/astra"):
            os.makedirs("workspace/astra")
        astra_path = "workspace/astra/astra.conf"

        if mode == "modify" and os.path.isfile(astra_path):
            with open(astra_path, "r", encoding="utf-8") as fh:
                old_conf = fh.read()
            for block in astra_blocks:
                lines = block.strip().split('\n')
                var_line = [l for l in lines if '=' in l and 'make_t2mi_decap' in l]
                if var_line:
                    v_name = var_line[0].split('=')[0].strip()
                    pattern = (rf"-- .*?\n{re.escape(v_name)} = .*?}}\)\n" rf"make_channel.*?}}\)\n")
                    old_conf = re.sub(pattern, "", old_conf, flags=re.DOTALL)
            
            final_astra = (old_conf.strip() + "\n\n-- [ ARCHITECT MODIFIED ENTRIES ] --\n")
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
    POL_CSV_MAP = {"2": "L", "3": "R", "0": "H", "1": "V"}
    timestamp = time.strftime("%Y-%m-%d_%H-%M-%S")
    def __init__(self):
        self.ui = UIManager()
        self.config = ConfigManager(self.ui)
        
        self.logger = logging.getLogger('ArchitectLogger')
        self.setup_logger()

        self.mode = "modify"
        self.existing_astra = {}
        self.merge_path = os.path.join("workspace", "lamedb")

        self.new_tps = {}
        self.new_srvs = {}
        self.bouquet = []
        self.astra_blocks = []

        self.bouquet_name = "T2MI_DX"
        self.bouquet_file = os.path.join("workspace", "userbouquet.t2mi_dx.tv")
        self.ONID = "0001"
        self.TSID = "0001"

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

        self.pid_input = "4096"
        self.plps_input = "0"
        self.sid = 800
        self.provider = "ORTM"
        self.path = "ortm"
        
        self.is_multistream = False
        self.isi_input = "-1"

        self.global_sid_counter = 800
        
        self.printed_astra_headers: Set[str] = set()

    def setup_logger(self):
        self.logger.setLevel(logging.DEBUG)
        
        # Ensure workspace exists
        os.makedirs("workspace", exist_ok=True)
        
        if not self.logger.handlers:
            # Append execution date AND time to filename (Hour-Minute-Second)
            log_file = f'workspace/architect_{self.timestamp}.log'
            
            try:
                file_handler = logging.FileHandler(log_file, mode='a', encoding='utf-8')
                formatter = logging.Formatter('%(asctime)s | %(levelname)-8s | %(message)s', datefmt='%Y-%m-%d %H:%M:%S')
                file_handler.setFormatter(formatter)
                self.logger.addHandler(file_handler)
                self.logger.info("="*60)
                self.logger.info("LOGGER INITIALIZED [VERBOSE DEBUG MODE]")
                self.logger.info("="*60)
            except Exception as e:
                print(f"{Color.RED}⚠ Failed to initialize logger: {e}{Color.END}")

    def _calculate_namespace(self, freq, sat_pos, sat_dir):
        """Calculates Enigma2 namespace hex and display position."""
        raw_sat = int(sat_pos * 10)
        ns_sat = (3600 - raw_sat) if sat_dir == "W" else raw_sat
        disp_sat = -raw_sat if sat_dir == "W" else raw_sat
        ns_hex = format((ns_sat << 16) | freq, '08x').lower()
        return ns_hex, disp_sat

    def _parse_pid_plps(self, raw_str):
        """Parses the 'pids-plps' string format into a list of (pid, plp) tuples."""
        pairs = []
        if not raw_str:
            return pairs
        
        clean_str = raw_str.strip('{}')
        if not clean_str:
            return pairs
            
        for item in clean_str.split(';'):
            if ',' in item:
                p, l = item.split(',', 1)
                pairs.append((p.strip(), l.strip()))
        return pairs

    def run(self):
        try:
            self.ui.clear_screen()
            self.ui.print_header()

            self.step_init()

            self.ui.print_banner("DATABASE SOURCE SELECTION", "📂", Color.YELLOW)
            print(f"  {Color.BLUE}📂 Opening File Manager...{Color.END}")
            self.merge_path = self.ui.file_browser("workspace")
            print(f"  {Color.GREEN}✅ Target Active: {Color.BOLD}{self.merge_path}{Color.END}")
            self.logger.info(f"Target database set to: {self.merge_path}")

            help_txt = ("The name of the favorites group in your Enigma2 receiver.\n"
                        "Example: 'T2MI_DX' or 'MyProvider'")
            self.bouquet_name = self.ui.ask(
                "Bouquet name", "T2MI Services", help_txt, "🏷️", category="bouquet")
            
            self._prepare_bouquet_file()
            
            help_sid = ("The starting Service ID (SID) in decimal format.\n"
                        "Each new service will increment this number.\nExample: 800")
            base_sid_str = self.ui.ask("Starting SID", "800", help_sid, "🆔", category="sid")
            self.global_sid_counter = int(base_sid_str)

            while True:
                choice = self.ui.choose_option(
                    "ARCHITECT MAIN MENU",
                    "Select an operation mode:",
                    [
                        ("manual", "🛠️ MANUAL ENTRY (Step-by-step or Single CSV Row)"),
                        ("batch", "⚡ BATCH IMPORT (Process entire CSV file automatically)"),
                        ("auto", "🤖 FULLY AUTOMATED MODE (Process all CSVs sequentially)"),
                        ("finish", "✅ FINISH & COMPILE (Save and Exit)")
                    ],
                    "manual"
                )

                if choice is None or choice == "finish":
                    break
                elif choice == "manual":
                    self.logger.info("Mode selected: Manual Entry")
                    self.run_manual_flow()
                elif choice == "batch":
                    self.logger.info("Mode selected: Batch Import")
                    self.run_batch_flow()
                elif choice == "auto":
                    self.logger.info("Mode selected: Fully Automated")
                    self.run_auto_mode()

            self.finalize()

        except KeyboardInterrupt:
            self.ui.exit_gracefully()

    def step_init(self):
        self.ui.print_banner("SESSION INITIALIZATION", "⚙️", Color.CYAN)

        self.mode = self.ui.choose_option(
            "OPERATION MODE",
            "How should existing database files be handled?",
            [
                ("modify", "📝 MODIFY/APPEND – read existing files and update matches."),
                ("fresh", "🧹 FRESH START – wipe everything and start a new database."),
            ],
            default="modify"
        )
        if self.mode is None:
            sys.exit(0)

        self.logger.info(f"Session started in {self.mode.upper()} mode.")

        if self.mode == "fresh":
            self.config.wipe_workspace()
        else:
            if not os.path.exists("workspace"):
                 os.makedirs("workspace/astra", exist_ok=True)
            for i in range(0, 101, 20):
                self.ui.draw_progress(i, task="Parsing Files")
            print(f"\n  {Color.GREEN}📂 Existing database loaded into memory.{Color.END}")

        self.existing_astra = self.config.parse_astra_configs() if self.mode == "modify" else {}

    def _prepare_bouquet_file(self):
        sanitized_name = self.bouquet_name.lower().replace(' ', '_')
        base_filename = f"userbouquet.{sanitized_name}.tv"
        
        if self.mode == "modify":
            full_path = os.path.join("workspace", base_filename)
            if os.path.exists(full_path):
                counter = 1
                while True:
                    new_filename = f"userbouquet.{sanitized_name}-{counter}.tv"
                    new_path = os.path.join("workspace", new_filename)
                    if not os.path.exists(new_path):
                        self.bouquet_file = new_path
                        print(f"\n  {Color.YELLOW}ℹ Existing bouquet found. Creating new file: {Color.BOLD}{self.bouquet_file}{Color.END}")
                        self.logger.info(f"Bouquet file set to: {self.bouquet_file}")
                        break
                    counter += 1
            else:
                self.bouquet_file = full_path
        else:
            self.bouquet_file = os.path.join("workspace", base_filename)

    # ==================================================================
    # HELPER METHODS
    # ==================================================================
    def _get_relay_path(self, provider_name):
        if not provider_name:
            return "stream"
        
        words = provider_name.strip().split()
        
        if len(words) == 0:
            return "stream"
        elif len(words) == 1:
            return words[0].lower()
        else:
            return (words[0] + words[1]).lower()

    # ==================================================================
    # AUTOMATED MODE LOGIC
    # ==================================================================
    def run_auto_mode(self):
        self.ui.print_banner("AUTOMATED GLOBAL PROCESSING", "🤖", Color.MAGENTA)
        
        csv_files = self.config.load_frequency_csvs()
        if not csv_files:
            print(f"\n{Color.RED}❌ No CSV files found in './frequencies' directory.{Color.END}")
            return

        print(f"\n  {Color.CYAN}📂 Found {len(csv_files)} satellite databases. Preparing for global scan...{Color.END}")
        print(f"  {Color.DIM}   Order: Furthest West -> Furthest East{Color.END}")

        help_def = ("Global default provider name if 'prov' column is missing in any file.")
        default_provider = self.ui.ask("Global Default Provider", "Provider", help_def, "🏢", category="provider")
        
        total_files = len(csv_files)
        
        for idx, f in enumerate(csv_files):
            print(f"\n{Color.MAGENTA}══════════════════════════════════════════════════════════════════════════════════════{Color.END}")
            print(f"{Color.MAGENTA}  🛰️  FILE [{idx+1}/{total_files}]: {Color.BOLD}{f}{Color.END}")
            
            self.logger.info(f"AUTO_MODE: Processing file [{idx+1}/{total_files}] -> {f}")
            
            self.process_csv_batch(f, default_provider=default_provider)
        
        print(f"\n{Color.GREEN}✅ All satellites processed.{Color.END}")
        
        # CALL FINALIZE WITH AUTO-SWAP ENABLED
        self.finalize(auto_apply_swap=True)
        
        self.logger.info("Automated run finished. Exiting.")
        sys.exit(0)

    # ==================================================================
    # MANUAL FLOW LOGIC
    # ==================================================================
    def run_manual_flow(self):
        try:
            self.step_frequency()
            
            if not self.auto_pairs:
                self.step_polarization()
                self.step_physical_layer()
                self.step_multistream()
            
            self.step_service_metadata()
            self.step_build()

        except GoBack:
            print(f"  {Color.YELLOW}↩ Returning to Main Menu...{Color.END}")
            return

    def step_frequency(self):
        self.ui.print_banner("FREQUENCY SELECTION", "📡", Color.CYAN)

        csv_files = self.config.load_frequency_csvs()
        if csv_files:
            print(f"\n{Color.CYAN}📂 Frequency Database Browser (Sorted W->E){Color.END}")
            options = [("manual", "⌨️  Manual Entry (Type Frequency)")] + [(f, f"📄 {f}") for f in csv_files]
            choice = self.ui.choose_option(
                "Import Source",
                "Select a CSV to load a single row, or choose Manual Entry:",
                options,
                "manual")

            if choice != "manual" and choice is not None:
                self._load_from_csv(choice)
                return

        help_f = ("Enter the transponder frequency in MHz.\n"
                  "Example: 4014 (C-Band) or 11495 (Ku-Band)")
        self.freq = int(self.ui.ask("Target Frequency", "4014", help_f, "📡", category="freq"))
        
        self.auto_pairs = []
        self.isi_input = "-1"
        self.is_multistream = False

    def _load_from_csv(self, filename):
        reader = self.config.read_csv(os.path.join("frequencies", filename))

        print(f"\n{Color.YELLOW}┌{'─' * 78}┐")
        print(f"│ {Color.BOLD}SELECT TRANSPONDER FROM DATABASE{Color.END}{' ' * 45}│")
        print(f"├{'─' * 78}┤")
        for idx, r in enumerate(reader):
            label = f"{r['Freq']} {r['Pol']} ({r['Pos']}{r['Dir']}) SR:{r['SR']}"
            print(f"│  [{idx}] {label.ljust(70)}│")
        print(f"└{'─' * 78}┘{Color.END}")

        help_tp = ("Enter the index number from the list above.\n"
                   "Example: 0")
        tp_idx_str = self.ui.ask("Select TP Index [#]", "0", help_tp, "📡")
        selected_row = reader[int(tp_idx_str)]

        # VERBOSE LOGGING
        self.logger.debug("-" * 60)
        self.logger.debug(f"LOADED CSV ROW INDEX: {tp_idx_str}")
        for k, v in selected_row.items():
            self.logger.debug(f"  CSV_COL [{k}]: {v}")
        self.logger.debug("-" * 60)

        self.freq = int(selected_row['Freq'])
        raw_pol = selected_row['Pol'].upper()
        self.pol = self.POL_CSV_MAP.get(raw_pol, raw_pol)
        self.sr = int(selected_row['SR'])
        self.sat_pos = float(selected_row['Pos'])
        self.sat_dir = selected_row['Dir'].upper()
        self.inv = selected_row['Inv']
        self.fec = selected_row['FEC']
        self.sys_type = selected_row['Sys']
        self.mod = selected_row['Mod']
        self.roll = selected_row['RO']
        self.pilot = selected_row['Pilot']
        
        raw_isi = selected_row.get('isi', '-1').strip()
        if raw_isi and raw_isi != '-1':
            self.is_multistream = True
            self.isi_input = raw_isi
        else:
            self.is_multistream = False
            self.isi_input = "-1"

        raw_pairs = selected_row.get('pids-plps', '')
        self.auto_pairs = self._parse_pid_plps(raw_pairs)
        
        if not self.auto_pairs:
            self.pid_input = selected_row.get('PID', '4096')
            self.plps_input = selected_row.get('PLP', '0')

        self.provider = selected_row.get('prov', selected_row.get('Provider', 'Unknown')).strip()
        self.path = self._get_relay_path(self.provider)
        
        self.current_cfg = self.config.get_current_params(self.freq, self.pol, self.existing_astra)
        print(f"\n{Color.GREEN}✅ Tuning Data Loaded: {self.freq} {self.pol} {self.sat_pos}{self.sat_dir}{Color.END}")
        print(f"   Provider: {Color.CYAN}{self.provider}{Color.END} -> Relay Path: {Color.CYAN}/{self.path}/{Color.END}")
        self.logger.info(f"Loaded from CSV: {self.freq}{self.pol} {self.sat_pos}{self.sat_dir} Prov: {self.provider} Path: {self.path}")

    def step_polarization(self):
        help_pol = ("Select the physical antenna orientation.\n"
                    "Examples: H (Horizontal), V (Vertical), L (Left Circular)")
        self.pol = self.ui.choose_option("Polarization", help_pol, [
            ("H", "Horizontal (18V)"), ("V", "Vertical (13V)"), 
            ("L", "Left Circular"), ("R", "Right Circular")], "L")
        if self.pol is None:
            raise GoBack()

        self.current_cfg = self.config.get_current_params(self.freq, self.pol, self.existing_astra)

    def step_physical_layer(self):
        help_edit = ("Do you want to modify Symbol Rate, FEC, Modulation?\n"
                     "y = Yes, edit details.\nn = No, use defaults (Typical for DVB-S2).")
        edit_tp = self.ui.ask("Modify Physical Layer?", "n", help_edit, "⚙️")

        if edit_tp.lower() == "y":
            self.sr = int(self.ui.ask("Symbol Rate (kS/s)", "7325", "Example: 30000 or 7325", "📶"))
            self.sat_pos = float(self.ui.ask("Orbital Position", "18.1", "Example: 36.0 or 8.1", "🌍"))
            self.sat_dir = self.ui.ask("Direction (E/W)", "W", "E = East, W = West", "🧭").upper()
            self.inv = self.ui.ask("Inversion", "2", "0=Off, 1=On, 2=Auto", "🛠️")
            self.fec = self.ui.ask("FEC", "9", "9=Auto, 2=2/3, 3=3/4", "🏗️")
            self.sys_type = self.ui.ask("Delivery System", "1", "0=DVB-S, 1=DVB-S2", "🏗️")
            self.mod = self.ui.ask("Modulation Type", "2", "1=QPSK, 2=8PSK", "💠")
            self.roll = self.ui.ask("Roll-Off Factor", "0", "0=0.35, 1=0.25, 2=0.20", "🌊")
            self.pilot = self.ui.ask("Pilot Tones", "2", "0=Off, 1=On, 2=Auto", "🔦")
        else:
            self.sr, self.sat_pos, self.sat_dir, self.inv, self.fec, self.sys_type, self.mod, self.roll, self.pilot = 7325, 18.1, "W", "2", "9", "1", "2", "0", "2"

    def step_multistream(self):
        help_mis = ("Multistream (ISI) allows multiple streams on one transponder.\n"
                    "Common in professional networks.\n"
                    "y = Yes (Enter ISI IDs).\nn = No (Standard Transponder).")
        is_mis = self.ui.ask("Enable Multistream?", "n", help_mis, "🌊")
        
        if is_mis.lower() == 'y':
            self.is_multistream = True
            help_isi = ("Enter numeric Stream IDs separated by commas.\n"
                        "Example: 171, 172, 173")
            self.isi_input = self.ui.ask("Stream IDs (ISIs)", "171", help_isi, "🆔")
        else:
            self.is_multistream = False
            self.isi_input = "-1"

    def step_service_metadata(self):
        self.ui.print_banner("SERVICE METADATA", "📝", Color.CYAN)
        
        help_sid = ("Base Service ID (decimal). Each PID/ISI/PLP will increment this.\nExample: 800")
        self.sid = int(self.ui.ask("Feed SID", str(self.global_sid_counter), help_sid, "🆔", category="sid"))
        
        help_prov = ("Broadcaster name used in metadata.\nExample: 'ORTM'")
        self.provider = self.ui.ask("Provider Name", self.provider, help_prov, "🏢", category="provider")
        
        self.path = self._get_relay_path(self.provider)
        
        help_path = ("URL path segment for the stream.\nExample: 'ortm' -> http://server:port/ortm/...")
        self.path = self.ui.ask("Relay Path", self.path, help_path, "🔗", category="paths")

    def step_build(self):
        ns_hex, disp_sat = self._calculate_namespace(self.freq, self.sat_pos, self.sat_dir)
        
        current_sid = self.sid

        if self.is_multistream:
            isi_list = [i.strip() for i in self.isi_input.split(",")]
            
            if self.auto_pairs:
                for idx, (pid, plp) in enumerate(self.auto_pairs):
                    if idx < len(isi_list):
                        isi = isi_list[idx]
                        self._process_single_service(isi, pid, plp, ns_hex, disp_sat, current_sid)
                        current_sid += 1
                    else:
                        print(f"  {Color.YELLOW}⚠ Warning: Pair {idx} (PID {pid}) has no corresponding ISI.{Color.END}")
            else:
                for isi in isi_list:
                    help_pid = (f"Enter T2-MI Packet IDs for Stream {isi}.\nExample: 4096")
                    pid_input = self.ui.ask(f"T2-MI PIDs for ISI {isi}", "4096", help_pid, "🔢", category="pid")
                    pids = [p.strip() for p in pid_input.split(",")]
                    for pid in pids:
                        help_plp = (f"PLP IDs for ISI {isi} PID {pid}.\nExample: 0, 1")
                        plps_input = self.ui.ask(f"PLPs for ISI {isi} PID {pid}", "0", help_plp, "📺")
                        plps = [p.strip() for p in plps_input.split(",")]
                        for plp in plps:
                            self._process_single_service(isi, pid, plp, ns_hex, disp_sat, current_sid)
                            current_sid += 1
            
            self.global_sid_counter = current_sid

        else:
            isi = "-1"
            
            if self.auto_pairs:
                pid_map = {}
                for p, plp in self.auto_pairs:
                    if p not in pid_map: pid_map[p] = []
                    pid_map[p].append(plp)
                
                for pid, plps in pid_map.items():
                    for plp in plps:
                        self._process_single_service(isi, pid, plp, ns_hex, disp_sat, current_sid)
                        current_sid += 1
            else:
                pids = [p.strip() for p in self.pid_input.split(",")]
                for pid in pids:
                    help_plp = (f"PLP IDs for PID {pid}.\nExample: 0, 1, 2")
                    plps_input = self.ui.ask(f"PLPs for PID {pid}", "0", help_plp, "📺")
                    plps = [p.strip() for p in plps_input.split(",")]
                    for plp in plps:
                        self._process_single_service(isi, pid, plp, ns_hex, disp_sat, current_sid)
                        current_sid += 1
            
            self.global_sid_counter = current_sid

        print(f"\n{Color.GREEN}✅ Transponder Processing Complete.{Color.END}")

    def _process_single_service(self, isi, pid, plp, ns_hex, disp_sat, sid_start):
        if isi != "-1":
            tsid_hex = format(int(isi), '04x')
            isi_val = isi
            stream_label = f"ISI{isi}"
        else:
            tsid_hex = self.TSID
            isi_val = "0"
            stream_label = ""

        # VERBOSE LOG
        self.logger.debug(f"PROCESSING SINGLE SERVICE: ISI={isi}, PID={pid}, PLP={plp}, SID={sid_start}")
        self.logger.debug(f"CALCULATED: NS_HEX={ns_hex}, DISP_SAT={disp_sat}, TSID={tsid_hex}")

        tp_key = f"{ns_hex}:{tsid_hex}:{self.ONID}"
        if tp_key not in self.new_tps:
            self.new_tps[tp_key] = (
                f"{ns_hex}:{tsid_hex}:{self.ONID}\n\ts {self.freq}000:{self.sr}000:{POL_MAP[self.pol]}:{self.fec}:" 
                f"{disp_sat}:{self.inv}:{self.sys_type}:{self.mod}:{self.roll}:{self.pilot}:{isi_val}\n/\n"
            )
            self.logger.info(f"Transponder added: {self.freq} {self.pol} ISI:{isi} TSID:{tsid_hex}")

        sid_hex = format(sid_start, 'x').lower()
        onid_hex = format(int(self.ONID, 16), 'x').lower()
        s_ref_core = f"{sid_hex}:{tsid_hex.lower()}:{onid_hex}:{ns_hex}"

        pid_hex = format(int(pid), '04x')
        srv_key = f"{sid_hex}:{ns_hex}:{tsid_hex}:{self.ONID}"
        
        pos_plain = f"{self.sat_pos}{self.sat_dir}"
        pos_disp = f"{self.sat_pos}°{self.sat_dir}"
        
        label_feed = f"{pos_plain}-{self.provider}@PID{pid}PLP{plp} Feed Service"
        if stream_label:
            label_feed += f" ({stream_label})"

        self.new_srvs[srv_key] = (
            f"{srv_key}:1:0\n{label_feed}\np:{self.provider},c:15{pid_hex},f:01\n"
        )
        
        header_parts = [f"━━━ {self.provider} {pos_disp} ━━━ Freq: {self.freq} MHz | PID: {pid} | PLP: {plp}"]
        if isi != "-1":
            header_parts.append(f"| ISI: {isi}")
        header_parts.append("━━━")
        marker_1 = " ".join(header_parts)
        
        self.bouquet.append(f"#SERVICE 1:64:0:0:0:0:0:0:0:0:\n#DESCRIPTION {marker_1}")
        
        marker_2 = f"━━━ {self.provider} {pos_disp} ━━━ FEED SOURCE ━━━"
        self.bouquet.append(f"#SERVICE 1:64:0:0:0:0:0:0:0:0:\n#DESCRIPTION {marker_2}")
        
        feed_desc = f"⚙ {pos_plain}-{self.provider}@PID{pid}PLP{plp}"
        if isi != "-1":
            feed_desc += f" [ISI {isi} FEED]"
        else:
            feed_desc += " [T2-MI FEED]"
            
        self.bouquet.append(f"#SERVICE 1:0:1:{s_ref_core}:0:0:0:\n#DESCRIPTION {feed_desc}")
        
        print(f"  {Color.GREEN}✔ Added Feed Service: {label_feed}{Color.END}")
        self.logger.info(f"Feed Service added: {label_feed}")
        
        self.logger.debug(f"SERVICE REF GENERATED: 1:0:1:{s_ref_core}:0:0:0:")

        var_name = f"f{self.freq}{self.pol.lower()}{self.provider.lower()[:2]}p{pid}plp{plp}"
        if isi != "-1":
            var_name += f"isi{isi}"
        
        label_plp = f"{self.provider} {self.freq}{self.pol} {stream_label} PID{pid} PLP{plp}"
        
        freq_key = f"{self.freq}_{self.pol}_{self.sr}"
        if freq_key not in self.printed_astra_headers:
            astra_header_general = f"-- {self.provider}@{pos_plain} {self.freq}{self.pol}{self.sr} Configs"
            self.astra_blocks.append(astra_header_general)
            self.printed_astra_headers.add(freq_key)
        
        astra_header_specific = f"-- {self.freq} {self.pol} PID {pid} PLP {plp} {stream_label}".strip()
        
        block = (
            f"{astra_header_specific}\n{var_name} = make_t2mi_decap({{\n    name = \"decap_{var_name}\",\n"
            f"    input = \"http://127.0.0.1:8001/1:0:1:{s_ref_core}:0:0:0:\",\n"
            f"    plp = {plp},\n    pnr = 0,\n    pid = {pid},\n}})\n"
            f"make_channel({{\n    name = \"{label_plp}\",\n    input = {{ \"t2mi://{var_name}\" }},\n"
            f"    output = {{ \"http://0.0.0.0:9999/{self.path}/{self.freq}_{self.sat_pos}{self.sat_dir.lower()}_plp{plp}\" }},\n}})\n"
        )
        self.astra_blocks.append(block)
        self.logger.info(f"Astra block generated for {label_plp}")
        self.logger.debug(f"ASTRA OUTPUT PATH: http://0.0.0.0:9999/{self.path}/{self.freq}_{self.sat_pos}{self.sat_dir.lower()}_plp{plp}")

        self._process_sub_channels(plp, tsid_hex.lower(), onid_hex, ns_hex, label_plp, pid, isi)

    def _process_sub_channels(self, plp, tsid_hex, onid_hex, ns_hex, label_parent, pid, isi):
        orbital_folder = f"{self.sat_pos}{self.sat_dir.upper()}"
        csv_dir = os.path.join("channellist", orbital_folder)
        
        filename_base = f"{self.freq}{self.pol}{self.sr}PLP{plp}PID{pid}"
        if isi != "-1":
            filename_base += f"_ISI{isi}"
        filename = f"{filename_base}.csv"
        
        target_path = os.path.join(csv_dir, filename)
        
        print(f"  {Color.CYAN}📂 Searching for channel list: {filename}{Color.END}")
        
        if os.path.isfile(target_path):
            sub_url = f"http://0.0.0.0:9999/{self.path}/{self.freq}_{self.sat_pos}{self.sat_dir.lower()}_plp{plp}".replace(":", "%3a")
            print(f"  {Color.GREEN}   -> Importing channels...{Color.END}")
            self.logger.info(f"Parsing channel file: {filename}")
            try:
                with open(target_path, "r", encoding="utf8") as fh:
                    for csv_line in fh:
                        if "," not in csv_line: continue
                        try:
                            parts = [x.strip() for x in csv_line.strip().split(",")]
                            if len(parts) >= 2:
                                csid, name = parts[0], parts[1]
                                stype = parts[2] if len(parts) > 2 else "1"
                                csid_hex = format(int(csid), 'x').lower()
                                c_ref = f"1:0:{stype}:{csid_hex}:{tsid_hex}:{onid_hex}:{ns_hex}:0:0:0:{sub_url}:{name}"
                                self.bouquet.append(f"#SERVICE {c_ref}\n#DESCRIPTION ▶ {name}")
                                print(f"    {Color.GREEN}✔ Added: {name}{Color.END}")
                                self.logger.info(f"Service imported: {name}")
                                self.logger.debug(f"IMPORTED CHANNEL REF: {c_ref}")
                        except Exception:
                            pass
            except Exception:
                pass
        else:
            print(f"  {Color.YELLOW}   -> No channel list file found for this stream.{Color.END}")
            self.logger.info(f"No channel list file found for stream: {filename}")

    # ==================================================================
    # BATCH FLOW LOGIC
    # ==================================================================
    def run_batch_flow(self):
        csv_files = self.config.load_frequency_csvs()
        if not csv_files:
            print(f"\n{Color.RED}❌ No CSV files found in './frequencies' directory.{Color.END}")
            return

        print(f"\n{Color.CYAN}📂 Frequency Database Browser (Sorted W->E){Color.END}")
        options = [(f, f"📄 {f}") for f in csv_files]
        choice = self.ui.choose_option("Batch Import Source", "Select a CSV file to process entirely:", options, csv_files[0] if csv_files else None)

        if choice is None:
            return
        
        self.logger.info(f"Batch processing file: {choice}")
        self.process_csv_batch(choice)

    def process_csv_batch(self, filename, default_provider=None):
        filepath = os.path.join("frequencies", filename)
        reader = self.config.read_csv(filepath)
        
        self.ui.print_banner(f"BATCH PROCESSING: {filename}", "⚡", Color.CYAN)

        if default_provider is None:
            help_def = ("Provider name used if 'prov' column is missing.\nExample: 'Provider'")
            default_provider = self.ui.ask("Default Provider Name", "Provider", help_def, "🏢", category="provider")
        
        total_rows = len(reader)
        print(f"\n  {Color.GREEN}🚀 Processing {total_rows} transponders...{Color.END}")

        for idx, row in enumerate(reader):
            freq = int(row['Freq'])
            raw_pol = row['Pol'].upper()
            pol = self.POL_CSV_MAP.get(raw_pol, raw_pol)
            sr = int(row['SR'])
            sat_pos = float(row['Pos'])
            sat_dir = row['Dir'].upper()
            
            provider = row.get('prov', row.get('Provider', default_provider))
            path = self._get_relay_path(provider)

            print(f"\n{Color.CYAN}────────────────────────────────────────────────────────────────────────────{Color.END}")
            print(f"{Color.CYAN} [{idx+1}/{total_rows}] Processing: {freq}{pol} {sat_pos}{sat_dir} - {provider}{Color.END}")
            print(f"    {Color.DIM}Deduced Relay Path: /{path}/{Color.END}")
            
            self.logger.info(f"Processing Row {idx+1}: {freq}{pol} {sat_pos}{sat_dir} Provider: {provider}")
            self.logger.debug(f"RAW ROW DATA: {row}")

            self.global_sid_counter = self.process_transponder_batch(
                row, provider, path, self.global_sid_counter
            )
        
        print(f"\n  {Color.GREEN}✅ Batch Complete. Last SID used: {self.global_sid_counter - 1}{Color.END}")

    def process_transponder_batch(self, row, provider, path, start_sid):
        freq = int(row['Freq'])
        raw_pol = row['Pol'].upper()
        pol = self.POL_CSV_MAP.get(raw_pol, raw_pol)
        sr = int(row['SR'])
        sat_pos = float(row['Pos'])
        sat_dir = row['Dir'].upper()
        inv = row['Inv']
        fec = row['FEC']
        sys_type = row['Sys']
        mod = row['Mod']
        roll = row['RO']
        pilot = row['Pilot']

        ns_hex, disp_sat = self._calculate_namespace(freq, sat_pos, sat_dir)

        raw_isi = str(row.get('isi', '-1')).strip()
        is_multistream = raw_isi != '-1' and raw_isi != ''
        isi_list = [i.strip() for i in raw_isi.split(',')] if is_multistream else ['-1']

        raw_pairs = row.get('pids-plps', '')
        flat_pair_list = self._parse_pid_plps(raw_pairs)
        
        if not flat_pair_list:
            pid = row.get('PID', '4096')
            plp = row.get('PLP', '0')
            flat_pair_list.append((pid, plp))

        current_sid = start_sid

        # 2. Logic: Group consecutive pairs with the SAME PID
        # This ensures PID 4097 appearing later in the list gets a new ISI (Case 8.1W)
        # But PID 4098 appearing consecutively shares the ISI (Case 3.1E)
        
        if is_multistream:
            grouped_pairs = []
            
            if flat_pair_list:
                # Initialize first group
                current_pid, current_plp = flat_pair_list[0]
                current_group = [(current_pid, current_plp)]
                
                # Iterate through the rest
                for pid, plp in flat_pair_list[1:]:
                    if pid == current_pid:
                        # Same PID as previous? Add to current group (Shared ISI)
                        current_group.append((pid, plp))
                    else:
                        # Different PID? Save previous group and start new one (New ISI)
                        grouped_pairs.append(current_group)
                        current_pid = pid
                        current_group = [(pid, plp)]
                
                # Append the last group
                grouped_pairs.append(current_group)

            # 3. Map Groups to ISIs
            for idx, group in enumerate(grouped_pairs):
                if idx < len(isi_list):
                    isi = isi_list[idx]
                else:
                    isi = "-1"
                    print(f"    {Color.YELLOW}⚠ Warning: Group index {idx} has no corresponding ISI.{Color.END}")
                
                # Generate entries for all PLPs in this group using the same ISI
                for (pid, plp) in group:
                    self._generate_batch_entry(
                        freq, pol, sr, sat_pos, sat_dir, ns_hex, isi, pid, plp, 
                        provider, path, current_sid, disp_sat, inv, fec, sys_type, mod, roll, pilot
                    )
                    current_sid += 1
        
        else:
            # Non-multistream: Standard grouping by PID
            isi = "-1"
            pid_map = {}
            for p, l in flat_pair_list:
                if p not in pid_map: pid_map[p] = []
                pid_map[p].append(l)
            
            for pid, plps in pid_map.items():
                for plp in plps:
                    self._generate_batch_entry(
                        freq, pol, sr, sat_pos, sat_dir, ns_hex, isi, pid, plp, 
                        provider, path, current_sid, disp_sat, inv, fec, sys_type, mod, roll, pilot
                    )
                    current_sid += 1

        return current_sid

    def _generate_batch_entry(self, freq, pol, sr, sat_pos, sat_dir, ns_hex, isi, pid, plp, provider, path, sid, disp_sat, inv, fec, sys_type, mod, roll, pilot):
        if isi != "-1":
            tsid_hex = format(int(isi), '04x')
            isi_val = isi
            stream_label = f"ISI{isi}"
        else:
            tsid_hex = self.TSID
            isi_val = "0"
            stream_label = ""

        tp_key = f"{ns_hex}:{tsid_hex}:{self.ONID}"
        if tp_key not in self.new_tps:
            self.new_tps[tp_key] = (
                f"{ns_hex}:{tsid_hex}:{self.ONID}\n\ts {freq}000:{sr}000:{POL_MAP[pol]}:{fec}:" 
                f"{disp_sat}:{inv}:{sys_type}:{mod}:{roll}:{pilot}:{isi_val}\n/\n"
            )
            print(f"  {Color.CYAN}📡 Generated Transponder Entry for ISI {isi}{Color.END}" if isi != "-1" else f"  {Color.CYAN}📡 Generated Transponder Entry{Color.END}")
            self.logger.info(f"Generated Transponder: Freq {freq} Pol {pol} ISI {isi}")
            self.logger.debug(f"TP CALCULATED: NS_HEX={ns_hex}, TSID={tsid_hex}, DISP={disp_sat}")

        sid_hex = format(sid, 'x').lower()
        onid_hex = format(int(self.ONID, 16), 'x').lower()
        s_ref_core = f"{sid_hex}:{tsid_hex.lower()}:{onid_hex}:{ns_hex}"
        
        pid_hex = format(int(pid), '04x')
        srv_key = f"{sid_hex}:{ns_hex}:{tsid_hex}:{self.ONID}"
        
        pos_plain = f"{sat_pos}{sat_dir}"
        pos_disp = f"{sat_pos}°{sat_dir}"
        
        label_feed = f"{pos_plain}-{provider}@PID{pid}PLP{plp} Feed Service"
        if stream_label:
            label_feed += f" ({stream_label})"

        self.new_srvs[srv_key] = (
            f"{srv_key}:1:0\n{label_feed}\np:{provider},c:15{pid_hex},f:01\n"
        )
        
        header_parts = [f"━━━ {provider} {pos_disp} ━━━ Freq: {freq} MHz | PID: {pid} | PLP: {plp}"]
        if isi != "-1":
            header_parts.append(f"| ISI: {isi}")
        header_parts.append("━━━")
        marker_1 = " ".join(header_parts)
        
        self.bouquet.append(f"#SERVICE 1:64:0:0:0:0:0:0:0:0:\n#DESCRIPTION {marker_1}")
        
        marker_2 = f"━━━ {provider} {pos_disp} ━━━ FEED SOURCE ━━━"
        self.bouquet.append(f"#SERVICE 1:64:0:0:0:0:0:0:0:0:\n#DESCRIPTION {marker_2}")
        
        feed_desc = f"⚙ {pos_plain}-{provider}@PID{pid}PLP{plp}"
        if isi != "-1":
            feed_desc += f" [ISI {isi} FEED]"
        else:
            feed_desc += " [T2-MI FEED]"
            
        self.bouquet.append(f"#SERVICE 1:0:1:{s_ref_core}:0:0:0:\n#DESCRIPTION {feed_desc}")
        print(f"  {Color.GREEN}✔ Added Feed Service: {label_feed}{Color.END}")
        self.logger.info(f"Feed Service added: {label_feed}")
        self.logger.debug(f"SERVICE REF GENERATED: 1:0:1:{s_ref_core}:0:0:0:")

        var_name = f"f{freq}{pol.lower()}{provider.lower()[:2]}p{pid}plp{plp}"
        if isi != "-1":
            var_name += f"isi{isi}"
        
        label_full = f"{provider} {freq}{pol} {stream_label} PID{pid} PLP{plp}"
        
        freq_key = f"{freq}_{pol}_{sr}"
        if freq_key not in self.printed_astra_headers:
            astra_header_general = f"-- {provider}@{pos_plain} {freq}{pol}{sr} Configs"
            self.astra_blocks.append(astra_header_general)
            self.printed_astra_headers.add(freq_key)

        astra_header_specific = f"-- {freq} {pol} PID {pid} PLP {plp} {stream_label}".strip()
        
        block = (
            f"{astra_header_specific}\n{var_name} = make_t2mi_decap({{\n    name = \"decap_{var_name}\",\n"
            f"    input = \"http://127.0.0.1:8001/1:0:1:{s_ref_core}:0:0:0:\",\n"
            f"    plp = {plp},\n    pnr = 0,\n    pid = {pid},\n}})\n"
            f"make_channel({{\n    name = \"{label_full}\",\n    input = {{ \"t2mi://{var_name}\" }},\n"
            f"    output = {{ \"http://0.0.0.0:9999/{path}/{freq}_{sat_pos}{sat_dir.lower()}_plp{plp}\" }},\n}})\n"
        )
        self.astra_blocks.append(block)
        self.logger.info(f"Generated Astra config for {label_full}")
        self.logger.debug(f"ASTRA OUTPUT PATH: http://0.0.0.0:9999/{path}/{freq}_{sat_pos}{sat_dir.lower()}_plp{plp}")

        orbital_folder = f"{sat_pos}{sat_dir.upper()}"
        csv_dir = os.path.join("channellist", orbital_folder)
        
        filename_base = f"{freq}{pol}{sr}PLP{plp}PID{pid}"
        if isi != "-1":
            filename_base += f"_ISI{isi}"
        filename = f"{filename_base}.csv"

        target_path = os.path.join(csv_dir, filename)
        
        print(f"  {Color.CYAN}📂 Searching for channel list: {filename}{Color.END}")
        
        if os.path.isfile(target_path):
            sub_url = f"http://0.0.0.0:9999/{path}/{freq}_{sat_pos}{sat_dir.lower()}_plp{plp}".replace(":", "%3a")
            print(f"  {Color.GREEN}   -> Importing channels...{Color.END}")
            self.logger.info(f"Parsing channel file: {filename}")
            try:
                with open(target_path, "r", encoding="utf8") as fh:
                    for csv_line in fh:
                        if "," not in csv_line: continue
                        try:
                            parts = [x.strip() for x in csv_line.strip().split(",")]
                            if len(parts) >= 2:
                                csid, name = parts[0], parts[1]
                                stype = parts[2] if len(parts) > 2 else "1"
                                csid_hex = format(int(csid), 'x').lower()
                                c_ref = f"1:0:{stype}:{csid_hex}:{tsid_hex.lower()}:{onid_hex}:{ns_hex}:0:0:0:{sub_url}:{name}"
                                self.bouquet.append(f"#SERVICE {c_ref}\n#DESCRIPTION ▶ {name}")
                                print(f"    {Color.GREEN}✔ Added: {name}{Color.END}")
                                self.logger.info(f"Service imported: {name}")
                                self.logger.debug(f"IMPORTED CHANNEL REF: {c_ref}")
                        except Exception:
                            pass
            except Exception:
                pass
        else:
            print(f"  {Color.YELLOW}   -> No channel list file found for this stream.{Color.END}")
            self.logger.info(f"No channel list file found for stream: {filename}")

    def finalize(self, auto_apply_swap=False):
        self.ui.print_banner("COMPILING ARCHITECTURAL BLUEPRINTS", "💾", Color.GREEN)
        self.logger.info("Starting final compilation...")

        backup_name = self.config.backup_file(self.merge_path)
        self.config.compile_lamedb(self.merge_path, self.new_tps, self.new_srvs)

        swap_applied = False
        # Check if we need to copy the file back to the source
        if os.path.abspath(self.merge_path) != os.path.abspath("workspace/lamedb"):
            if auto_apply_swap:
                # AUTOMATED MODE: Perform swap without asking
                print(f"\n{Color.CYAN}📂 Automated Mode: Updating source database...{Color.END}")
                swap_applied = self.config.perform_live_swap(self.merge_path)
                if swap_applied:
                    self.logger.info(f"Automated swap performed to {self.merge_path}")
            else:
                # MANUAL MODE: Ask the user
                print(f"\n{Color.YELLOW}┌{'─' * 78}┐")
                print(f"│ {Color.BOLD}LIVE DATABASE SWAP{Color.END}{' ' * 60}│")
                print(f"├{'─' * 78}┤")
                print(f"│ Apply these edits to the source file now?{' ' * 34}│")
                b_disp = os.path.basename(backup_name) if backup_name else "N/A"
                print(f"│ {Color.BLUE}ℹ Verified Backup: {b_disp.ljust(53)}{Color.END} │")
                print(f"└{'─' * 78}┘{Color.END}")

                if self.ui.ask("Update source lamedb?", "n", "y = Overwrite | n = Keep local", "🔄").lower() == "y":
                    swap_applied = self.config.perform_live_swap(self.merge_path)
                    if swap_applied:
                        self.logger.info(f"Live database swap performed on {self.merge_path}")

        self.config.sync_bouquet(self.mode, self.bouquet_file, self.bouquet, self.bouquet_name)
        astra_path = self.config.write_astra_conf(self.mode, self.astra_blocks)

        print(f"\n{Color.GREEN}✅ ALL FILES SYNCHRONIZED SUCCESSFULLY.{Color.END}")
        print(f"{Color.CYAN}📂 LOCAL WORKSPACE : ./workspace/lamedb")
        if backup_name:
            print(f"📂 SOURCE BACKUP  : {backup_name}")

        if swap_applied:
            print(f"📂 LIVE DATABASE  : {self.merge_path} {Color.BOLD}(UPDATED){Color.END}")
        else:
            print(f"📂 SOURCE TARGET  : {self.merge_path} {Color.BOLD}(UNTOUCHED){Color.END}")

        print(f"📂 BOUQUET        : ./{self.bouquet_file}")
        print(f"📂 ASTRA          : ./{astra_path}{Color.END}")
        print(f"📂 LOG FILE       : ./workspace/architect_{self.timestamp}.log{Color.END}")
        print(f"\n{Color.GREEN}{Color.BOLD}✨ v15.6 UNIVERSAL ARCHITECT LOCKED!{Color.END}")
        self.logger.info("Session finished successfully.")


if __name__ == "__main__":
    app = SatelliteArchitect()
    app.run()
