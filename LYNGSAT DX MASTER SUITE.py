#!/usr/bin/env python3
"""
LyngSat DX Master Suite - Version 17.18
FIX: PLS Extraction Logic Corrected.
     - Properly extracts PLS Mode/Code from mux page text.
     - Maps the extracted PLS value (e.g., 1,242133) 1:1 with the pids-plps matrix.
     - Defaults to 0,0 only if no PLS string is found.
"""

import os
import sys
import re
import csv
import time
import signal
import unicodedata
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
# [ 🖼️ UI RENDERER ]
# ==============================================================================
class UIRenderer:
    ANSI_ESCAPE = re.compile(r'\x1B(?:[@-Z\\-_]|\[[0-?]*[ -/]*[@-~])')
    DEFAULT_WIDTH = 80

    def __init__(self, color: ColorTheme):
        self.color = color
        self.terminal_width = self._get_terminal_width()

    def _get_terminal_width(self) -> int:
        try: return os.get_terminal_size().columns
        except: return self.DEFAULT_WIDTH

    @staticmethod
    def strip_ansi(text: str) -> str:
        return UIRenderer.ANSI_ESCAPE.sub('', text)

    @staticmethod
    def visible_width(text: str) -> int:
        stripped = UIRenderer.strip_ansi(text)
        width = 0
        for char in stripped:
            eaw = unicodedata.east_asian_width(char)
            if eaw in ('F', 'W'): width += 2
            elif unicodedata.category(char) in ('Mn', 'Me', 'Cf'): width += 0
            else: width += 1
        return width

    def _pad_to_width(self, text: str, target_width: int, align: str = 'left') -> str:
        visible_len = self.visible_width(text)
        padding_needed = target_width - visible_len
        if padding_needed <= 0: return text
        if align == 'left': return text + ' ' * padding_needed
        elif align == 'right': return ' ' * padding_needed + text
        else: return ' ' * (padding_needed // 2) + text + ' ' * (padding_needed - padding_needed // 2)

    def render_banner(self, title: str, version: str, width: int = None) -> List[str]:
        if width is None: width = self.terminal_width
        inner_width = width - 2
        lines = []
        lines.append(self.color.GOLD + "█" + "▀" * inner_width + "█" + self.color.ENDC)
        title_text = f"  {title}"
        version_text = f"{version}  "
        gap = inner_width - self.visible_width(title_text) - self.visible_width(version_text)
        lines.append(f"{self.color.GOLD}█{self.color.ENDC}{self.color.SKY}{self.color.BOLD}{title_text}{self.color.ENDC}{' ' * gap}{self.color.GOLD}{version_text}█{self.color.ENDC}")
        lines.append(self.color.GOLD + "█" + "▄" * inner_width + "█" + self.color.ENDC)
        return lines

    def print_banner(self, title: str = "🛰️  LYNGSAT DX MASTER SUITE", version: str = "VER 17.18 | PLS-FIX") -> None:
        for line in self.render_banner(title, version): print(line)

    def print_instructions_box(self, instructions: List[str], notes: List[str]) -> None:
        c = self.color
        width = self.terminal_width
        inner_width = width - 2
        print(f"{c.BASE}┌{'─' * inner_width}┐{c.ENDC}")
        print(f"{c.BASE}│{self._pad_to_width(f'  {c.BOLD}{c.SKY}RECURSIVE DEEP-SCAN SYSTEM v17.18{c.ENDC}', inner_width)}{c.BASE}│{c.ENDC}")
        print(f"{c.BASE}│{' ' * inner_width}│{c.ENDC}")
        print(f"{c.BASE}│{self._pad_to_width(f'  {c.LIME}Instructions:{c.ENDC}', inner_width)}{c.BASE}│{c.ENDC}")
        for instr in instructions: print(f"{c.BASE}│{self._pad_to_width(f'  • {instr}', inner_width)}{c.BASE}│{c.ENDC}")
        print(f"{c.BASE}│{' ' * inner_width}│{c.ENDC}")
        print(f"{c.BASE}│{self._pad_to_width(f'  {c.GOLD}System Notes:{c.ENDC}', inner_width)}{c.BASE}│{c.ENDC}")
        for note in notes: print(f"{c.BASE}│{self._pad_to_width(f'  • {note}', inner_width)}{c.BASE}│{c.ENDC}")
        print(f"{c.BASE}└{'─' * inner_width}┘{c.ENDC}")

    def print_channel_table(self, channels: List[List[str]], plp: str, isi: str, indent: str = "      ") -> None:
        c = self.color
        border = c.VIOLET
        sid_width, name_width, type_width = 10, 45, 10
        for ch in channels: name_width = max(name_width, min(len(ch[1]) + 2, 60))
        print(f"\n{indent}{border}┌{'─' * sid_width}┬{'─' * name_width}┬{'─' * type_width}┐{c.ENDC}")
        print(f"{indent}{border}│{c.ENDC} {'SID':<{sid_width - 2}} {border}│{c.ENDC} {f'SERVICE NAME (Matrix: {plp}/{isi})':<{name_width - 2}} {border}│{c.ENDC} {'TYPE':<{type_width - 2}} {border}│{c.ENDC}")
        print(f"{indent}{border}├{'─' * sid_width}┼{'─' * name_width}┼{'─' * type_width}┤{c.ENDC}")
        for ch in channels:
            ch_type = "TV" if ch[2] == "1" else "Radio"
            print(f"{indent}{border}│{c.ENDC} {ch[0]:<{sid_width - 2}} {border}│{c.ENDC} {ch[1][:name_width - 2]:<{name_width - 2}} {border}│{c.ENDC} {ch_type:<{type_width - 2}} {border}│{c.ENDC}")
        print(f"{indent}{border}└{'─' * sid_width}┴{'─' * name_width}┴{'─' * type_width}┘{c.ENDC}")

    def print_transponder_table(self, transponders: List[Dict], indent: str = "") -> None:
        c = self.color
        border = c.TEAL
        freq_w, pol_w, sr_w, mod_w, url_w = 10, 8, 10, 10, 42
        for tp in transponders: url_w = max(url_w, min(len(tp['mux_url'].split('/')[-1]) + 2, 60))
        print(f"\n{indent}{border}┌{'─' * freq_w}┬{'─' * pol_w}┬{'─' * sr_w}┬{'─' * mod_w}┬{'─' * url_w}┐{c.ENDC}")
        print(f"{indent}{border}│{c.ENDC} {c.SKY}{'FREQ':<{freq_w - 2}}{c.ENDC} {border}│{c.ENDC} {c.SKY}{'POL':<{pol_w - 2}}{c.ENDC} {border}│{c.ENDC} {c.SKY}{'SR':<{sr_w - 2}}{c.ENDC} {border}│{c.ENDC} {c.SKY}{'MOD':<{mod_w - 2}}{c.ENDC} {border}│{c.ENDC} {c.SKY}{'MUX URL / BEAM REFERENCE':<{url_w - 2}}{c.ENDC} {border}│{c.ENDC}")
        print(f"{indent}{border}├{'─' * freq_w}┼{'─' * pol_w}┼{'─' * sr_w}┼{'─' * mod_w}┼{'─' * url_w}┤{c.ENDC}")
        for tp in transponders:
            print(f"{indent}{border}│{c.ENDC} {c.LIME}{tp['f_v']:<{freq_w - 2}}{c.ENDC} {border}│{c.ENDC} {c.BASE}{tp['p_r']:<{pol_w - 2}}{c.ENDC} {border}│{c.ENDC} {c.GOLD}{tp['sr']:<{sr_w - 2}}{c.ENDC} {border}│{c.ENDC} {c.VIOLET}{tp['mod']:<{mod_w - 2}}{c.ENDC} {border}│{c.ENDC} {c.BASE}{tp['mux_url'].split('/')[-1][:url_w - 2]:<{url_w - 2}}{c.ENDC} {border}│{c.ENDC}")
        print(f"{indent}{border}└{'─' * freq_w}┴{'─' * pol_w}┴{'─' * sr_w}┴{'─' * mod_w}┴{'─' * url_w}┘{c.ENDC}")

    def print_band_config_box(self, sat_slug: str, sat_deg: float, sat_dir: str, auto_suggest_cband: bool) -> None:
        c = self.color
        border = c.VIOLET
        width = self.terminal_width
        inner = width - 2
        print(f"\n{border}┌──[ BAND CONFIGURATION ]{'─' * (inner - 24)}┐{c.ENDC}")
        print(f"{border}│{c.ENDC}{c.GOLD}  Target: {sat_slug}{' ' * (inner - self.visible_width(f'  Target: {sat_slug}'))}{c.ENDC}{border}│{c.ENDC}")
        print(f"{border}│{c.ENDC}{c.SKY}  Sat Degree: {sat_deg}° {sat_dir}{' ' * (inner - self.visible_width(f'  Sat Degree: {sat_deg}° {sat_dir}'))}{c.ENDC}{border}│{c.ENDC}")
        val = 'C-BAND' if auto_suggest_cband else 'KU-BAND'
        col = c.LIME if auto_suggest_cband else c.BASE
        print(f"{border}│{c.ENDC}  Auto-Detection Suggestion: {col}{val}{c.ENDC}{' ' * (inner - self.visible_width(f'  Auto-Detection Suggestion: {val}'))}{border}│{c.ENDC}")
        print(f"{border}└{'─' * inner}┘{c.ENDC}")

    def print_satellite_header(self, sat_deg: float, sat_dir: str, sat_slug: str) -> None:
        c = self.color
        width = min(self.terminal_width, 90)
        inner = width - 2
        pos_text = f"SATELLITE POSITION: {sat_deg}°{sat_dir}"
        target_text = f"TARGET: {sat_slug}"
        gap = inner - self.visible_width(pos_text) - self.visible_width(target_text) - 2
        print(f"\n{c.GOLD}╔{'═' * inner}╗{c.ENDC}")
        print(f"{c.GOLD}║{c.ENDC} {c.BOLD}{c.SKY}{pos_text}{c.ENDC}{' ' * gap}{c.BOLD}{c.SKY}{target_text}{c.ENDC} {c.GOLD}║{c.ENDC}")
        print(f"{c.GOLD}╚{'═' * inner}╝{c.ENDC}")

    def print_summary_banner(self, stats: Dict[str, Any], width: int = None) -> None:
        c = self.color
        if width is None: width = self.terminal_width
        inner = width - 2
        print(f"\n{c.GOLD}█{'▀' * inner}█{c.ENDC}")
        title = "GLOBAL DX EXECUTION SUMMARY"
        print(f"{c.GOLD}█{c.ENDC} {c.SKY}{title}{' ' * (inner - self.visible_width(title) - 1)}{c.GOLD}█{c.ENDC}")
        for label, value in stats.items():
            plain_text = f"├─ {label}: {value}"
            padding = inner - self.visible_width(plain_text) - 1
            print(f"{c.GOLD}█{c.ENDC} {c.BASE}{plain_text}{' ' * max(0, padding)}{c.GOLD}█{c.ENDC}")
        print(f"{c.GOLD}█{'▄' * inner}█{c.ENDC}\n")


# ==============================================================================
# [ 📝 LOGGING ENGINE ]
# ==============================================================================
class MasterLogger:
    ANSI_ESCAPE = re.compile(r'\x1B(?:[@-Z\\-_]|\[[0-?]*[ -/]*[@-~])')
    def __init__(self, filename: str = "dx_session.log"):
        self.terminal = sys.stdout
        self.log_file = open(filename, "a", encoding="utf-8")
        self._closed = False
    def write(self, message: str) -> None:
        self.terminal.write(message)
        if not self._closed: self.log_file.write(self.ANSI_ESCAPE.sub('', message))
    def flush(self) -> None:
        self.terminal.flush()
        if not self._closed: self.log_file.flush()
    def log_debug(self, msg: str) -> None:
        if self._closed: return
        self.log_file.write(f"[DEBUG][{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] {msg}\n")
        self.log_file.flush()
    def close(self) -> None:
        if not self._closed: self._closed = True; self.log_file.close()


# ==============================================================================
# [ 🛰️ MAIN APPLICATION CLASS ]
# ==============================================================================
class LyngSatDXMaster:
    JUNK_KEYWORDS = ["ROLL-OFF", "FOOTPRINT", "C BAND", "KU BAND", "DVB-S", "CLEAR", "MPEG", "HEVC", "DBW", "INDEX", "VERIFIED"]
    URL_HISTORY_FILE = "url.txt"

    def __init__(self):
        self.color = ColorTheme()
        self.ui = UIRenderer(self.color)
        self.logger: Optional[MasterLogger] = None
        self.total_channels = 0
        self.total_tps = 0
        self.running = True
        self._setup_signal_handlers()

    def _setup_signal_handlers(self) -> None:
        signal.signal(signal.SIGINT, lambda s, f: self._handle_interrupt(s, f))
        signal.signal(signal.SIGTERM, lambda s, f: self._handle_interrupt(s, f))

    def _handle_interrupt(self, signum: int, frame) -> None:
        self.running = False
        print(f"\n\n{self.color.CRIMSON}{self.color.BOLD}⚠️  INTERRUPT RECEIVED{self.color.ENDC}")
        print(f"{self.color.GOLD}🛑 Gracefully shutting down...{self.color.ENDC}")
        self._cleanup(interrupted=True)
        sys.exit(0)

    def _cleanup(self, interrupted: bool = False) -> None:
        if self.logger:
            self.log_proc("Session " + ("interrupted." if interrupted else "finished."), self.color.CRIMSON if interrupted else self.color.LIME)
            self.logger.close()

    def print_banner(self) -> None:
        self.ui.print_banner()

    def print_instructions(self) -> None:
        instructions = ["Select URL source from the main menu.", "Manual entry: Paste URLs line by line, ENTER to finish.", "Press Ctrl+C at any time to gracefully exit."]
        notes = ["Processed URLs are auto-saved to url.txt.", "C-Band frequencies automatically apply +0.1 degree indexing.", "Two-Pass Engine: Extracts Frequencies first, then Service Tables."]
        self.ui.print_instructions_box(instructions, notes)

    def log_proc(self, msg: str, color: Optional[str] = None, debug_only: bool = False) -> None:
        if color is None: color = self.color.BASE
        ts = datetime.now().strftime("%H:%M:%S")
        formatted_msg = f"{self.color.BASE}[{ts}]{self.color.ENDC} {color}{msg}{self.color.ENDC}"
        if debug_only:
            if self.logger: self.logger.log_debug(msg)
        else:
            print(formatted_msg)

    def _print_summary(self, urls_count: int, duration: float) -> None:
        stats = {"Total Satellites Processed": urls_count, "Total Unique Transponders": self.total_tps, "Total Channels Mapped": self.total_channels, "Operation Time": f"{duration:.2f}s"}
        self.ui.print_summary_banner(stats)

    # --------------------------------------------------------------------------
    # [ URL HISTORY MANAGEMENT ]
    # --------------------------------------------------------------------------

    def _save_url_to_history(self, url: str, pos_label: str) -> None:
        """Save processed URL to url.txt with pos_label if it doesn't already exist."""
        # Check for duplicates
        if os.path.exists(self.URL_HISTORY_FILE):
            try:
                with open(self.URL_HISTORY_FILE, 'r', encoding='utf-8') as f:
                    if any(line.strip() == f"{url},{pos_label}" for line in f):
                        return
            except: pass
        
        try:
            with open(self.URL_HISTORY_FILE, 'a', encoding='utf-8') as f: 
                f.write(f"{url},{pos_label}\n")
            self.log_proc(f"Saved to history: {url} [{pos_label}]", self.color.LIME)
        except Exception as e: self.log_proc(f"Failed to save URL history: {e}", self.color.CRIMSON)

    def _load_urls_from_file(self) -> List[Dict[str, Any]]:
        if not os.path.exists(self.URL_HISTORY_FILE): return []
        entries = []
        try:
            with open(self.URL_HISTORY_FILE, 'r', encoding='utf-8') as f:
                for line in f:
                    parts = line.strip().split(',', 1) # Split only on first comma
                    if len(parts) == 2 and parts[0]:
                        entries.append({'url': parts[0], 'pos_label': parts[1]})
        except: return []
        if not entries: return []
        
        print(f"\n{self.color.SKY}━━━━━━ URL HISTORY LOADER ━━━━━━{self.color.ENDC}")
        for i, e in enumerate(entries): print(f"  {self.color.GOLD}{i+1}{self.color.ENDC}. {e['url']} [{self.color.LIME}{e['pos_label']}{self.color.ENDC}]")
        print(f"  {self.color.GOLD}A{self.color.ENDC}. Process ALL\n  {self.color.GOLD}M{self.color.ENDC}. Manual Entry")
        choice = input(f"{self.color.SKY}❓ Select option: {self.color.ENDC}").strip().lower()
        if choice == 'a': return entries
        if choice == 'm': return []
        try:
            idx = int(choice) - 1
            return [entries[idx]] if 0 <= idx < len(entries) else []
        except: return []

    # --------------------------------------------------------------------------
    # [ STORAGE & USER INPUT ]
    # --------------------------------------------------------------------------

    def setup_storage(self, sat_deg: float, sat_dir: str, is_cband: bool) -> Tuple[str, str, str]:
        effective_pos = float(sat_deg) + 0.1 if is_cband else float(sat_deg)
        # Ensure exact formatting: e.g., 39.0E (forced uppercase direction)
        pos_label = f"{effective_pos:.1f}{sat_dir.upper()}"
        
        f_dir = "frequencies"
        c_dir = os.path.join("channellist", pos_label)
        
        for d in [f_dir, c_dir]:
            if not os.path.exists(d): os.makedirs(d)
            
        return f_dir, c_dir, pos_label

    def get_band_choice(self, sat_slug: str, sat_deg: float, sat_dir: str, auto_suggest_cband: bool) -> bool:
        self.ui.print_band_config_box(sat_slug, sat_deg, sat_dir, auto_suggest_cband)
        print(f"{self.color.SKY}❓ Treat this satellite as C-BAND? (y/n) [Auto-resolving in 10s]: {self.color.ENDC}", end='', flush=True)
        start = time.time()
        choice = None
        while (time.time() - start) < 10:
            if not self.running: return auto_suggest_cband
            if sys.platform == 'win32':
                if msvcrt.kbhit(): choice = sys.stdin.readline().strip().lower(); break
            else:
                if select.select([sys.stdin], [], [], 0.1)[0]: choice = sys.stdin.readline().strip().lower(); break
        is_cband = (choice in ['y', 'yes']) if choice else auto_suggest_cband
        print(f"\n  {self.color.GOLD}└─► Proceeding with: {self.color.BOLD}{'C-BAND' if is_cband else 'KU-BAND'}{self.color.ENDC}")
        return is_cband

    def collect_urls(self) -> List[str]:
        urls = []
        while self.running:
            try:
                u = input(f"{self.color.GOLD}🔗 SAT URL #{len(urls) + 1}:{self.color.ENDC} ").strip()
                if not u: break
                urls.append(u)
            except: break
        return urls

    # --------------------------------------------------------------------------
    # [ PARSING ]
    # --------------------------------------------------------------------------

    def parse_mux_channels(self, url: str, save_path: str, freq_label: str, pls_val: str = "0,0") -> Tuple[int, List[str]]:
        if not self.running: return 0, []
        try:
            from curl_cffi import requests
            from bs4 import BeautifulSoup
            res = requests.get(url, impersonate="chrome", timeout=15)
            soup = BeautifulSoup(res.content, 'html.parser')
            buckets = self._extract_channels_from_soup(soup)
            if not buckets: return 0, []
            
            total = 0
            clean_prefix = re.match(r'(\d+[LRHV]\d+)', freq_label).group(1)
            output_dir = os.path.dirname(save_path)
            
            # --- PLS FILENAME LOGIC ---
            # Extract the code from "mode,code" (e.g., "1,242133" -> "242133")
            pls_suffix = ""
            if pls_val and "," in pls_val:
                try:
                    p_code = pls_val.split(",")[1]
                    if p_code != "0":
                        pls_suffix = f"_PLS{p_code}"
                except IndexError:
                    pass
            
            found_keys = []

            for bucket, channels in buckets.items():
                plp = re.search(r'PLP(\d+)', bucket).group(1)
                isi = re.search(r'ISI(-?\d+)', bucket).group(1)
                pid = re.search(r'PID(\d+)', bucket).group(1)
                
                # Updated filename construction to include PLS suffix
                fname = f"{clean_prefix}PLP{plp}PID{pid}{'_ISI'+isi if isi != '-1' else ''}{pls_suffix}.csv"
                
                # Save Services
                with open(os.path.join(output_dir, fname), 'w', newline='', encoding='utf-8') as f: 
                    csv.writer(f).writerows(channels)
                
                self.ui.print_channel_table(channels, plp, isi)
                self.log_proc(f"Saved: {fname} ({len(channels)} services)", self.color.LIME)
                
                total += len(channels)
                found_keys.append(bucket)
            
            return total, found_keys
        except Exception as e: 
            self.log_proc(f"Matrix Error: {e}", self.color.CRIMSON)
            return 0, []

    def _extract_channels_from_soup(self, soup) -> Dict[str, List[List[str]]]:
        buckets = {}
        # Changed: Start with None to ensure we don't collect "Table 1" (Standard DVB-S)
        plp, isi, pid = None, None, None 
        
        # We iterate through all elements in order
        for el in soup.find_all(['div', 'tr', 'table']):
            # 1. Look for the T2-MI / Multistream Header Div
            if el.name == 'div' and 'mux-header' in el.get('class', []):
                txt = el.get_text(" ", strip=True).upper()
                # If we find a header, update our active bucket pointers
                m_plp = re.search(r'PLP\s*(\d+)', txt)
                m_pid = re.search(r'PID\s*(\d+)', txt)
                m_isi = re.search(r'STREAM\s*(\d+)', txt)
                
                plp = m_plp.group(1) if m_plp else "0"
                pid = m_pid.group(1) if m_pid else "4096"
                isi = m_isi.group(1) if m_isi else "-1"
                continue

            # 2. Process Table Rows only if we are currently "inside" a detected T2-MI bucket
            if el.name == 'tr' and plp is not None:
                tds = el.find_all('td')
                if len(tds) < 3: continue # Skip headers/short rows
                
                # Validation: First column must be a numeric SID
                sid = tds[0].get_text(strip=True)
                if not sid.isdigit(): continue
                
                # Extraction
                name_td = tds[2]
                name = name_td.get_text(strip=True)
                
                # Filter junk
                if not name or any(k in name.upper() for k in self.JUNK_KEYWORDS) or "," in name:
                    continue
                
                # Determine TV vs Radio
                link = name_td.find('a', href=True)
                typ = "2" if link and "radiochannels" in link['href'] else "1"
                
                bid = f"PLP{plp}PID{pid}_ISI{isi}"
                if bid not in buckets: buckets[bid] = []
                buckets[bid].append([sid, name, typ])
                
        return buckets

    # --------------------------------------------------------------------------
    # [ SCANNING ]
    # --------------------------------------------------------------------------

    def deep_scan_satellite(self, url: str, pre_determined_pos: Optional[str] = None) -> str:
        """Perform deep scan. Returns pos_label on success, empty string on failure."""
        if not self.running: return ""
        try:
            from curl_cffi import requests
            from bs4 import BeautifulSoup
            
            self.log_proc(f"Establishing Uplink: {url}", self.color.GOLD)
            res = requests.get(url, impersonate="chrome", timeout=15)
            soup = BeautifulSoup(res.text, 'html.parser')

            # 1. Info
            title = soup.title.string if soup.title else ""
            sat_m = re.search(r'(\d+\.?\d*)\s?°?\s*([EW])', title)
            if not sat_m: self.log_proc("Could not find sat info.", self.color.CRIMSON); return ""
            sat_deg, sat_dir, sat_slug = float(sat_m.group(1)), sat_m.group(2), title.split('/')[-1].replace(".html", "")

            # 2. Band/Pos Logic
            is_cband = False
            f_dir, c_dir, pos_label = "", "", ""

            if pre_determined_pos:
                self.log_proc(f"Override Active: Using exact position {pre_determined_pos} from history.", self.color.SKY)
                
                # Extract degree and direction from the history string
                m = re.match(r'(\d+\.?\d*)\s*([EWew])?', pre_determined_pos)
                if m: 
                    hist_deg = float(m.group(1))
                    # If history is missing E/W, fallback to the page title's direction
                    hist_dir = m.group(2).upper() if m.group(2) else sat_dir
                    
                    # Reconstruct to guarantee formatting consistency
                    pos_label = f"{hist_deg:.1f}{hist_dir}"
                    
                    # Update main variables for UI consistency
                    sat_deg = hist_deg
                    sat_dir = hist_dir
                else:
                    pos_label = pre_determined_pos

                f_dir = "frequencies"
                c_dir = os.path.join("channellist", pos_label)
                for d in [f_dir, c_dir]:
                    if not os.path.exists(d): os.makedirs(d)
                is_cband = False 
            else:
                rows = soup.find_all('tr')
                c_w, k_w = 0, 0
                for r in rows:
                    td = r.find('td')
                    if td:
                        fm = re.search(r'^(\d{4,5})\s*([LRHV])', td.get_text(strip=True).upper())
                        if fm:
                            f = int(fm.group(1))
                            if 3000<=f<=4999: c_w+=2
                            elif f>=10000: k_w+=2
                is_cband = self.get_band_choice(sat_slug, sat_deg, sat_dir, c_w >= k_w if (c_w+k_w)>0 else False)
                f_dir, c_dir, pos_label = self.setup_storage(sat_deg, sat_dir, is_cband)
                self._save_url_to_history(url, pos_label)

            self.ui.print_satellite_header(sat_deg, sat_dir, sat_slug)

            # 3. Discover
            transponders = []
            seen = set()
            
            mux_re = re.compile(r'muxes/')
            freq_pol_re = re.compile(r'[\-_]\d{4,5}[\-_][HVLR]\.html$', re.IGNORECASE)
            
            for row in soup.find_all('tr'):
                tds = row.find_all('td')
                if len(tds) < 1: continue
                
                row_text = row.get_text(" ", strip=True).upper()
                fm = re.search(r'(\d{4,5})\s*([LRHV])', row_text)
                if not fm: continue
                
                f_v, p_r = fm.group(1), fm.group(2)
                
                link = None
                potential_links = row.find_all('a', href=True)
                for l in potential_links:
                    h = l['href']
                    if mux_re.search(h): link = l; break
                    if freq_pol_re.search(h):
                        if 'footprints' not in h and 'maps' not in h: link = l; break

                if not link: continue
                
                href = link['href']
                if href.startswith('http'): mux_url = href
                elif href.startswith('/'): mux_url = f"https://www.lyngsat.com{href}"
                else: mux_url = f"https://www.lyngsat.com/muxes/{href}"

                if not self.running: break
                self.log_proc(f"Queueing Mux: {f_v} {p_r} -> {mux_url.split('/')[-1]}", self.color.BASE, debug_only=True)
                
                try:
                    mux_res = requests.get(mux_url, impersonate="chrome", timeout=12)
                    mux_soup = BeautifulSoup(mux_res.text, 'html.parser')
                    
                    # [FIXED] PLS EXTRACTION LOGIC
                    # We extract text from the entire soup safely to catch 'PLS Gold 242133' anywhere
                    mux_text_raw = mux_soup.get_text(separator=" ", strip=True)
                    mux_text_upper = mux_text_raw.upper()
                    
                    # Target format: "PLS Gold 242133" or "PLS Root 123"
                    pls_match = re.search(r'PLS\s+(Root|Gold|Combo)\s+(\d+)', mux_text_raw, re.IGNORECASE)
                    
                    if pls_match:
                        mode_str = pls_match.group(1).upper()
                        # Map strings to standard indices
                        found_mode = {"ROOT": "0", "GOLD": "1", "COMBO": "2"}.get(mode_str, "0")
                        found_code = pls_match.group(2)
                        current_pls = f"{found_mode},{found_code}"
                    else:
                        current_pls = "0,0" # Default if nothing found

                    if "PLP" not in mux_text_upper: 
                        self.log_proc(f"Rejected {f_v}: No PLP marker found (Standard DVB-S2?).", self.color.GOLD, debug_only=True)
                        continue

                    sr_m = re.search(r'SR-FEC:.*?(\d+)', mux_text_upper)
                    sr = sr_m.group(1) if sr_m else "0"
                    if int(sr) < 1000: continue
                    
                    tp_id = f"{f_v}{p_r}{sr}"
                    if tp_id in seen: continue
                    seen.add(tp_id)

                    # Provider Logic
                    prov = "N/A"
                    # 1. Primary Check: Multistream/T2-MI Header (e.g., "Cypriotic mux")
                    # These often use <b><i> inside <div class="mux-header"> instead of <a> links
                    mux_header_div = mux_soup.find("div", class_="mux-header")
                    if mux_header_div:
                        b_tag = mux_header_div.find('b')
                        if b_tag:
                            cand_prov = b_tag.get_text(strip=True)
                            if cand_prov: prov = cand_prov

                    # 2. Standard Logic: Table-based Provider/Package links
                    if prov == "N/A" or not prov:
                        mux_header_table = mux_soup.find('table', class_='mux-header')
                        if mux_header_table:
                            provider_a = mux_header_table.find('a', href=re.compile(r'/providers/'))
                            if provider_a: prov = provider_a.get_text(strip=True)
                            if not provider_a:
                                provider_a = mux_header_table.find('a', href=re.compile(r'/packages/'))
                                if provider_a: prov = provider_a.get_text(strip=True)

                    # 3. Fallback: Global page links
                    if prov == "N/A" or not prov:
                        provider_a = mux_soup.find('a', href=re.compile(r'/providers/'))
                        if provider_a: prov = provider_a.get_text(strip=True)
                        if not provider_a:
                             package_a = mux_soup.find('a', href=re.compile(r'/packages/'))
                             if package_a: prov = package_a.get_text(strip=True)

                    # 4. Fallback: Title Tag Parsing
                    if prov == "N/A" or not prov:
                        t_tag = mux_soup.find('title')
                        if t_tag:
                            t_text = t_tag.get_text(strip=True).replace(" - LyngSat", "")
                            parts = t_text.split(" - ")
                            if len(parts) > 1:
                                cand = parts[-1]
                                if re.match(r'^\d{4,5}\s*[VHRL]', cand) and len(parts) > 2: cand = parts[-2]
                                if not re.match(r'^\d{4,5}\s*[VHRL]', cand): prov = cand

                    # 5. Final Fallback: Regex Search in Raw Text
                    if prov == "N/A" or not prov:
                         prov_m = re.search(r'Provider:\s*([A-Za-z0-9\s\.\-]+)', mux_text_raw, re.IGNORECASE)
                         if prov_m:
                             p_val = prov_m.group(1).strip()
                             if not re.search(r'\d{4,5}\s*[VHRL]', p_val): prov = p_val

                    # Detect Modulation
                    if "32APSK" in mux_text_upper: mod_val, mod_label = "4", "32APSK"
                    elif "16APSK" in mux_text_upper: mod_val, mod_label = "3", "16APSK"
                    elif "8PSK" in mux_text_upper: mod_val, mod_label = "2", "8PSK"
                    elif "QPSK" in mux_text_upper: mod_val, mod_label = "1", "QPSK"
                    else: mod_val, mod_label = "0", "AUTO"

                    sys_val = "2" if "DVB-S2X" in mux_text_upper else "1"
                    hw = round(float(sat_deg) + 0.1, 1) if is_cband else float(sat_deg)
                    
                    transponders.append({
                        "f_v": f_v, "p_r": p_r, "sr": sr, "mod": mod_label, "mux_url": mux_url,
                        "file_label": f"{f_v}{p_r}{sr}",
                        "prov": prov,
                        "pls_val": current_pls, # <--- FIX: STORE THE EXTRACTED VALUE HERE
                        
                        # Indices mapping:
                        # 0:Freq, 1:Pol, 2:SR, 3:Pos, 4:Dir, 5:Inv, 6:FEC, 7:Sys, 8:Mod, 9:RO, 10:Pilot
                        # 11:pids-plps, 12:isi, 13:plsmode-plsvalue, 14:prov, 15:MuxURL
                        "csv_row": [f_v, {"H":"0","V":"1","L":"2","R":"3"}.get(p_r,"0"), sr, f"{hw:.1f}", sat_dir, "2", "9", sys_val, mod_val, "3", "0", "{}", "-1", "{}", prov, mux_url]
                    })
                except Exception as e: 
                    self.log_proc(f"Mux Error ({f_v}): {e}", self.color.CRIMSON)

            self.ui.print_transponder_table(transponders)
            self.log_proc(f"Total Verified T2-MI Frequencies Discovered: {len(transponders)}", self.color.LIME)
            
            # --- FILTERING & VERIFICATION LOOP ---
            valid_transponders = []
            
            for tp in transponders:
                if not self.running: break
                print(f"\n{self.color.TEAL}▶ {self.color.SKY}Drill-Down: {tp['f_v']} {tp['p_r']}{self.color.ENDC}")
                
                # Parse channels (Passing PLS value for filename generation)
                count, found_buckets = self.parse_mux_channels(
                    tp['mux_url'], 
                    os.path.join(c_dir, f"{tp['file_label']}.csv"), 
                    tp['file_label'],
                    tp.get('pls_val', '0,0')
                )
                
                if count > 0:
                    self.total_channels += count
                    
                    verified_parts = []
                    pls_parts = []  # To store the {mode,value} pairs
                    found_isis = set()
                    
                    # Fetch the PLS value we extracted for this specific transponder
                    pls_val_to_use = tp.get("pls_val", "0,0")
                    
                    # Iterate buckets in the order they were found
                    for b_key in found_buckets:
                        m_plp = re.search(r'PLP(\d+)', b_key)
                        m_pid = re.search(r'PID(\d+)', b_key)
                        m_isi = re.search(r'ISI(-?\d+)', b_key)
                        
                        if m_plp and m_pid:
                            pid_val = m_pid.group(1)
                            plp_val = m_plp.group(1)
                            
                            verified_parts.append(f"{pid_val},{plp_val}")
                            
                            # <--- FIX: INJECT THE EXTRACTED PLS INSTEAD OF "0,0"
                            pls_parts.append(pls_val_to_use)
                        
                        if m_isi:
                            isi_val = m_isi.group(1)
                            if isi_val != '-1':
                                found_isis.add(isi_val)
                    
                    # Update Matrix
                    if verified_parts:
                        matrix_str = "{" + ";".join(verified_parts) + "}"
                        tp['csv_row'][11] = matrix_str

                        # Index 13: plsmode-plsvalue {1,242133;1,242133}
                        tp['csv_row'][13] = "{" + ";".join(pls_parts) + "}"
                    
                    # Update ISI List
                    if found_isis:
                        isi_str = ",".join(sorted(list(found_isis), key=int))
                        tp['csv_row'][12] = isi_str
                    
                    valid_transponders.append(tp)
                else:
                    self.log_proc(f"Dropped frequency {tp['f_v']} {tp['p_r']} (0 channels found).", self.color.GOLD)

            self.total_tps += len(valid_transponders)

            # Write CSV with correct 16 columns
            csv_rows = [t['csv_row'] for t in valid_transponders]
            with open(os.path.join(f_dir, f"f{pos_label}.csv"), 'w', newline='', encoding='utf-8') as f:
                w = csv.writer(f)
                w.writerow(["Freq","Pol","SR","Pos","Dir","Inv","FEC","Sys","Mod","RO","Pilot","pids-plps","isi","plsmode-plsvalue","prov","MuxURL"])
                w.writerows(csv_rows)
                
            return pos_label

        except Exception as e:
            self.log_proc(f"Error: {e}", self.color.CRIMSON)
            return ""

    # --------------------------------------------------------------------------
    # [ MAIN ]
    # --------------------------------------------------------------------------

    def run(self) -> None:
        os.system('clear' if os.name == 'posix' else 'cls')
        if input(f"{self.color.GOLD}❓ Enable session logging? (y/n): {self.color.ENDC}").lower() == 'y':
            self.logger = MasterLogger(f"DX_LOG_{datetime.now().strftime('%Y%m%d_%H%M%S')}.log")
            sys.stdout = self.logger
        
        self.print_banner()
        self.print_instructions()
        
        print(f"\n{self.color.SKY}━━━━━━ SOURCE SELECTION ━━━━━━{self.color.ENDC}")
        print(f"  {self.color.GOLD}1{self.color.ENDC}. Load URLs from url.txt\n  {self.color.GOLD}2{self.color.ENDC}. Enter Manually")
        mode = input(f"{self.color.SKY}❓ Mode: {self.color.ENDC}").strip()
        
        urls = []
        if mode == '1':
            urls = self._load_urls_from_file()
            if not urls: self.log_proc("Falling back to manual entry.", self.color.GOLD); urls = [{'url': u, 'pos_label': None} for u in self.collect_urls()]
        else:
            urls = [{'url': u, 'pos_label': None} for u in self.collect_urls()]

        if urls and self.running:
            start = time.time()
            for item in urls:
                if not self.running: break
                self.deep_scan_satellite(item['url'], pre_determined_pos=item.get('pos_label'))
            
            self._print_summary(len(urls), time.time() - start)
        
        self._cleanup()

if __name__ == "__main__":
    app = LyngSatDXMaster()
    app.run()
