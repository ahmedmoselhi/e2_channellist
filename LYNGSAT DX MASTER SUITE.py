#!/usr/bin/env python3
"""
LyngSat DX Master Suite - Version 17.0
Refactored with OOP Architecture and Auto-Adjusting UI Borders
"""

import os
import sys
import re
import csv
import time
import signal
from datetime import datetime
from typing import Optional, Dict, List, Tuple, Any

# Platform-specific input handling
if sys.platform == 'win32':
    import msvcrt
else:
    import select


# ==============================================================================
# [ 🎨 COLOR THEMES ]
# ==============================================================================
class ColorTheme:
    """ANSI color codes for terminal output."""
    BASE = "\033[38;5;250m"
    GOLD = "\033[38;5;220m"
    SKY = "\033[38;5;117m"
    LIME = "\033[38;5;121m"
    CRIMSON = "\033[38;5;196m"
    VIOLET = "\033[38;5;141m"
    TEAL = "\033[38;5;51m"
    BOLD = "\033[1m"
    ENDC = "\033[0m"


# ==============================================================================
# [ 🖼️ UI RENDERER - AUTO-ADJUSTING BORDERS ]
# ==============================================================================
class UIRenderer:
    """
    Handles all UI rendering with automatic border width calculation.
    Strips ANSI codes for accurate width measurement.
    """

    ANSI_ESCAPE = re.compile(r'\x1B(?:[@-Z\\-_]|\[[0-?]*[ -/]*[@-~])')

    # Default terminal width (can be overridden)
    DEFAULT_WIDTH = 80

    def __init__(self, color: ColorTheme):
        self.color = color
        self.terminal_width = self._get_terminal_width()

    def _get_terminal_width(self) -> int:
        """Get terminal width or use default."""
        try:
            return os.get_terminal_size().columns
        except Exception:
            return self.DEFAULT_WIDTH

    @staticmethod
    def strip_ansi(text: str) -> str:
        """Remove ANSI escape codes from text for accurate width calculation."""
        return UIRenderer.ANSI_ESCAPE.sub('', text)

    @staticmethod
    def visible_width(text: str) -> int:
        """Calculate the visible width of text (excluding ANSI codes)."""
        return len(UIRenderer.strip_ansi(text))

    def _pad_to_width(
            self,
            text: str,
            target_width: int,
            align: str = 'left') -> str:
        """
        Pad text to target width, accounting for ANSI codes.
        Alignment: 'left', 'right', 'center'
        """
        visible_len = self.visible_width(text)
        padding_needed = target_width - visible_len

        if padding_needed <= 0:
            return text

        if align == 'left':
            return text + ' ' * padding_needed
        elif align == 'right':
            return ' ' * padding_needed + text
        else:  # center
            left_pad = padding_needed // 2
            right_pad = padding_needed - left_pad
            return ' ' * left_pad + text + ' ' * right_pad

    # --------------------------------------------------------------------------
    # [ BANNER RENDERING ]
    # --------------------------------------------------------------------------

    def render_banner(self, title: str, version: str,
                      width: int = None) -> List[str]:
        """
        Render a banner with auto-adjusted borders.
        Returns list of lines to print.
        """
        if width is None:
            width = self.terminal_width

        inner_width = width - 2  # Account for border characters

        lines = []
        lines.append(
            self.color.GOLD +
            "█" +
            "▀" *
            inner_width +
            "█" +
            self.color.ENDC)

        # Title line with version on right
        title_text = f"  {title}"
        version_text = f"{version}  "
        title_visible = self.visible_width(title_text)
        version_visible = self.visible_width(version_text)
        gap = inner_width - title_visible - version_visible

        content_line = (
            f"{self.color.GOLD}█{self.color.ENDC}"
            f"{self.color.SKY}{self.color.BOLD}{title_text}{self.color.ENDC}"
            f"{' ' * gap}"
            f"{self.color.GOLD}{version_text}█{self.color.ENDC}"
        )
        lines.append(content_line)
        lines.append(
            self.color.GOLD +
            "█" +
            "▄" *
            inner_width +
            "█" +
            self.color.ENDC)

        return lines

    def print_banner(self, title: str = "🛰️  LYNGSAT DX MASTER SUITE",
                     version: str = "VER 17.0 | AUTO-UI") -> None:
        """Print the application banner."""
        for line in self.render_banner(title, version):
            print(line)

    # --------------------------------------------------------------------------
    # [ BOX RENDERING ]
    # --------------------------------------------------------------------------

    def render_box(self, lines: List[str], width: int = None,
                   border_color: str = None) -> List[str]:
        """
        Render a box with automatic width adjustment.
        Width is determined by the longest line or terminal width.
        """
        if border_color is None:
            border_color = self.color.BASE

        # Calculate required width based on content
        max_content_width = max(self.visible_width(line)
                                for line in lines) if lines else 0
        if width is None:
            width = min(max(max_content_width + 4, 60), self.terminal_width)

        inner_width = width - 2
        result = []

        # Top border
        result.append(f"{border_color}┌{'─' * inner_width}┐{self.color.ENDC}")

        # Content lines
        for line in lines:
            padded = self._pad_to_width(f"  {line}", inner_width)
            result.append(
                f"{border_color}│{self.color.ENDC}{padded}{border_color}│{self.color.ENDC}")

        # Empty line for spacing if needed
        result.append(f"{border_color}│{' ' * inner_width}│{self.color.ENDC}")

        # Bottom border
        result.append(f"{border_color}└{'─' * inner_width}┘{self.color.ENDC}")

        return result

    def print_instructions_box(
            self,
            instructions: List[str],
            notes: List[str]) -> None:
        """Print instructions in a formatted box."""
        c = self.color
        width = self.terminal_width
        inner_width = width - 2

        print(f"{c.BASE}┌{'─' * inner_width}┐{c.ENDC}")

        # Title
        title = f"  {c.BOLD}{c.SKY}RECURSIVE DEEP-SCAN SYSTEM v17.0{c.ENDC}"
        print(f"{c.BASE}│{self._pad_to_width( title, inner_width)}{c.BASE}│{c.ENDC}")
        print(f"{c.BASE}│{' ' * inner_width}│{c.ENDC}")

        # Instructions header
        instr_header = f"  {c.LIME}Instructions:{c.ENDC}"
        print(f"{c.BASE}│{self._pad_to_width( instr_header, inner_width)}{c.BASE}│{c.ENDC}")

        # Instructions
        for instr in instructions:
            line = f"  • {instr}"
            print(f"{c.BASE}│{self._pad_to_width( line, inner_width)}{c.BASE}│{c.ENDC}")

        print(f"{c.BASE}│{' ' * inner_width}│{c.ENDC}")

        # Notes header
        notes_header = f"  {c.GOLD}System Notes:{c.ENDC}"
        print(f"{c.BASE}│{self._pad_to_width( notes_header, inner_width)}{c.BASE}│{c.ENDC}")

        # Notes
        for note in notes:
            line = f"  • {note}"
            print(f"{c.BASE}│{self._pad_to_width( line, inner_width)}{c.BASE}│{c.ENDC}")

        print(f"{c.BASE}└{'─' * inner_width}┘{c.ENDC}")

    # --------------------------------------------------------------------------
    # [ TABLE RENDERING ]
    # --------------------------------------------------------------------------

    def render_table(self, headers: List[str], rows: List[List[str]],
                     column_widths: List[int] = None,
                     border_color: str = None,
                     header_color: str = None) -> List[str]:
        """
        Render a table with automatic column width calculation.
        """
        if border_color is None:
            border_color = self.color.VIOLET
        if header_color is None:
            header_color = self.color.SKY

        # Auto-calculate column widths if not provided
        if column_widths is None:
            column_widths = []
            for i, header in enumerate(headers):
                max_width = len(header)
                for row in rows:
                    if i < len(row):
                        max_width = max(max_width, len(str(row[i])))
                column_widths.append(max_width + 2)  # Add padding

        result = []
        num_cols = len(headers)

        # Build border parts
        top_border = border_color + "┌" + \
            "┬".join("─" * w for w in column_widths) + "┐" + self.color.ENDC
        mid_border = border_color + "├" + \
            "┼".join("─" * w for w in column_widths) + "┤" + self.color.ENDC
        bot_border = border_color + "└" + \
            "┴".join("─" * w for w in column_widths) + "┘" + self.color.ENDC

        result.append(top_border)

        # Header row
        header_cells = []
        for i, header in enumerate(headers):
            w = column_widths[i] if i < len(column_widths) else 10
            header_cells.append(
                f" {header_color}{header:<{w - 1}}{self.color.ENDC}")
        result.append(
            f"{border_color}│{self.color.ENDC}{border_color}│{self.color.ENDC}".join(header_cells).replace(
                f"{self.color.ENDC}{border_color}│{self.color.ENDC}", f"{self.color.ENDC} {border_color}│{self.color.ENDC} "))

        # Actually let's build it properly
        header_line = border_color + "│" + self.color.ENDC
        for i, header in enumerate(headers):
            w = column_widths[i] if i < len(column_widths) else 10
            header_line += (
                f" {header_color}{header:<{w - 2}}"
                f"{self.color.ENDC} {border_color}│{self.color.ENDC}"
            )
        result.append(header_line)

        result.append(mid_border)

        # Data rows
        for row in rows:
            row_line = border_color + "│" + self.color.ENDC
            for i, cell in enumerate(row):
                w = column_widths[i] if i < len(column_widths) else 10
                cell_text = str(
                    cell)[:w - 2] if len(str(cell)) > w - 2 else str(cell)
                row_line += (
                    f" {cell_text:<{w - 2}}"
                    f" {border_color}│{self.color.ENDC}"
                )
            result.append(row_line)

        result.append(bot_border)

        return result

    def print_channel_table(self,
                            channels: List[List[str]],
                            plp: str,
                            isi: str,
                            indent: str = "      ") -> None:
        """Print a formatted channel table with auto-adjusting borders."""
        c = self.color
        border = c.VIOLET

        # Calculate column widths based on content
        sid_width = 10
        name_width = 45
        type_width = 10

        # Adjust name width based on longest channel name
        for ch in channels:
            name_width = max(name_width, min(len(ch[1]) + 2, 60))

        header_text = f"SERVICE NAME (Matrix: {plp}/{isi})"

        # Top border
        print(
            f"\n{indent}{border}┌{ '─' * sid_width}┬{ '─' * name_width}┬{ '─' * type_width}┐{c.ENDC}")

        # Header
        print(
            f"{indent}{border}│{c.ENDC} "
            f"{'SID':<{sid_width - 2}} {border}│{c.ENDC} "
            f"{header_text:<{name_width - 2}} {border}│{c.ENDC} "
            f"{'TYPE':<{type_width - 2}} {border}│{c.ENDC}"
        )

        # Separator
        print(
            f"{indent}{border}├{ '─' * sid_width}┼{ '─' * name_width}┼{ '─' * type_width}┤{c.ENDC}")

        # Data rows
        for ch in channels:
            ch_type = "TV" if ch[2] == "1" else "Radio"
            clean_n = ch[1][:name_width - 2]
            print(
                f"{indent}{border}│{c.ENDC} "
                f"{ch[0]:<{sid_width - 2}} {border}│{c.ENDC} "
                f"{clean_n:<{name_width - 2}} {border}│{c.ENDC} "
                f"{ch_type:<{type_width - 2}} {border}│{c.ENDC}"
            )

        # Bottom border
        print(
            f"{indent}{border}└{ '─' * sid_width}┴{ '─' * name_width}┴{ '─' * type_width}┘{c.ENDC}")

    def print_transponder_table(
            self,
            transponders: List[Dict],
            indent: str = "") -> None:
        """Print transponder table with auto-adjusting borders."""
        c = self.color
        border = c.TEAL

        # Column widths
        freq_w, pol_w, sr_w, mod_w = 10, 8, 10, 10

        # Calculate URL column width based on longest URL
        url_w = 42
        for tp in transponders:
            url_name = tp['mux_url'].split('/')[-1]
            url_w = max(url_w, min(len(url_name) + 2, 60))

        # Top border
        print(
            f"\n{indent}{border}┌{ '─' * freq_w}┬{ '─' * pol_w}┬{ '─' * sr_w}┬{ '─' * mod_w}┬{ '─' * url_w}┐{c.ENDC}")

        # Header
        print(f"{indent}{border}│{c.ENDC} {c.SKY}{'FREQ':<{freq_w - 2}}{c.ENDC} {border}│{c.ENDC} {c.SKY}{'POL':<{pol_w - 2}}{c.ENDC} {border}│{c.ENDC} {c.SKY}{'SR':<{sr_w - 2}}{c.ENDC} {border}│{c.ENDC} {c.SKY}{'MOD':<{mod_w - 2}}{c.ENDC} {border}│{c.ENDC} {c.SKY}{'MUX URL / BEAM REFERENCE':<{url_w - 2}}{c.ENDC} {border}│{c.ENDC}")

        # Separator
        print(
            f"{indent}{border}├{ '─' * freq_w}┼{ '─' * pol_w}┼{ '─' * sr_w}┼{ '─' * mod_w}┼{ '─' * url_w}┤{c.ENDC}")

        # Data rows
        for tp in transponders:
            url_name = tp['mux_url'].split('/')[-1][:url_w - 2]
            print(
                f"{indent}{border}│{c.ENDC} {c.LIME}{tp['f_v']:<{freq_w - 2}}"
                f"{c.ENDC} {border}│{c.ENDC} {c.BASE}{tp['p_r']:<{pol_w - 2}}"
                f"{c.ENDC} {border}│{c.ENDC} {c.GOLD}{tp['sr']:<{sr_w - 2}}"
                f"{c.ENDC} {border}│{c.ENDC} {c.VIOLET}{tp['mod']:<{mod_w - 2}}"
                f"{c.ENDC} {border}│{c.ENDC} {c.BASE}{url_name:<{url_w - 2}}"
                f"{c.ENDC} {border}│{c.ENDC}"
            )

        # Bottom border
        print(
            f"{indent}{border}└{ '─' * freq_w}┴{ '─' * pol_w}┴{ '─' * sr_w}┴{ '─' * mod_w}┴{ '─' * url_w}┘{c.ENDC}")

    # --------------------------------------------------------------------------
    # [ SPECIALIZED BOXES ]
    # --------------------------------------------------------------------------

    def print_band_config_box(
            self,
            sat_slug: str,
            sat_deg: float,
            sat_dir: str,
            auto_suggest_cband: bool) -> None:
        """Print band configuration dialog box."""
        c = self.color
        border = c.VIOLET
        width = self.terminal_width
        inner = width - 2

        # Calculate visible content widths
        target_text = f"  Target: {sat_slug}"
        degree_text = f"  Sat Degree: {sat_deg}° {sat_dir}"
        suggest_val = 'C-BAND' if auto_suggest_cband else 'KU-BAND'
        suggest_col = c.LIME if auto_suggest_cband else c.BASE
        suggest_text = f"  Auto-Detection Suggestion: {suggest_val}"

        print(f"\n{border}┌──[ BAND CONFIGURATION ]{'─' * (inner - 25)}┐{c.ENDC}")

        # Target line with proper padding
        visible_content = f"  Target: {sat_slug}"
        padding = inner - self.visible_width(f"{c.GOLD}{sat_slug}{c.ENDC}") - 2
        print(f"{border}│{c.ENDC}{c.GOLD}{visible_content}{' ' * max(0, padding - len('  Target: '))}{c.ENDC}{border}│{c.ENDC}")

        # Degree line
        deg_content = f"  Sat Degree: {sat_deg}° {sat_dir}"
        deg_padding = inner - len(deg_content) - 2
        print(f"{border}│{c.ENDC}{c.SKY}{deg_content}{' ' * max(0, deg_padding)}{c.ENDC}{border}│{c.ENDC}")

        # Suggestion line with colored value
        sug_prefix = "  Auto-Detection Suggestion: "
        sug_visible_len = len(sug_prefix) + len(suggest_val)
        sug_padding = inner - sug_visible_len - 2
        print(f"{border}│{c.ENDC}{sug_prefix}{suggest_col}{suggest_val}{c.ENDC}{' ' * max(0, sug_padding)}{border}│{c.ENDC}")

        print(f"{border}└{'─' * inner}┘{c.ENDC}")

    def print_satellite_header(
            self,
            sat_deg: float,
            sat_dir: str,
            sat_slug: str) -> None:
        """Print satellite header with auto-adjusted borders."""
        c = self.color
        width = min(self.terminal_width, 90)
        inner = width - 2

        # Build content
        pos_text = f"SATELLITE POSITION: {sat_deg}°{sat_dir}"
        target_text = f"TARGET: {sat_slug}"

        # Calculate padding
        pos_visible = len(pos_text)
        target_visible = len(target_text)
        gap = inner - pos_visible - target_visible - 4  # 4 for spacing

        print(f"\n{c.GOLD}╔{'═' * inner}╗{c.ENDC}")
        print(
            f"{c.GOLD}║{c.ENDC} {c.BOLD}{c.SKY}{pos_text}{c.ENDC}{ ' ' * gap}{c.BOLD}{c.SKY}{target_text}{c.ENDC} {c.GOLD}║{c.ENDC}")
        print(f"{c.GOLD}╚{'═' * inner}╝{c.ENDC}")

    def print_summary_banner(
            self, stats: Dict[str, Any], width: int = None) -> None:
        """Print execution summary with auto-adjusted borders."""
        c = self.color
        if width is None:
            width = self.terminal_width
        inner = width - 2

        # Top border
        print(f"\n{c.GOLD}█{'▀' * inner}█{c.ENDC}")

        # Title
        title = "GLOBAL DX EXECUTION SUMMARY"
        title_padding = inner - len(title) - 2
        print(
            f"{c.GOLD}█{c.ENDC} {c.SKY}{title}{c.ENDC}{ ' ' * title_padding}{c.GOLD}█{c.ENDC}")

        # Stats
        for label, value in stats.items():
            stat_text = f"├─ {label}: {c.BOLD}{value}{c.ENDC}"
            visible_len = len(f"├─ {label}: {value}")
            padding = inner - visible_len - 2
            print(f"{c.GOLD}█{c.ENDC} {c.BASE}{stat_text}{' ' * max(0, padding)}{c.GOLD}█{c.ENDC}")

        # Bottom border
        print(f"{c.GOLD}█{'▄' * inner}█{c.ENDC}\n")


# ==============================================================================
# [ 📝 LOGGING ENGINE ]
# ==============================================================================
class MasterLogger:
    """Dual-stream logger: terminal output + file logging with ANSI stripping."""

    ANSI_ESCAPE = re.compile(r'\x1B(?:[@-Z\\-_]|\[[0-?]*[ -/]*[@-~])')

    def __init__(self, filename: str = "dx_session.log"):
        self.terminal = sys.stdout
        self.log_file = open(filename, "a", encoding="utf-8")

    def write(self, message: str) -> None:
        self.terminal.write(message)
        clean_msg = self.ANSI_ESCAPE.sub('', message)
        self.log_file.write(clean_msg)

    def flush(self) -> None:
        self.terminal.flush()
        self.log_file.flush()

    def log_debug(self, msg: str) -> None:
        """Writes detailed technical data ONLY to the file."""
        ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        self.log_file.write(f"[DEBUG][{ts}] {msg}\n")
        self.log_file.flush()

    def close(self) -> None:
        """Close the log file properly."""
        self.log_file.close()


# ==============================================================================
# [ 🛰️ MAIN APPLICATION CLASS ]
# ==============================================================================
class LyngSatDXMaster:
    """
    Main application class for LyngSat DX Master Suite.
    Encapsulates all functionality for satellite scanning and channel extraction.
    """

    # Junk keywords for filtering noise in channel names
    JUNK_KEYWORDS = [
        "ROLL-OFF", "FOOTPRINT", "C BAND", "KU BAND", "DVB-S",
        "CLEAR", "MPEG", "HEVC", "DBW", "INDEX", "VERIFIED"
    ]

    def __init__(self):
        self.color = ColorTheme()
        self.ui = UIRenderer(self.color)
        self.logger: Optional[MasterLogger] = None
        self.total_channels = 0
        self.total_tps = 0
        self.running = True

        # Setup signal handlers for graceful shutdown
        self._setup_signal_handlers()

    def _setup_signal_handlers(self) -> None:
        """Setup keyboard interrupt signal handlers."""
        signal.signal(signal.SIGINT, self._handle_interrupt)
        signal.signal(signal.SIGTERM, self._handle_interrupt)

    def _handle_interrupt(self, signum: int, frame) -> None:
        """Handle Ctrl+C and other interrupt signals gracefully."""
        self.running = False
        c = self.color
        print(f"\n\n{c.CRIMSON}{c.BOLD}⚠️  INTERRUPT RECEIVED{c.ENDC}")
        print(f"{c.GOLD}🛑 Gracefully shutting down...{c.ENDC}")
        self._cleanup()
        sys.exit(0)

    def _cleanup(self) -> None:
        """Cleanup resources before exit."""
        if self.logger:
            self.log_proc("Session interrupted by user.", self.color.CRIMSON)
            self.logger.close()

    # --------------------------------------------------------------------------
    # [ UI METHODS ]
    # --------------------------------------------------------------------------

    def print_banner(self) -> None:
        """Display the application banner."""
        self.ui.print_banner()

    def print_instructions(self) -> None:
        """Display usage instructions."""
        instructions = [
            "Paste your LyngSat URLs line by line.",
            "Press ENTER on an empty line to trigger the batch extraction.",
            "Press Ctrl+C at any time to gracefully exit."
        ]
        notes = [
            "C-Band frequencies automatically apply +0.1 degree indexing.",
            "Two-Pass Engine: Extracts Frequencies first, then Service Tables.",
            "Auto-adjusting UI borders for any terminal width."]
        self.ui.print_instructions_box(instructions, notes)

    def log_proc(
            self,
            msg: str,
            color: Optional[str] = None,
            debug_only: bool = False) -> None:
        """Log a message with timestamp and optional color."""
        if color is None:
            color = self.color.BASE

        ts = datetime.now().strftime("%H:%M:%S")
        formatted_msg = f"{self.color.BASE}[{ts}]{self.color.ENDC} {color}{msg}{self.color.ENDC}"

        if debug_only:
            if self.logger:
                self.logger.log_debug(msg)
        else:
            print(formatted_msg)

    def _print_summary(self, urls_count: int, duration: float) -> None:
        """Print the final execution summary."""
        stats = {
            "Total Satellites Processed": urls_count,
            "Total Unique Transponders": self.total_tps,
            "Total Channels Mapped": self.total_channels,
            f"Operation Time": f"{duration:.2f}s"
        }
        self.ui.print_summary_banner(stats)

    # --------------------------------------------------------------------------
    # [ STORAGE METHODS ]
    # --------------------------------------------------------------------------

    def setup_storage(self, sat_deg: float, sat_dir: str,
                      is_cband: bool) -> Tuple[str, str, str]:
        """Create necessary directories for storing output."""
        effective_pos = float(sat_deg) + 0.1 if is_cband else float(sat_deg)
        pos_label = f"{effective_pos:.1f}{sat_dir}"
        f_dir = "frequencies"
        c_dir = os.path.join("channellist", pos_label)

        for d in [f_dir, c_dir]:
            if not os.path.exists(d):
                os.makedirs(d)
            else:
                self._clear_existing_csvs(d, pos_label, f_dir, c_dir)

        return f_dir, c_dir, pos_label

    def _clear_existing_csvs(
            self,
            directory: str,
            pos_label: str,
            f_dir: str,
            c_dir: str) -> None:
        """Clear existing CSV files in the directory."""
        for item in os.listdir(directory):
            if not item.endswith(".csv"):
                continue

            item_path = os.path.join(directory, item)
            if directory == f_dir and item == f"f{pos_label}.csv":
                os.remove(item_path)
            elif directory == c_dir:
                os.remove(item_path)

    # --------------------------------------------------------------------------
    # [ USER INPUT METHODS ]
    # --------------------------------------------------------------------------

    def get_band_choice(self, sat_slug: str, sat_deg: float, sat_dir: str,
                        auto_suggest_cband: bool) -> bool:
        """Get user's band choice with auto-timeout."""
        c = self.color

        self.ui.print_band_config_box(
            sat_slug, sat_deg, sat_dir, auto_suggest_cband)

        prompt_text = f"{c.SKY}❓ Treat this satellite as C-BAND? (y/n) [Auto-resolving in 10s]: {c.ENDC}"
        print(prompt_text, end='', flush=True)

        user_choice = self._timed_input(10)

        is_cband_sat = (
            user_choice in [
                'y',
                'yes']) if user_choice else auto_suggest_cband
        print(f"\n  {c.GOLD}└─► Proceeding with: {c.BOLD}{'C-BAND' if is_cband_sat else 'KU-BAND'}{c.ENDC}")

        return is_cband_sat

    def _timed_input(self, timeout: int) -> Optional[str]:
        """Get user input with a timeout."""
        start_time = time.time()

        while (time.time() - start_time) < timeout:
            if not self.running:
                return None

            if sys.platform == 'win32':
                if msvcrt.kbhit():
                    return sys.stdin.readline().strip().lower()
            else:
                ready, _, _ = select.select([sys.stdin], [], [], 0.1)
                if ready:
                    return sys.stdin.readline().strip().lower()

            time.sleep(0.1)

        return None

    def collect_urls(self) -> List[str]:
        """Collect satellite URLs from user input."""
        c = self.color
        urls = []

        while self.running:
            try:
                u = input(f"{c.GOLD}🔗 SAT URL #{len(urls) + 1}:{c.ENDC} ").strip()
                if not u:
                    break
                urls.append(u)
            except EOFError:
                break

        return urls

    # --------------------------------------------------------------------------
    # [ PARSING METHODS ]
    # --------------------------------------------------------------------------

    def parse_mux_channels(
            self,
            url: str,
            save_path: str,
            freq_label: str) -> int:
        """Parse and extract channels from a mux URL."""
        if not self.running:
            return 0

        try:
            from curl_cffi import requests
            from bs4 import BeautifulSoup

            res = requests.get(url, impersonate="chrome", timeout=15)
            soup = BeautifulSoup(res.content, 'html.parser')

            matrix_buckets = self._extract_channels_from_soup(soup)

            if matrix_buckets:
                return self._save_channel_buckets(
                    matrix_buckets, save_path, freq_label)

            return 0

        except Exception as e:
            self.log_proc(f"Matrix Error: {e}", debug_only=True)
            return 0

    def _extract_channels_from_soup(self, soup) -> Dict[str, List[List[str]]]:
        """Extract channel data from BeautifulSoup object."""
        matrix_buckets = {}
        current_plp, current_isi, current_pid = "0", "0", "4096"

        for el in soup.find_all(['div', 'tr']):
            el_text = el.get_text(" ", strip=True).upper()

            if el.name == 'div':
                current_plp, current_isi, current_pid = self._parse_header_element(
                    el_text, current_plp, current_isi, current_pid)
                continue

            channel_data = self._extract_channel_from_row(el)
            if channel_data:
                bucket_id = f"PLP{current_plp}PID{current_pid}_ISI{current_isi}"
                if bucket_id not in matrix_buckets:
                    matrix_buckets[bucket_id] = []
                matrix_buckets[bucket_id].append(channel_data)

        return matrix_buckets

    def _parse_header_element(
            self, el_text: str, plp: str, isi: str, pid: str) -> Tuple[str, str, str]:
        """Parse PLP, ISI, and PID from header element."""
        plp_m = re.search(r'PLP\s*(\d+)', el_text)
        isi_m = re.search(r'STREAM\s*(\d+)', el_text)
        pid_m = re.search(r'PID\s*(\d+)', el_text)

        if plp_m:
            plp = plp_m.group(1)
        if isi_m:
            isi = isi_m.group(1)
        if pid_m:
            pid = pid_m.group(1)

        return plp, isi, pid

    def _extract_channel_from_row(self, el) -> Optional[List[str]]:
        """Extract channel data from a table row element."""
        tds = el.find_all('td')
        if len(tds) < 3:
            return None

        raw_name = tds[2].get_text(strip=True)
        if not raw_name or any(jk in raw_name.upper()
                               for jk in self.JUNK_KEYWORDS) or "," in raw_name:
            return None

        sid_raw = tds[0].get_text(strip=True)
        if not re.match(r'^\d+$', sid_raw):
            return None

        link = tds[2].find('a', href=True)
        ch_type = "2" if link and "radiochannels" in link['href'] else "1"

        return [sid_raw, raw_name, ch_type]

    def _save_channel_buckets(
            self,
            matrix_buckets: Dict,
            save_path: str,
            freq_label: str) -> int:
        """Save channel buckets to CSV files."""
        c = self.color
        clean_prefix = re.match(r'(\d+[LRHV]\d+)', freq_label).group(1)
        output_dir = os.path.dirname(save_path)
        total_services = 0

        for bucket, channels in matrix_buckets.items():
            filename, final_path = self._generate_bucket_filename(
                bucket, clean_prefix, output_dir
            )

            with open(final_path, 'w', newline='', encoding='utf-8') as f:
                writer = csv.writer(f)
                writer.writerows(channels)

            h_plp = re.search(r'PLP(\d+)', bucket).group(1)
            h_isi = re.search(r'ISI(\d+)', bucket).group(1)

            self.ui.print_channel_table(channels, h_plp, h_isi)
            print(
                f"      {c.LIME}└─► Saved: {filename} | Total: {len(channels)} services{c.ENDC}")

            total_services += len(channels)

        return total_services

    def _generate_bucket_filename(
            self, bucket: str, clean_prefix: str, output_dir: str) -> Tuple[str, str]:
        """Generate filename for a channel bucket."""
        h_plp = re.search(r'PLP(\d+)', bucket).group(1)
        h_isi = re.search(r'ISI(\d+)', bucket).group(1)
        h_pid = re.search(r'PID(\d+)', bucket).group(1)

        isi_prefix = f"_ISI{h_isi}" if h_isi != "0" else ""
        filename = f"{clean_prefix}PLP{h_plp}PID{h_pid}{isi_prefix}.csv"
        final_path = os.path.join(output_dir, filename)

        return filename, final_path

    # --------------------------------------------------------------------------
    # [ SCANNING METHODS ]
    # --------------------------------------------------------------------------

    def deep_scan_satellite(self, url: str) -> None:
        """Perform deep scan of a satellite URL."""
        if not self.running:
            return

        try:
            from curl_cffi import requests
            from bs4 import BeautifulSoup

            self.log_proc(f"Establishing Uplink: {url}", self.color.GOLD)
            res = requests.get(url, impersonate="chrome", timeout=15)
            html_source = res.text
            soup = BeautifulSoup(html_source, 'html.parser')

            sat_info = self._extract_satellite_info(soup)
            if not sat_info:
                return

            sat_deg, sat_dir, sat_slug = sat_info
            auto_suggest_cband = self._detect_band(soup)

            is_cband_sat = self.get_band_choice(
                sat_slug, sat_deg, sat_dir, auto_suggest_cband)
            f_dir, c_dir, pos_label = self.setup_storage(
                sat_deg, sat_dir, is_cband_sat)

            self.ui.print_satellite_header(sat_deg, sat_dir, sat_slug)

            transponders = self._discover_transponders(
                soup, sat_deg, sat_dir, is_cband_sat)
            self.ui.print_transponder_table(transponders)

            c = self.color
            print(
                f"  {c.LIME}└─► Total Verified T2-MI Frequencies Discovered: {c.BOLD}{len(transponders)}{c.ENDC}")

            self.total_tps += len(transponders)

            self._process_transponders(transponders, c_dir)

            self._save_frequency_file(f_dir, pos_label, transponders)

        except Exception as e:
            self.log_proc(f"Error: {e}", self.color.CRIMSON)

    def _extract_satellite_info(
            self, soup) -> Optional[Tuple[float, str, str]]:
        """Extract satellite position and slug from page."""
        title = soup.title.string if soup.title else ""
        sat_m = re.search(r'(\d+\.?\d*)\s?°?\s?([EW])', title)

        if not sat_m:
            return None

        sat_deg = float(sat_m.group(1))
        sat_dir = sat_m.group(2)
        sat_slug = soup.find('title').string.split(
            '/')[-1].replace(".html", "") if soup.title else ""

        return sat_deg, sat_dir, sat_slug

    def _detect_band(self, soup) -> bool:
        """Auto-detect if satellite is C-Band or KU-Band."""
        rows = soup.find_all('tr')
        c_w, k_w = 0, 0

        for r in rows:
            td1 = r.find('td')
            if td1:
                fm = re.search(
                    r'^(\d{4,5})\s*([LRHV])',
                    td1.get_text(
                        strip=True).upper())
                if fm:
                    f_val = int(fm.group(1))
                    if 3000 <= f_val <= 4999:
                        c_w += 2
                    elif f_val >= 10000:
                        k_w += 2

        return c_w >= k_w if (c_w + k_w) > 0 else False

    def _discover_transponders(
            self,
            soup,
            sat_deg: float,
            sat_dir: str,
            is_cband: bool) -> List[Dict]:
        """Discover all T2-MI transponders from satellite page."""
        from curl_cffi import requests
        from bs4 import BeautifulSoup

        rows = soup.find_all('tr')
        transponders_data = []
        seen_tps = set()

        for row in rows:
            if not self.running:
                break

            tp_data = self._process_transponder_row(
                row, sat_deg, sat_dir, is_cband, seen_tps
            )
            if tp_data:
                transponders_data.append(tp_data)

        return transponders_data

    def _process_transponder_row(
            self,
            row,
            sat_deg: float,
            sat_dir: str,
            is_cband: bool,
            seen_tps: set) -> Optional[Dict]:
        """Process a single transponder row."""
        from curl_cffi import requests
        from bs4 import BeautifulSoup

        tds = row.find_all('td')
        if len(tds) < 5:
            return None

        row_text = row.get_text(" ", strip=True).upper()
        fm = re.search(r'(\d{4,5})\s*([LRHV])', row_text)

        if not fm:
            return None

        f_v, p_r = fm.group(1), fm.group(2)
        beam_link = row.find('a', href=re.compile(r'muxes/|/muxes/'))

        if not beam_link:
            return None

        mux_url = f"https://www.lyngsat.com/muxes/{beam_link['href'].split('/')[-1]}"

        self.log_proc(
            f"Evaluating potential T2-MI candidate: {f_v} {p_r}",
            debug_only=True)

        return self._validate_and_extract_transponder(
            mux_url, f_v, p_r, sat_deg, sat_dir, is_cband, seen_tps
        )

    def _validate_and_extract_transponder(
            self,
            mux_url: str,
            f_v: str,
            p_r: str,
            sat_deg: float,
            sat_dir: str,
            is_cband: bool,
            seen_tps: set) -> Optional[Dict]:
        """Validate and extract transponder data from mux URL."""
        from curl_cffi import requests
        from bs4 import BeautifulSoup

        try:
            self.log_proc(
                f"[REQ] Requesting Mux Data -> {mux_url}",
                debug_only=True)

            req_start = time.time()
            mux_res = requests.get(mux_url, impersonate="chrome", timeout=12)
            latency = (time.time() - req_start) * 1000

            self.log_proc(
                f"[RES] HTTP {mux_res.status_code} | Latency: {latency:.2f}ms",
                debug_only=True)

            if mux_res.status_code != 200:
                self.log_proc(
                    f"[FAIL] Skipping due to HTTP Error {mux_res.status_code}",
                    debug_only=True)
                return None

            mux_soup = BeautifulSoup(mux_res.text, 'html.parser')
            mux_text = mux_soup.get_text().upper()

            is_t2mi = "PLP" in mux_text
            is_vidi = "VIDI TV" in mux_text and "PLP" in mux_text

            self.log_proc(
                f"[LOGIC] PLP_Found={is_t2mi} | VidiTV_Found={is_vidi}",
                debug_only=True)

            if not (is_t2mi or is_vidi):
                self.log_proc(
                    f"[FILTER] Frequency {f_v} {p_r} rejected: No T2-MI/PLP markers.",
                    debug_only=True)
                return None

            return self._extract_transponder_data(
                mux_text, mux_url, f_v, p_r, sat_deg, sat_dir, is_cband, seen_tps)

        except Exception as e:
            self.log_proc(
                f"[CRITICAL ERROR] Exception: {str(e)}", debug_only=True)
            return None

    def _extract_transponder_data(
            self,
            mux_text: str,
            mux_url: str,
            f_v: str,
            p_r: str,
            sat_deg: float,
            sat_dir: str,
            is_cband: bool,
            seen_tps: set) -> Optional[Dict]:
        """Extract transponder data from mux page text."""
        plp_matches = re.findall(r'PLP\s*(\d+)', mux_text)
        pid_matches = re.findall(r'PID\s*(\d+)', mux_text)
        sr_m = re.search(r'SR-FEC:.*?(\d+)', mux_text)
        nid_m = re.search(r'NID\s*:\s*(\d+)', mux_text)
        tid_m = re.search(r'TID\s*:\s*(\d+)', mux_text)

        plp_id = "-".join(sorted(set(plp_matches), key=int)
                          ) if plp_matches else "0"
        pid_id = "-".join(sorted(set(pid_matches), key=int)
                          ) if pid_matches else "4096"
        sr = sr_m.group(1) if sr_m else "0"
        nid = nid_m.group(1) if nid_m else "N/A"
        tid = tid_m.group(1) if tid_m else "N/A"

        self.log_proc(f"[EXTRACT] PLP:{plp_id} | PID:{pid_id} | SR:{sr} | NID:{nid} | TID:{tid}", debug_only=True)

        if int(sr) < 1000:
            self.log_proc(
                f"[ABORT] Invalid SR detected ({sr}). Frequency discarded.",
                debug_only=True)
            return None

        tp_id = f"{f_v}{p_r}{sr}"
        if tp_id in seen_tps:
            self.log_proc(
                f"[DUPLICATE] Frequency {tp_id} already in stack.",
                debug_only=True)
            return None

        seen_tps.add(tp_id)
        mod = "8PSK" if "8PSK" in mux_text else "QPSK"
        hw_pos = round(float(sat_deg) + 0.1, 1) if is_cband else float(sat_deg)
        p_map = {"H": "0", "V": "1", "L": "2", "R": "3"}

        self.log_proc(
            f"[SUCCESS] Verified T2-MI Mux: {f_v} {p_r} {sr} {mod}",
            debug_only=True)

        return {
            "f_v": f_v,
            "p_r": p_r,
            "sr": sr,
            "mod": mod,
            "mux_url": mux_url,
            "file_label": f"{f_v}{p_r}{sr}PLP{plp_id}PID{pid_id}",
            "csv_row": [
                f_v, p_map.get(p_r, "0"), sr, f"{hw_pos:.1f}", sat_dir,
                "2", "9", "1", "1", "2" if mod == "8PSK" else "1", "0", "2", mux_url
            ]
        }

    def _process_transponders(
            self,
            transponders: List[Dict],
            c_dir: str) -> None:
        """Process each transponder and extract channels."""
        c = self.color

        for tp in transponders:
            if not self.running:
                break

            print(
                f"\n{c.TEAL}▶ {c.SKY}Drill-Down: Fetching services for {c.ENDC}{c.BOLD}{c.LIME}{tp['f_v']} {tp['p_r']}{c.ENDC}")
            target_csv = os.path.join(c_dir, f"{tp['file_label']}.csv")
            self.total_channels += self.parse_mux_channels(
                tp['mux_url'], target_csv, tp['file_label'])

    def _save_frequency_file(
            self,
            f_dir: str,
            pos_label: str,
            transponders: List[Dict]) -> None:
        """Save frequency data to CSV file."""
        csv_rows = [tp['csv_row'] for tp in transponders]

        with open(os.path.join(f_dir, f"f{pos_label}.csv"), 'w', newline='', encoding='utf-8') as f:
            writer = csv.writer(f)
            writer.writerow([
                "Freq", "Pol", "SR", "Pos", "Dir", "Inv", "FEC",
                "Sys", "Mod", "RO", "Pilot", "MuxURL"
            ])
            writer.writerows(csv_rows)

    # --------------------------------------------------------------------------
    # [ MAIN ENTRY POINT ]
    # --------------------------------------------------------------------------

    def run(self) -> None:
        """Main application entry point."""
        os.system('clear' if os.name == 'posix' else 'cls')

        # Ask for logging
        enable_log = input(
            f"{self.color.GOLD}❓ Enable detailed session logging to file? (y/n): {self.color.ENDC}").lower()
        if enable_log == 'y':
            log_name = f"DX_LOG_{datetime.now().strftime('%Y%m%d_%H%M%S')}.log"
            self.logger = MasterLogger(log_name)
            sys.stdout = self.logger
            self.log_proc(
                f"Session started. Outputting to {log_name}",
                self.color.LIME)

        self.print_banner()
        self.print_instructions()

        urls = self.collect_urls()

        if urls and self.running:
            start = time.time()

            for url in urls:
                if not self.running:
                    break
                self.deep_scan_satellite(url)

            duration = time.time() - start
            self._print_summary(len(urls), duration)

        self._cleanup()


# ==============================================================================
# [ 🚀 BOOTSTRAP ]
# ==============================================================================
def main():
    """Application bootstrap function."""
    try:
        app = LyngSatDXMaster()
        app.run()
    except KeyboardInterrupt:
        print(
            f"\n{ColorTheme.CRIMSON}⚠️  Operation cancelled by user.{ColorTheme.ENDC}")
        sys.exit(0)
    except Exception as e:
        print(f"{ColorTheme.CRIMSON}Fatal error: {e}{ColorTheme.ENDC}")
        sys.exit(1)


if __name__ == "__main__":
    main()
