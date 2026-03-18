#!/usr/bin/env python3
"""
The Encyclopedia Architect v9.7
A T2-MI Configuration Tool for DVB-S2 Transponders
Refactored with Class-Based Architecture
"""

import os
import sys
import shutil
import time
from typing import Dict, List, Optional, Tuple, Any

# ----------------------------------------------------------------------
# Exceptions
# ----------------------------------------------------------------------


class GoBack(Exception):
    """Custom exception to handle step reversion."""
    pass


# ----------------------------------------------------------------------
# Styling Constants
# ----------------------------------------------------------------------
class Color:
    """ANSI color codes for terminal output."""
    BLUE = '\033[94m'
    CYAN = '\033[96m'
    GREEN = '\033[92m'
    YELLOW = '\033[93m'
    RED = '\033[91m'
    BOLD = '\033[1m'
    END = '\033[0m'

    @classmethod
    def header(cls, text: str) -> str:
        """Apply header styling."""
        return f"{cls.BLUE}{cls.BOLD}{text}{cls.END}"

    @classmethod
    def success(cls, text: str) -> str:
        """Apply success styling."""
        return f"{cls.GREEN}✅ {text}{cls.END}"

    @classmethod
    def warning(cls, text: str) -> str:
        """Apply warning styling."""
        return f"{cls.YELLOW}⚠ {text}{cls.END}"

    @classmethod
    def error(cls, text: str) -> str:
        """Apply error styling."""
        return f"{cls.RED}❌ {text}{cls.END}"


# ----------------------------------------------------------------------
# Dependency Manager
# ----------------------------------------------------------------------
class DependencyManager:
    """Handles module dependencies and environment setup."""

    REQUIRED_MODULES = {
        'prompt_toolkit': {
            'imports': [
                ('prompt_toolkit', 'prompt', 'pt_prompt'),
                ('prompt_toolkit.history', 'FileHistory', 'FileHistory'),
                ('prompt_toolkit.shortcuts', 'radiolist_dialog', 'radiolist_dialog'),
                ('prompt_toolkit.completion', 'PathCompleter', 'PathCompleter'),
            ]
        }
    }

    def __init__(self):
        self._toolkit = None

    def ensure_dependencies(self) -> Tuple[Any, ...]:
        """Ensure all dependencies are available, installing if necessary."""
        try:
            return self._import_toolkit()
        except ImportError:
            self._install_dependencies()
            return self._import_toolkit()

    def _import_toolkit(self) -> Tuple[Any, ...]:
        """Import prompt_toolkit components."""
        from prompt_toolkit import prompt as pt_prompt
        from prompt_toolkit.history import FileHistory
        from prompt_toolkit.shortcuts import radiolist_dialog
        from prompt_toolkit.completion import PathCompleter
        return pt_prompt, FileHistory, radiolist_dialog, PathCompleter

    def _install_dependencies(self) -> None:
        """Install missing dependencies."""
        if "pyenv" not in sys.executable and os.path.exists(
                os.path.expanduser("~/.pyenv")):
            print(f"{Color.YELLOW}⚠ System Python detected. Switching to environment shim...{
                  Color.END}")
            os.execvp("python", ["python"] + sys.argv)

        print(
            f"\n{
                Color.YELLOW}⚠ Module 'prompt_toolkit' not found.{
                Color.END}")
        print(f"{Color.CYAN}⚙ Attempting installation...{Color.END}")

        pip_cmd = [sys.executable, "-m", "pip", "install", "prompt_toolkit"]
        if sys.version_info >= (3, 11):
            pip_cmd.append("--break-system-packages")

        try:
            import subprocess
            subprocess.check_call(
                pip_cmd,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL)
            print(f"{Color.GREEN}✅ Success!{Color.END}\n")
        except Exception:
            print(f"{Color.RED}❌ Failed to initialize environment.{Color.END}")
            print(f"Please run: {
                  Color.BOLD}python -m pip install prompt_toolkit{Color.END}")
            sys.exit(1)


# ----------------------------------------------------------------------
# Input History Manager
# ----------------------------------------------------------------------
class HistoryManager:
    """Manages command history for different input categories."""

    HISTORY_CATEGORIES = {
        "default": ".dx_history_default",
        "paths": ".dx_history_paths",
        "bouquet": ".dx_history_bouquet",
        "freq": ".dx_history_freq",
        "pid": ".dx_history_pid",
        "sid": ".dx_history_sid",
        "provider": ".dx_history_provider"
    }

    def __init__(self, file_history_class):
        self._file_history_class = file_history_class
        self._histories: Dict[str, Any] = {}

    def get_history(self, category: str = "default"):
        """Get or create history for a category."""
        if category not in self._histories:
            filename = self.HISTORY_CATEGORIES.get(
                category, self.HISTORY_CATEGORIES["default"])
            self._histories[category] = self._file_history_class(filename)
        return self._histories[category]


# ----------------------------------------------------------------------
# UI Components
# ----------------------------------------------------------------------
class UIComponents:
    """Handles all user interface rendering and interactions."""

    ASCII_HEADER = r"""
  _______ ___       __  __ ___   _   _ _   _ _   _ __  __  _   _____ _____
 |__   __|__ \     |  \/  |_ _| | | | | | | | | | |  \/  |/ \ |_   _| ____|
    | |     ) |____| |\/| || |  | | | | | | | | | | |\/| / _ \  | | |  _|
    | |    / /|____| |  | || |  | |_| | |_| | |_| | |  |/ ___ \ | | | |___
    |_|   |___|    |_|  |_|___|  \___/ \___/ \___/|_|  /_/   \_\|_| |_____|

               v9.7 - [ THE ENCYCLOPEDIA ARCHITECT ]
    """

    def __init__(
            self,
            pt_prompt,
            radiolist_dialog,
            path_completer,
            history_manager: HistoryManager):
        self._prompt = pt_prompt
        self._radiolist_dialog = radiolist_dialog
        self._path_completer = path_completer
        self._history_manager = history_manager

    @staticmethod
    def clear_screen() -> None:
        """Clear the terminal screen."""
        os.system('cls' if os.name == 'nt' else 'clear')

    def print_header(self) -> None:
        """Display the application header."""
        print(f"{Color.BLUE}{Color.BOLD}" + "=" * 80)
        print(self.ASCII_HEADER)
        print("=" * 80 + f"{Color.END}")

    @staticmethod
    def draw_progress(
            percent: int,
            width: int = 40,
            task: str = "Processing") -> None:
        """Display a progress bar."""
        filled = int(width * percent / 100)
        bar = "█" * filled + "░" * (width - filled)
        sys.stdout.write(f"\r  {Color.CYAN}{task.ljust(20)}: {
                         Color.BOLD}[{bar}]{Color.END} {percent}%")
        sys.stdout.flush()
        time.sleep(0.01)

    def ask(
            self,
            prompt: str,
            default: Optional[str] = None,
            help_text: str = "",
            icon: str = "ℹ",
            allow_back: bool = True,
            category: str = "default") -> str:
        """Prompt user for input with history support."""
        while True:
            self._print_input_box(prompt, default, help_text, icon, allow_back)
            history = self._history_manager.get_history(category)
            val = self._prompt(f"  {prompt}: ", history=history).strip()

            if val.lower() == "back" and allow_back:
                raise GoBack()
            if val == "" and default is not None:
                return default
            if val != "":
                return val
            print(f"  {Color.RED}⚠ ALERT: Value required.{Color.END}")

    def _print_input_box(
            self,
            prompt: str,
            default: Optional[str],
            help_text: str,
            icon: str,
            allow_back: bool) -> None:
        """Print the styled input prompt box."""
        print(
            f"\n{
                Color.YELLOW}┌── {
                Color.BOLD}INPUT FIELD{
                Color.END}{
                    Color.YELLOW} " +
            "─" *
            65 +
            "┐")

        full_help = help_text
        if allow_back:
            full_help += "\n[ Type 'back' to return to the previous question ]"
        full_help += f"\n[ DEFAULT CHOICE: {
            default} ]" if default is not None else "\n[ REQUIRED FIELD ]"

        for line in full_help.strip().split('\n'):
            print(
                f"│ {
                    Color.BLUE}{icon} {
                    line.ljust(74)}{
                    Color.END}{
                    Color.YELLOW} │")
        print(f"└" + "─" * 78 + "┘" + Color.END)

    def choose_option(self,
                      title: str,
                      text: str,
                      options: List[Tuple[str,
                                          str]],
                      default: Optional[str] = None) -> str:
        """Display a radio list dialog for option selection."""
        result = self._radiolist_dialog(
            title=title,
            text=text,
            values=options,
            default=default).run()
        if result is None:
            raise GoBack()
        return result

    def ask_path(self, prompt: str, category: str = "paths") -> str:
        """Prompt for path input with autocomplete."""
        history = self._history_manager.get_history(category)
        return self._prompt(
            f"  {prompt}: ",
            completer=self._path_completer,
            history=history).strip()

    @staticmethod
    def print_section_header(title: str, char: str = "═") -> None:
        """Print a styled section header."""
        print(f"\n{Color.CYAN}╔" + char * 78 + "╗")
        print(f"║ {Color.BOLD}{title.center(88)}{Color.END}{Color.CYAN}║")
        print(f"╚" + char * 78 + "╝" + Color.END)


# ----------------------------------------------------------------------
# File Manager
# ----------------------------------------------------------------------
class FileManager:
    """Handles file system operations and browsing."""

    def __init__(self, ui: UIComponents):
        self._ui = ui

    def browse(self, start_path: str = ".") -> str:
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

                selection = self._ui._radiolist_dialog(
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

    @staticmethod
    def backup_file(filepath: str) -> Optional[str]:
        """Create a timestamped backup of a file."""
        if not os.path.isfile(filepath):
            return None

        try:
            timestamp = time.strftime("%Y%m%d_%H%M%S")
            backup_name = f"{filepath}_{timestamp}.bak"
            shutil.copy2(filepath, backup_name)
            return backup_name
        except Exception:
            return None

    @staticmethod
    def read_lines(filepath: str) -> List[str]:
        """Read file lines, returning default structure if not exists."""
        if os.path.isfile(filepath):
            with open(filepath, "r", encoding="utf-8", errors="ignore") as f:
                return [line.rstrip() for line in f.readlines()]
        return ["eDVB services /4/", "transponders", "end", "services", "end"]

    @staticmethod
    def write_lines(filepath: str, lines: List[str]) -> None:
        """Write lines to a file."""
        with open(filepath, "w", encoding="utf-8", newline='\n') as f:
            f.write("\n".join(lines) + "\n")


# ----------------------------------------------------------------------
# Data Models
# ----------------------------------------------------------------------
class TransponderConfig:
    """Configuration data for a DVB transponder."""

    def __init__(self):
        self.frequency: int = 0
        self.symbol_rate: int = 0
        self.polarization: str = "L"
        self.sat_position: float = 0.0
        self.sat_direction: str = "W"
        self.inversion: str = "2"
        self.fec: str = "9"
        self.system: str = "1"
        self.modulation: str = "2"
        self.rolloff: str = "0"
        self.pilot: str = "2"
        self.service_id: int = 0
        self.provider: str = ""
        self.pids: List[str] = []
        self.plps: Dict[str, List[str]] = {}
        self.astra_path: str = ""

    @property
    def pol_digit(self) -> str:
        """Get polarization digit code."""
        return {
            "H": "0",
            "V": "1",
            "L": "2",
            "R": "3"}.get(
            self.polarization,
            "0")

    @property
    def raw_sat(self) -> int:
        """Get raw satellite position."""
        return int(self.sat_position * 10)

    @property
    def ns_sat(self) -> int:
        """Get north/south satellite position."""
        return (3600 - self.raw_sat) if self.sat_direction == "W" else self.raw_sat

    @property
    def disp_sat(self) -> int:
        """Get display satellite position."""
        return -self.raw_sat if self.sat_direction == "W" else self.raw_sat

    @property
    def ns_hex(self) -> str:
        """Get hex representation of namespace."""
        return format((self.ns_sat << 16) | self.frequency, '08x').lower()


class DatabaseEntry:
    """Represents a transponder or service database entry."""

    def __init__(self, key: str, content: str):
        self.key = key
        self.content = content


# ----------------------------------------------------------------------
# Configuration Generator
# ----------------------------------------------------------------------
class ConfigGenerator:
    """Generates configuration output for various formats."""

    ONID = "0001"
    TSID = "0001"

    def __init__(self, transponder: TransponderConfig):
        self._config = transponder
        self.transponders: Dict[str, str] = {}
        self.services: Dict[str, str] = {}
        self.bouquet_entries: List[str] = []
        self.astra_blocks: List[str] = []

    @property
    def sid_hex(self) -> str:
        """Service ID in hex format."""
        return format(self._config.service_id, '04x').lower()

    @property
    def sid_no_lead(self) -> str:
        """Service ID without leading zeros."""
        return format(self._config.service_id, 'x').lower()

    @property
    def tsid_no_lead(self) -> str:
        """TSID without leading zeros."""
        return format(int(self.TSID, 16), 'x').lower()

    @property
    def onid_no_lead(self) -> str:
        """ONID without leading zeros."""
        return format(int(self.ONID, 16), 'x').lower()

    @property
    def tp_key(self) -> str:
        """Transponder database key."""
        return f"{self._config.ns_hex}:{self.TSID}:{self.ONID}"

    def generate_transponder_entry(self) -> str:
        """Generate transponder database entry."""
        return (
            f"{
                self.tp_key}\n" f"\ts {
                self._config.frequency *
                1000}:{
                self._config.symbol_rate *
                1000}:" f"{
                    self._config.pol_digit}:{
                        self._config.fec}:{
                            self._config.disp_sat}:" f"{
                                self._config.inversion}:0:{
                                    self._config.system}:" f"{
                                        self._config.modulation}:{
                                            self._config.rolloff}:{
                                                self._config.pilot}\n/\n")

    def generate_service_entry(self, pid: str) -> str:
        """Generate service database entry."""
        srv_key = f"{
            self.sid_hex}:{
            self._config.ns_hex}:{
            self.TSID}:{
                self.ONID}"
        return (
            f"{srv_key}:1:0\n"
            f"{self._config.provider} PID{pid} FEED\n"
            f"p:{self._config.provider},c:15{format(int(pid), '04x')},f:01\n"
        )

    def generate_service_ref(self, pid: str) -> str:
        """Generate service reference string."""
        return f"{
            self.sid_no_lead}:{
            self.tsid_no_lead}:{
            self.onid_no_lead}:{
                self._config.ns_hex}"

    def generate_astra_block(self, pid: str, plp: str) -> str:
        """Generate Astra configuration block."""
        s_ref = self.generate_service_ref(pid)
        var_name = f"f{
            self._config.frequency}{
            self._config.polarization.lower()}" f"{
            self._config.provider.lower()[
                :2]}p{pid}plp{plp}"
        label = f"{
            self._config.provider} {
            self._config.frequency}{
            self._config.polarization} PID{pid} PLP{plp}"
        stream_url = f"http://0.0.0.0:9999/{self._config.astra_path}/" \
            f"{self._config.frequency}_{self._config.sat_position}" \
            f"{self._config.sat_direction.lower()}_plp{plp}"

        return (
            f"-- {label}\n"
            f"{var_name} = make_t2mi_decap({{\n"
            f'    name = "decap_{var_name}",\n'
            f'    input = "http://127.0.0.1:8001/1:0:1:{s_ref}:0:0:0:",\n'
            f"    plp = {plp},\n    pnr = 0,\n    pid = {pid},\n}})\n"
            f"make_channel({{\n"
            f'    name = "{label}",\n'
            f'    input = {{ "t2mi://decap_{var_name}", }},\n'
            f'    output = {{ "{stream_url}", }},\n}})\n'
        )

    def build_all(self) -> None:
        """Build all configuration entries."""
        # Transponder entry
        self.transponders[self.tp_key] = self.generate_transponder_entry()

        # Service and bouquet entries for each PID
        for pid in self._config.pids:
            s_ref = self.generate_service_ref(pid)
            srv_key = f"{
                self.sid_hex}:{
                self._config.ns_hex}:{
                self.TSID}:{
                self.ONID}"

            self.services[srv_key] = self.generate_service_entry(pid)
            self.bouquet_entries.append(
                f"#SERVICE 1:0:1:{s_ref}:0:0:0:\n"
                f"#DESCRIPTION {self._config.provider} PID{pid} FEED"
            )


# ----------------------------------------------------------------------
# Database Manager
# ----------------------------------------------------------------------
class DatabaseManager:
    """Handles lamedb database operations."""

    def __init__(self, file_manager: FileManager):
        self._file_manager = file_manager
        self.lines: List[str] = []

    def load(self, filepath: str) -> None:
        """Load database from file."""
        self.lines = self._file_manager.read_lines(filepath)

    def merge_transponders(self, transponders: Dict[str, str]) -> None:
        """Merge transponder entries into database."""
        try:
            tp_idx = self.lines.index("transponders")
            for key, block in transponders.items():
                # Remove existing entry
                for idx, line in enumerate(self.lines):
                    if line.startswith(key):
                        del self.lines[idx:idx + 3]
                        break
                # Insert new entry
                self.lines.insert(tp_idx + 1, block.strip())
        except ValueError:
            pass

    def merge_services(self, services: Dict[str, str]) -> None:
        """Merge service entries into database."""
        try:
            srv_idx = self.lines.index("services")
            for key, block in services.items():
                # Remove existing entry
                for idx, line in enumerate(self.lines):
                    if line.startswith(key):
                        del self.lines[idx:idx + 3]
                        break
                # Insert new entry
                self.lines.insert(srv_idx + 1, block.strip())
        except ValueError:
            pass

    def save(self, filepath: str) -> None:
        """Save database to file."""
        self._file_manager.write_lines(filepath, self.lines)


# ----------------------------------------------------------------------
# Channel List Processor
# ----------------------------------------------------------------------
class ChannelListProcessor:
    """Processes CSV channel lists and generates bouquet entries."""

    def __init__(
            self,
            config: TransponderConfig,
            generator: ConfigGenerator,
            ui: UIComponents):
        self._config = config
        self._generator = generator
        self._ui = ui

    def process_plp(self, pid: str, plp: str, bouquet_entries: List[str],
                    astra_blocks: List[str]) -> None:
        """Process a single PLP configuration."""
        s_ref = self._generator.generate_service_ref(pid)
        var_name = (f"f{self._config.frequency}{self._config.polarization.lower()}"
                    f"{self._config.provider.lower()[:2]}p{pid}plp{plp}")
        label = f"{
            self._config.provider} {
            self._config.frequency}{
            self._config.polarization} PID{pid} PLP{plp}"

        # Add separator
        bouquet_entries.append(
            f"#SERVICE 1:64:0:0:0:0:0:0:0:0:\n#DESCRIPTION --- {label} ---")

        # Add Astra block
        astra_blocks.append(self._generator.generate_astra_block(pid, plp))

        # Process CSV channel list
        self._process_csv_channels(pid, plp, s_ref, bouquet_entries)

    def _process_csv_channels(self, pid: str, plp: str, s_ref: str,
                              bouquet_entries: List[str]) -> None:
        """Process CSV file for channel mappings."""
        orbital_folder = f"{
            self._config.sat_position}{
            self._config.sat_direction.upper()}"
        csv_dir = os.path.join("channellist", orbital_folder)

        suggestions = sorted(
            [f for f in os.listdir(csv_dir) if f.lower().endswith('.csv')]
        ) if os.path.isdir(csv_dir) else []

        self._print_csv_options(pid, plp, suggestions)

        ch_choice = self._ui.ask_path(
            f"Select file [#] or path for {orbital_folder} PLP {plp}")
        if ch_choice.lower() == "back":
            raise GoBack()

        ch_file = self._resolve_csv_path(csv_dir, suggestions, ch_choice)

        if ch_file and os.path.isfile(ch_file):
            self._import_csv_channels(ch_file, plp, s_ref, bouquet_entries)

    def _print_csv_options(
            self,
            pid: str,
            plp: str,
            suggestions: List[str]) -> None:
        """Print CSV file selection options."""
        print(
            f"\n{
                Color.YELLOW}┌── {
                Color.BOLD}SUB-CHANNEL MAPPING: PID {pid} PLP {plp}{
                Color.END}{
                    Color.YELLOW} " +
            "─" *
            40 +
            "┐")
        for idx, fname in enumerate(suggestions, 1):
            print(
                f"│ {
                    Color.CYAN} [{idx}] {
                    fname.ljust(72)}{
                    Color.END}{
                    Color.YELLOW} │")
        print(f"└" + "─" * 78 + "┘" + Color.END)

    def _resolve_csv_path(
            self,
            csv_dir: str,
            suggestions: List[str],
            choice: str) -> Optional[str]:
        """Resolve the CSV file path from user choice."""
        if choice.isdigit() and 1 <= int(choice) <= len(suggestions):
            return os.path.join(csv_dir, suggestions[int(choice) - 1])
        return choice if choice else None

    def _import_csv_channels(self, csv_file: str, plp: str, s_ref: str,
                             bouquet_entries: List[str]) -> None:
        """Import channels from CSV file."""
        sub_url = (
            f"http://0.0.0.0:9999/{self._config.astra_path}/"
            f"{self._config.frequency}_{self._config.sat_position}"
            f"{self._config.sat_direction.lower()}_plp{plp}"
        ).replace(":", "%3a")

        with open(csv_file, "r", encoding="utf8") as f:
            for line in f:
                if "," not in line:
                    continue
                try:
                    csid, name, stype = [x.strip() for x in line.split(",")]
                    c_ref = (
                        f"1:0:{stype}:{
                            format(
                                int(csid),
                                'x').lower()}:" f"{
                            self._generator.tsid_no_lead}:{
                            self._generator.onid_no_lead}:" f"{
                            self._config.ns_hex}:0:0:0:{sub_url}:{name}")
                    bouquet_entries.append(
                        f"#SERVICE {c_ref}\n#DESCRIPTION {name}")
                    print(f"    {Color.GREEN}✔ Added: {name}{Color.END}")
                except ValueError:
                    continue


# ----------------------------------------------------------------------
# Main Application
# ----------------------------------------------------------------------
class EncyclopediaArchitect:
    """Main application controller."""

    def __init__(self):
        # Initialize dependencies
        dep_manager = DependencyManager()
        pt_prompt, FileHistory, radiolist_dialog, PathCompleter = dep_manager.ensure_dependencies()

        # Initialize managers
        self._history_manager = HistoryManager(FileHistory)
        self._ui = UIComponents(
            pt_prompt,
            radiolist_dialog,
            PathCompleter(),
            self._history_manager)
        self._file_manager = FileManager(self._ui)
        self._db_manager = DatabaseManager(self._file_manager)

        # Application state
        self._step = 1
        self._config = TransponderConfig()
        self._generator: Optional[ConfigGenerator] = None
        self._channel_processor: Optional[ChannelListProcessor] = None

        # Output data
        self._all_transponders: Dict[str, str] = {}
        self._all_services: Dict[str, str] = {}
        self._bouquet_entries: List[str] = []
        self._astra_blocks: List[str] = []
        self._bouquet_name = "T2MI DX"
        self._bouquet_file = ""
        self._merge_path = "./lamedb"
        self._backup_name: Optional[str] = None

    def run(self) -> None:
        """Main application entry point."""
        try:
            self._ui.clear_screen()
            self._ui.print_header()

            self._run_wizard()
            self._finalize()

        except KeyboardInterrupt:
            self._exit_gracefully()

    def _run_wizard(self) -> None:
        """Run the configuration wizard."""
        while True:
            try:
                step_handlers = {
                    1: self._step_cleanup,
                    2: self._step_source_selection,
                    3: self._step_bouquet_name,
                    4: self._step_frequency,
                    5: self._step_symbol_rate,
                    6: self._step_polarization,
                    7: self._step_satellite_position,
                    8: self._step_satellite_direction,
                    9: self._step_inversion,
                    10: self._step_fec,
                    11: self._step_system,
                    12: self._step_modulation,
                    13: self._step_rolloff,
                    14: self._step_pilot,
                    15: self._step_service_id,
                    16: self._step_provider,
                    17: self._step_pids,
                    18: self._step_astra_path_and_finalize,
                }

                handler = step_handlers.get(self._step)
                if handler:
                    handler()
                else:
                    break

            except GoBack:
                self._step = max(1, self._step - 1)
                self._ui.clear_screen()
                self._ui.print_header()
                print(
                    f"\n{
                        Color.RED}↩ REVERTING TO PREVIOUS STEP...{
                        Color.END}")

    # --- Step Handlers ---

    def _step_cleanup(self) -> None:
        """Handle workspace cleanup step."""
        cleanup = self._ui.ask(
            "Clean workspace?",
            "n",
            "Wipe existing files to avoid conflicts.\ny = Yes (Delete lamedb/astra/bouquets) | n = No (Safe Merge).",
            "🧹",
            allow_back=False)
        if cleanup.lower() == 'y':
            for i in range(0, 101, 10):
                self._ui.draw_progress(i, task="Wiping Data")
            for f in os.listdir('.'):
                if (f.startswith('userbouquet.')
                        and f.endswith('.tv')) or f == 'lamedb':
                    try:
                        os.remove(f)
                    except OSError:
                        pass
            if os.path.exists('astra'):
                shutil.rmtree('astra')
        self._step = 2

    def _step_source_selection(self) -> None:
        """Handle database source selection."""
        print(
            f"\n{
                Color.YELLOW}┌── {
                Color.BOLD}DATABASE SOURCE{
                Color.END}{
                    Color.YELLOW} " +
            "─" *
            61 +
            "┐")
        print(f"│ {Color.BLUE}📂 Opening File Manager...{
              ' ' * 47}{Color.END}{Color.YELLOW}│")
        print(f"│ {Color.BLUE}ℹ Cancelling will automatically select local ./lamedb.{
              ' ' * 23}{Color.END}{Color.YELLOW}│")
        print(f"└" + "─" * 78 + "┘" + Color.END)

        self._merge_path = self._file_manager.browse(".")
        print(
            f"  {
                Color.GREEN}✅ Target Active: {
                Color.BOLD}{
                self._merge_path}{
                    Color.END}")
        self._step = 3

    def _step_bouquet_name(self) -> None:
        """Handle bouquet naming."""
        self._bouquet_name = self._ui.ask(
            "Bouquet name", "T2MI DX",
            "The name of the favorites group in your channel list.", "🏷️"
        )
        self._bouquet_file = f"userbouquet.{
            self._bouquet_name.lower().replace(' ', '_')}.tv"
        self._step = 4

    def _step_frequency(self) -> None:
        """Handle frequency input."""
        self._ui.print_section_header("DETAILED PARAMETER CONFIGURATION")
        self._config.frequency = int(self._ui.ask(
            "Frequency MHz", "4014",
            "Downlink Frequency (e.g., 4014, 3665, 11495).", "📡"
        ))
        self._step = 5

    def _step_symbol_rate(self) -> None:
        """Handle symbol rate input."""
        self._config.symbol_rate = int(self._ui.ask(
            "Symbol Rate", "15284",
            "Transponder Symbol Rate (e.g., 15284, 30000, 7325).", "📶"
        ))
        self._step = 6

    def _step_polarization(self) -> None:
        """Handle polarization selection."""
        self._config.polarization = self._ui.choose_option(
            "Polarization", "Select antenna polarization:",
            [("H", "Horizontal"), ("V", "Vertical"), ("L", "Left Circular"), ("R", "Right Circular")],
            "L"
        )
        self._step = 7

    def _step_satellite_position(self) -> None:
        """Handle satellite position input."""
        self._config.sat_position = float(self._ui.ask(
            "Satellite position", "18.1",
            "Orbital position (e.g., 18.1, 40.0, 4.8).", "🌍"
        ))
        self._step = 8

    def _step_satellite_direction(self) -> None:
        """Handle satellite direction selection."""
        self._config.sat_direction = self._ui.ask(
            "Direction (E/W)", "W",
            "Orbital direction:\nE = East | W = West.", "🧭"
        ).upper()
        self._step = 9

    def _step_inversion(self) -> None:
        """Handle inversion setting."""
        self._config.inversion = self._ui.ask(
            "Inversion", "2",
            "Spectral Inversion settings:\n0 = Off | 1 = On | 2 = Auto.", "🛠️"
        )
        self._step = 10

    def _step_fec(self) -> None:
        """Handle FEC selection."""
        self._config.fec = self._ui.choose_option(
            "FEC", "Forward Error Correction:",
            [("1", "1/2"), ("2", "2/3"), ("3", "3/4"), ("4", "5/6"),
             ("5", "7/8"), ("6", "8/9"), ("7", "3/5"), ("8", "4/5"), ("9", "Auto")],
            "9"
        )
        self._step = 11

    def _step_system(self) -> None:
        """Handle system type selection."""
        self._config.system = self._ui.ask(
            "System",
            "1",
            "DVB Delivery System:\n0 = DVB-S (Legacy) | 1 = DVB-S2 (Modern,required for T2-MI).",
            "🛠️")
        self._step = 12

    def _step_modulation(self) -> None:
        """Handle modulation selection."""
        self._config.modulation = self._ui.ask(
            "Modulation", "2",
            "Constellation: 1=QPSK | 2=8PSK | 3=16APSK | 4=32APSK.", "🛠️"
        )
        self._step = 13

    def _step_rolloff(self) -> None:
        """Handle rolloff selection."""
        self._config.rolloff = self._ui.ask(
            "RollOff", "0",
            "Pulse Shaping Factor: 0=0.35 | 1=0.25 | 2=0.20.", "🛠️"
        )
        self._step = 14

    def _step_pilot(self) -> None:
        """Handle pilot selection."""
        self._config.pilot = self._ui.ask(
            "Pilot", "2",
            "DVB-S2 Pilot Tones: 0=Off | 1=On | 2=Auto.", "🛠️"
        )
        self._step = 15

    def _step_service_id(self) -> None:
        """Handle service ID input."""
        self._generator = ConfigGenerator(self._config)
        self._config.service_id = int(self._ui.ask(
            "Feed SID", "800",
            "Service ID (Decimal) for the raw T2-MI PID carrier.", "🆔"
        ))
        self._step = 16

    def _step_provider(self) -> None:
        """Handle provider name input."""
        self._config.provider = self._ui.ask(
            "Provider name", "ORTM",
            "Provider label for service metadata.", "🏢"
        )
        self._step = 17

    def _step_pids(self) -> None:
        """Handle PID input."""
        pid_input = self._ui.ask(
            "T2-MI PIDs",
            "4096",
            "PIDs carrying T2-MI data (e.g., 4096,4097).\n You can enter Multiple PIDs (Comma seperated)",
            "🔢")
        self._config.pids = [p.strip() for p in pid_input.split(",")]
        self._step = 18

    def _step_astra_path_and_finalize(self) -> None:
        """Handle astra path and process all PIDs/PLPs."""
        self._config.astra_path = self._ui.ask(
            "Astra path", "ortm",
            "URL segment for Astra-SM.", "🔗"
        )

        self._channel_processor = ChannelListProcessor(
            self._config, self._generator, self._ui
        )

        # Build base entries
        self._generator.build_all()

        # Process each PID and PLP
        for pid in self._config.pids:
            plps_input = self._ui.ask(
                f"PLPs for PID {pid}", "0",
                "Physical Layer Pipe IDs.", "📺"
            )
            plps = [pl.strip() for pl in plps_input.split(",")]

            for plp in plps:
                self._channel_processor.process_plp(
                    pid, plp, self._bouquet_entries, self._astra_blocks
                )

        # Check for another transponder
        if self._ui.ask(
            "Add another transponder?", "n",
            "y = Add transponder | n = Finalize generation.", "❓"
        ) == "y":
            # Save current transponder data
            self._all_transponders.update(self._generator.transponders)
            self._all_services.update(self._generator.services)
            # Reset for new transponder
            self._config = TransponderConfig()
            self._generator = ConfigGenerator(self._config)
            self._step = 4
        else:
            # Merge all transponder data
            self._all_transponders.update(self._generator.transponders)
            self._all_services.update(self._generator.services)
            # Exit wizard
            self._step = 19

    def _finalize(self) -> None:
        """Finalize configuration generation."""
        # Progress animation
        for i in range(0, 101, 20):
            self._ui.draw_progress(i, task="Syncing Database")

        # Create backup
        self._backup_name = self._file_manager.backup_file(self._merge_path)
        if self._backup_name:
            print(
                f"\n  {
                    Color.GREEN}💾 BACKUP CREATED: {
                    self._backup_name}{
                    Color.END}")

        # Load and merge database
        self._db_manager.load(self._merge_path)
        self._db_manager.merge_transponders(self._all_transponders)
        self._db_manager.merge_services(self._all_services)
        self._db_manager.save("lamedb")

        # Handle live swap
        swap_applied = self._handle_live_swap()

        # Save bouquet and astra config
        self._save_outputs()

        # Display completion
        self._display_completion(swap_applied)

    def _handle_live_swap(self) -> bool:
        """Handle optional live database swap."""
        if os.path.abspath(self._merge_path) == os.path.abspath("./lamedb"):
            return False

        print(
            f"\n{
                Color.YELLOW}┌── {
                Color.BOLD}LIVE DATABASE SWAP{
                Color.END}{
                    Color.YELLOW} " +
            "─" *
            57 +
            "┐")
        print(f"│ {Color.CYAN}Apply these edits to the source file now?{
              ' ' * 36}{Color.END}{Color.YELLOW}│")

        b_disp = os.path.basename(
            self._backup_name) if self._backup_name else "N/A"
        print(
            f"│ {
                Color.BLUE}ℹ Verified Backup: {
                b_disp.ljust(53)}{
                Color.END}{
                    Color.YELLOW} │")
        print(f"└" + "─" * 78 + "┘" + Color.END)

        swap_choice = self._ui.ask(
            "Update source lamedb?", "n",
            "y = Overwrite original file | n = Keep edits locally", "🔄"
        )

        if swap_choice.lower() == "y":
            try:
                shutil.copy2("lamedb", self._merge_path)
                print(
                    f"  {
                        Color.GREEN}✨ SUCCESS: {
                        self._merge_path} updated.{
                        Color.END}")
                return True
            except Exception as e:
                print(f"  {Color.RED}✖ SWAP FAILED: {str(e)}{Color.END}")
        return False

    def _save_outputs(self) -> None:
        """Save bouquet and astra configuration files."""
        # Save bouquet
        with open(self._bouquet_file, "w") as f:
            f.write(
                f"#NAME {
                    self._bouquet_name}\n" +
                "\n".join(
                    self._bouquet_entries) +
                "\n")

        # Save astra config
        if not os.path.exists("astra"):
            os.makedirs("astra")
        with open("astra/astra.conf", "w") as f:
            f.write(
                "-- [ ARCHITECT GENERATED CONFIG ] --\n" +
                "\n".join(
                    self._astra_blocks))

    def _display_completion(self, swap_applied: bool) -> None:
        """Display completion summary."""
        self._ui.draw_progress(100, task="Architecture Locked")
        print(
            f"\n\n{
                Color.GREEN}{
                Color.BOLD}✅ v9.7 ENCYCLOPEDIA ARCHITECT SUCCESSFUL!{
                Color.END}")
        print(f"{Color.CYAN}📂 LOCAL WORKSPACE : ./lamedb")

        if self._backup_name:
            print(f"📂 SOURCE BACKUP   : {self._backup_name}")

        if swap_applied:
            print(
                f"📂 LIVE DATABASE   : {
                    self._merge_path} {
                    Color.BOLD}(UPDATED){
                    Color.END}")
        else:
            print(
                f"📂 SOURCE TARGET   : {
                    self._merge_path} {
                    Color.BOLD}(UNTOUCHED){
                    Color.END}")

        print(f"📂 BOUQUET         : ./{self._bouquet_file}")
        print(f"📂 ASTRA           : ./astra/astra.conf{Color.END}\n")

    @staticmethod
    def _exit_gracefully() -> None:
        """Handle graceful exit on interrupt."""
        print(
            f"\n\n{Color.RED}⚠ Process interrupted by user (Ctrl+C).{Color.END}")
        print(f"{Color.YELLOW}Exiting The Encyclopedia Architect...{Color.END}")
        sys.exit(0)


# ----------------------------------------------------------------------
# Entry Point
# ----------------------------------------------------------------------
def main():
    """Application entry point."""
    app = EncyclopediaArchitect()
    app.run()


if __name__ == "__main__":
    main()
