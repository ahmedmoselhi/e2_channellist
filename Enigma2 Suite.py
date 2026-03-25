import sys
import os
import subprocess
import shutil
import json
import re
import signal
from datetime import datetime

# ==============================================================================
# BOOTSTRAP: PySide6
# ==============================================================================

def check_and_install_dependencies():
    try:
        from PySide6.QtWidgets import QApplication
        return True
    except ImportError:
        print("PySide6 not found. Attempting automatic installation...")
        try:
            subprocess.check_call([sys.executable, "-m", "pip", "install", "PySide6", "--break-system-packages"])
            return True
        except Exception as e:
            print(f"Failed to install PySide6: {e}")
            return False

if not check_and_install_dependencies():
    sys.exit(1)

from PySide6.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout, 
                             QHBoxLayout, QPushButton, QTextEdit, QLabel, 
                             QFileDialog, QMessageBox, QTabWidget, QCheckBox,
                             QLineEdit, QGroupBox, QScrollArea, QDialog)
from PySide6.QtCore import Qt, QSize, QTimer

# ==============================================================================
# CORE LOGIC: LAMEDB PARSER
# ==============================================================================

class LamedbParser:
    """Static logic class for parsing and merging Lamedb files."""
    
    HEADER_PATTERN = re.compile(r"^[0-9a-fA-F]+:[0-9a-fA-F]+:[0-9a-fA-F]+")

    @staticmethod
    def parse_file(filepath):
        transponders = {}
        services = {}
        current_mode = 0  # 0=None, 1=Transponders, 2=Services
        current_header = None
        current_block_lines = []

        def save_block():
            nonlocal current_header, current_block_lines
            if current_header and current_block_lines:
                content = "".join(current_block_lines)
                if current_mode == 1:
                    transponders[current_header] = content
                elif current_mode == 2:
                    lines = content.splitlines()
                    s_name = ""
                    if len(lines) > 1:
                        s_name = lines[1].strip()
                    
                    services[current_header] = {
                        'content': content,
                        'name': s_name
                    }
            current_header = None
            current_block_lines = []

        try:
            with open(filepath, 'r', encoding='utf-8', errors='ignore') as f:
                for line in f:
                    stripped = line.strip()
                    
                    if stripped == "transponders":
                        save_block(); current_mode = 1; continue
                    elif stripped == "services":
                        save_block(); current_mode = 2; continue
                    elif stripped == "end":
                        save_block(); current_mode = 0; continue
                    
                    if stripped == "/":
                        save_block(); continue

                    is_header = (not line.startswith('\t')) and LamedbParser.HEADER_PATTERN.match(stripped)

                    if is_header:
                        save_block()
                        current_header = stripped
                        current_block_lines = [line]
                    elif current_header:
                        current_block_lines.append(line)
            
            save_block()
            return transponders, services
            
        except Exception as e:
            raise Exception(f"Parse Error: {e}")

    @staticmethod
    def merge_data(base_data, source_data, strict_name_check=False):
        merged = base_data.copy()
        new_count = 0
        
        for key, src_val in source_data.items():
            is_duplicate = False
            
            if key in merged:
                if strict_name_check:
                    if merged[key]['name'] == src_val['name']:
                        is_duplicate = True
                else:
                    is_duplicate = True

            if not is_duplicate:
                merged[key] = src_val
                new_count += 1
                
        return merged, new_count

# ==============================================================================
# UI COMPONENT: Lamedb Merger Tab
# ==============================================================================

class LamedbMergerWidget(QWidget):
    def __init__(self, log_filename, parent=None):
        super().__init__(parent)
        self.log_filename = log_filename
        # Use absolute path for config file to ensure it is found reliably
        self.config_file = os.path.join(os.path.dirname(os.path.abspath(__file__)), "enigma2_suite_config.json")
        self.log_buffer = [] 
        self.init_ui()
        self.load_paths()

    def init_ui(self):
        main_layout = QVBoxLayout(self)
        
        # --- File Inputs ---
        self.l_src_edit = QLineEdit()
        self.l_dest_edit = QLineEdit()
        self.l_out_edit = QLineEdit()
        
        # Source Input
        group1 = QVBoxLayout()
        group1.addWidget(QLabel("<b>File 1 (Source):</b>"))
        row1 = QHBoxLayout()
        row1.addWidget(self.l_src_edit)
        btn_src = QPushButton("Browse")
        btn_src.clicked.connect(self.browse_src)
        row1.addWidget(btn_src)
        main_layout.addLayout(group1)
        main_layout.addLayout(row1)

        # Destination Input
        group2 = QVBoxLayout()
        group2.addWidget(QLabel("<b>File 2 (Destination/Base):</b>"))
        row2 = QHBoxLayout()
        row2.addWidget(self.l_dest_edit)
        btn_dest = QPushButton("Browse")
        btn_dest.clicked.connect(self.browse_dest)
        row2.addWidget(btn_dest)
        main_layout.addLayout(group2)
        main_layout.addLayout(row2)

        # Output Input - Explicit creation to capture button reference for disabling
        group3 = QVBoxLayout()
        group3.addWidget(QLabel("<b>Output File:</b>"))
        row3 = QHBoxLayout()
        row3.addWidget(self.l_out_edit)
        self.btn_out_browse = QPushButton("Browse") # Stored as instance variable
        self.btn_out_browse.clicked.connect(self.browse_out)
        row3.addWidget(self.btn_out_browse)
        main_layout.addLayout(group3)
        main_layout.addLayout(row3)

        # --- Options ---
        opts_group = QGroupBox("Merge Options")
        opts_layout = QVBoxLayout(opts_group)
        self.l_strict = QCheckBox("Strict Duplicate Check (ID + Name Match)")
        self.l_sort = QCheckBox("Sort Services Alphabetically (Empty names first)")
        
        # Replace Checkbox
        self.l_replace = QCheckBox("Replace Destination File (Overwrite File 2)")
        self.l_replace.stateChanged.connect(self.on_replace_toggle)
        
        opts_layout.addWidget(self.l_strict)
        opts_layout.addWidget(self.l_sort)
        opts_layout.addWidget(self.l_replace)
        main_layout.addWidget(opts_group)

        # --- Control Buttons ---
        btn_row = QHBoxLayout()
        
        run_btn = QPushButton("🚀 START MERGE")
        run_btn.setFixedHeight(50)
        run_btn.setStyleSheet("font-weight: bold; background-color: #0078D4; color: white;")
        run_btn.clicked.connect(self.run_merge)
        btn_row.addWidget(run_btn)

        log_btn = QPushButton("📜 View Log")
        log_btn.setFixedHeight(50)
        log_btn.clicked.connect(self.show_log_popup)
        btn_row.addWidget(log_btn)

        main_layout.addLayout(btn_row)
        main_layout.addStretch()

    def on_replace_toggle(self, state):
        is_checked = (state == Qt.Checked)
        # Disable both the text field and the browse button
        self.l_out_edit.setEnabled(not is_checked)
        self.btn_out_browse.setEnabled(not is_checked)
        
        if is_checked:
            self.l_out_edit.setText("Will be replaced by Destination File path.")
        else:
            # Restore logic: if dest path exists, put the auto-generated name back
            dest = self.l_dest_edit.text()
            if dest:
                self.update_output_path(dest)
            else:
                self.l_out_edit.clear()

    def log_msg(self, message):
        timestamp = datetime.now().strftime("%H:%M:%S")
        entry = f"[{timestamp}] {message}"
        self.log_buffer.append(entry)
        try:
            with open(self.log_filename, 'a', encoding='utf-8') as f:
                f.write(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] {message}\n")
        except: pass

    def show_log_popup(self):
        dialog = QDialog(self)
        dialog.setWindowTitle("Process Log - Lamedb Merger")
        dialog.resize(600, 400)
        layout = QVBoxLayout(dialog)
        
        log_view = QTextEdit()
        log_view.setReadOnly(True)
        log_view.setStyleSheet("background-color: #1a1a1a; color: #00ff00; font-family: monospace;")
        log_view.setText("\n".join(self.log_buffer))
        layout.addWidget(log_view)
        
        dialog.exec()

    def get_file(self, title, is_save=False):
        dialog = QFileDialog(self)
        dialog.setWindowTitle(title)
        if is_save: dialog.setAcceptMode(QFileDialog.AcceptSave)
        if dialog.exec(): return dialog.selectedFiles()[0]
        return ""

    def browse_src(self):
        f = self.get_file("Select Source Lamedb")
        if f: self.l_src_edit.setText(f)

    def browse_dest(self):
        f = self.get_file("Select Destination Lamedb")
        if f:
            self.l_dest_edit.setText(f)
            if not self.l_replace.isChecked():
                self.update_output_path(f)

    def update_output_path(self, dest_path):
        ts = datetime.now().strftime("%Y%m%d_%H%M%S")
        base_dir = os.path.dirname(dest_path)
        default_name = f"lamedb_merged_{ts}"
        self.l_out_edit.setText(os.path.join(base_dir, default_name))

    def browse_out(self):
        self.l_out_edit.setText(self.get_file("Save Result As", True))

    def _backup_file(self, filepath, prefix):
        if not filepath or not os.path.exists(filepath): return
        backup_dir = os.path.join(os.path.dirname(filepath), "backups")
        try:
            if not os.path.exists(backup_dir): os.makedirs(backup_dir)
            ts = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = os.path.basename(filepath)
            backup_name = f"{filename}_{prefix}_{ts}.bak"
            backup_path = os.path.join(backup_dir, backup_name)
            shutil.copy2(filepath, backup_path)
            self.log_msg(f"Backup created: {backup_name}")
        except Exception as e:
            self.log_msg(f"Warning: Backup failed - {e}")

    def run_merge(self):
        f1 = self.l_src_edit.text()
        f2 = self.l_dest_edit.text()
        
        if self.l_replace.isChecked():
            out = f2
        else:
            out = self.l_out_edit.text()
        
        if not f1 or not f2:
            self.log_msg("Error: Please select Source and Destination files.")
            self.show_log_popup()
            return

        if not out:
            self.log_msg("Error: Output file path is empty.")
            self.show_log_popup()
            return

        self.log_msg("-" * 20)
        self.log_msg("Starting merge process...")
        
        try:
            # 1. Backups
            self._backup_file(f1, "source")
            self._backup_file(f2, "dest")

            # 2. Parsing
            self.log_msg(f"Parsing Source File: {os.path.basename(f1)}...")
            src_t, src_s = LamedbParser.parse_file(f1)
            
            self.log_msg(f"Parsing Destination File: {os.path.basename(f2)}...")
            base_t, base_s = LamedbParser.parse_file(f2)

            # 3. Merging
            mode_str = "Strict (ID + Name)" if self.l_strict.isChecked() else "Standard (ID only)"
            self.log_msg(f"Calculating merge (Mode: {mode_str})...")
            
            merged_t, new_t = LamedbParser.merge_data(base_t, src_t)
            merged_s, new_s = LamedbParser.merge_data(base_s, src_s, self.l_strict.isChecked())
            
            # 4. Calculate Stats
            src_t_count = len(src_t)
            base_t_count = len(base_t)
            merged_t_count = len(merged_t)
            dup_t_count = src_t_count - new_t
            
            src_s_count = len(src_s)
            base_s_count = len(base_s)
            merged_s_count = len(merged_s)
            dup_s_count = src_s_count - new_s

            # 5. Writing
            self.log_msg(f"Writing merged database to: {os.path.basename(out)}")
            with open(out, 'w', encoding='utf-8') as f:
                f.write("eDVB services /4/\ntransponders\n")
                for k in sorted(merged_t.keys()):
                    f.write(merged_t[k])
                    if not merged_t[k].strip().endswith('/'): f.write("/\n")
                f.write("end\nservices\n")
                
                keys = list(merged_s.keys())
                if self.l_sort.isChecked():
                    keys.sort(key=lambda k: (bool(merged_s[k]['name']), merged_s[k]['name'].lower()))
                else: 
                    keys.sort()
                
                for k in keys:
                    lines = merged_s[k]['content'].splitlines()
                    while lines and lines[-1].strip() == '/': lines.pop()
                    for line in lines: f.write(line + "\n")
                f.write("end\n")
            
            # 6. Detailed Summary Report
            self.log_msg("-" * 50)
            self.log_msg("JOB SUMMARY")
            self.log_msg("-" * 50)
            self.log_msg(f"Total Transponders:")
            self.log_msg(f"  Source File      : {src_t_count}")
            self.log_msg(f"  Destination File : {base_t_count}")
            self.log_msg(f"  Merged File      : {merged_t_count}")
            self.log_msg(f"  Duplicates Found : {dup_t_count}")
            self.log_msg("")
            self.log_msg(f"Total Services:")
            self.log_msg(f"  Source File      : {src_s_count}")
            self.log_msg(f"  Destination File : {base_s_count}")
            self.log_msg(f"  Merged File      : {merged_s_count}")
            self.log_msg(f"  Duplicates Found : {dup_s_count}")
            self.log_msg("-" * 50)
            
            if self.l_replace.isChecked():
                self.log_msg("✅ Merge completed successfully! Destination file replaced.")
            else:
                self.log_msg("✅ Merge completed successfully!")
            
            self.save_paths()
            self.show_log_popup() 
            
        except Exception as e:
            self.log_msg(f"❌ Error: {e}")
            self.show_log_popup()

    def load_paths(self):
        if os.path.exists(self.config_file):
            try:
                with open(self.config_file, 'r') as file:
                    d = json.load(file)
                    src = d.get('l_src','')
                    dest = d.get('l_dest','')
                    
                    self.l_src_edit.setText(src)
                    self.l_dest_edit.setText(dest)
                    
                    # Auto-populate output path if dest is loaded and replace is not checked
                    if dest and not self.l_replace.isChecked():
                        self.update_output_path(dest)
                        
            except Exception as e:
                print(f"Error loading config: {e}")

    def save_paths(self):
        try:
            with open(self.config_file, 'w') as file:
                json.dump({'l_src': self.l_src_edit.text(), 'l_dest': self.l_dest_edit.text()}, file)
        except: pass

# ==============================================================================
# UI COMPONENT: Satellites.xml Processor Tab
# ==============================================================================

class SatellitesProcessorWidget(QWidget):
    def __init__(self, log_filename, parent=None):
        super().__init__(parent)
        self.log_filename = log_filename
        self.log_buffer = []
        self.init_ui()

    def init_ui(self):
        layout = QVBoxLayout(self)
        
        layout.addWidget(QLabel("<b>Select satellites.xml</b>"))
        self.s_input_edit = QLineEdit()
        row = QHBoxLayout()
        row.addWidget(self.s_input_edit)
        btn = QPushButton("Browse")
        btn.clicked.connect(self.browse_file)
        row.addWidget(btn)
        layout.addLayout(row)

        # Replace Checkbox
        self.s_replace = QCheckBox("Replace Original File (Backup before overwrite)")
        layout.addWidget(self.s_replace)

        # --- Control Buttons ---
        btn_row = QHBoxLayout()
        
        run_btn = QPushButton("🛠️ PROCESS SATELLITES.XML")
        run_btn.setFixedHeight(50)
        run_btn.clicked.connect(self.run_process)
        btn_row.addWidget(run_btn)

        log_btn = QPushButton("📜 View Log")
        log_btn.setFixedHeight(50)
        log_btn.clicked.connect(self.show_log_popup)
        btn_row.addWidget(log_btn)
        
        layout.addLayout(btn_row)
        layout.addStretch()

    def log_msg(self, message):
        timestamp = datetime.now().strftime("%H:%M:%S")
        entry = f"[{timestamp}] {message}"
        self.log_buffer.append(entry)
        try:
            with open(self.log_filename, 'a', encoding='utf-8') as f:
                f.write(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] {message}\n")
        except: pass

    def show_log_popup(self):
        dialog = QDialog(self)
        dialog.setWindowTitle("Process Log - Satellites.xml")
        dialog.resize(600, 400)
        layout = QVBoxLayout(dialog)
        
        log_view = QTextEdit()
        log_view.setReadOnly(True)
        log_view.setStyleSheet("background-color: #1a1a1a; color: #00ccff; font-family: monospace;")
        log_view.setText("\n".join(self.log_buffer))
        layout.addWidget(log_view)
        
        dialog.exec()

    def browse_file(self):
        dialog = QFileDialog(self)
        dialog.setWindowTitle("Select satellites.xml")
        if dialog.exec():
            self.s_input_edit.setText(dialog.selectedFiles()[0])

    def _backup_file(self, filepath, prefix):
        if not filepath or not os.path.exists(filepath): return
        backup_dir = os.path.join(os.path.dirname(filepath), "backups")
        try:
            if not os.path.exists(backup_dir): os.makedirs(backup_dir)
            ts = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = os.path.basename(filepath)
            backup_name = f"{filename}_{prefix}_{ts}.bak"
            backup_path = os.path.join(backup_dir, backup_name)
            shutil.copy2(filepath, backup_path)
            self.log_msg(f"Backup created: {backup_name}")
        except Exception as e:
            self.log_msg(f"Warning: Backup failed - {e}")

    def run_process(self):
        file_path = self.s_input_edit.text()
        if not file_path:
            self.log_msg("Error: No file selected.")
            self.show_log_popup()
            return
        
        self.log_msg("Processing satellites.xml...")
        
        # --- Full Conversion List ---
        conversions = [
            {"pos": "-345", "new_name": "(55) 34.5W Intelsat 35e"},
            {"pos": "-300", "new_name": "(54) 30.0W Hispasat 30W-5/30W-6"},
            {"pos": "-245", "new_name": "(52) 24.5W Alcomsat 1"},
            {"pos": "-220", "new_name": "(48) 22.0W SES 4"},
            {"pos": "-150", "new_name": "(50) 15.0W Telstar 12 Vantage"},
            {"pos": "-140", "new_name": "(47) 14.0W Express AM8"},
            {"pos": "-80", "new_name": "(44) 8.0W Eutelsat 8 West B"},
            {"pos": "-70", "new_name": "(43) 7.0W Nilesat 201/301 : Eutelsat 7 West A"},
            {"pos": "-50", "new_name": "(42) 5.0W Eutelsat 5 West B"},
            {"pos": "-40", "new_name": "(41) 4.0W Amos 3 : Dror 1"},
            {"pos": "-30", "new_name": "(40) 3.0W ABS 3A"},
            {"pos": "-8", "new_name": "(39) 0.8W Thor 5/6/7 : Intelsat 10-02"},
            {"pos": "19", "new_name": "(38) 1.9E BulgariaSat 1"},
            {"pos": "30", "new_name": "(37) 3.0E Eutelsat 3B : Rascom QAF 1R"},
            {"pos": "48", "new_name": "(36) 4.8E Astra 4A : SES 5"},
            {"pos": "70", "new_name": "(35) 7.0E Eutelsat 7B/7C"},
            {"pos": "90", "new_name": "(34) 9.0E Eutelsat 9B : Ka-Sat 9A"},
            {"pos": "100", "new_name": "(33) 10.0E Eutelsat 10B"},
            {"pos": "130", "new_name": "(32) 13.0E Hotbird 13F/13G"},
            {"pos": "160", "new_name": "(31) 16.0E Eutelsat 16A"},
            {"pos": "170", "new_name": "17.0E Amos 17"},
            {"pos": "192", "new_name": "(1) 19.2E Astra 1KR/1M/1N/1P"},
            {"pos": "215", "new_name": "(2) 21.5E Eutelsat 21B"},
            {"pos": "235", "new_name": "(3) 23.5E Astra 3B/3C"},
            {"pos": "255", "new_name": "(4) 25.5E Es'hail 1"},
            {"pos": "260", "new_name": "(5) 26.0E Badr 7/8 : Es'hail 2"},
            {"pos": "282", "new_name": "(6) 28.2E Astra 2E/2F/2G"},
            {"pos": "305", "new_name": "30.5E Arabsat 5A/6A"},
            {"pos": "310", "new_name": "(7) 31.0E Türksat 5A"},
            {"pos": "360", "new_name": "(10) 36.0E Eutelsat 36D : Express AMU1"},
            {"pos": "381", "new_name": "38.1E Paksat 1R/MM1"},
            {"pos": "390", "new_name": "(11) 39.0E Hellas Sat 3/4"},
            {"pos": "400", "new_name": "40.0E Express AM7"},
            {"pos": "420", "new_name": "(12) 42.0E Türksat 3A/4A/5B/6A"},
            {"pos": "425", "new_name": "42.5E NigComSat 1R"},
            {"pos": "450", "new_name": "(13) 45.0E Azerspace 2/Intelsat 38"},
            {"pos": "460", "new_name": "(14) 46.0E Azerspace 1"},
            {"pos": "500", "new_name": "(15) 50.0E Türksat 4B"},
            {"pos": "515", "new_name": "(17) 51.5E Belintersat 1"},
            {"pos": "520", "new_name": "(18) 52.0E TurkmenÄlem/MonacoSat"},
            {"pos": "525", "new_name": "(19) 52.5E Al Yah 1"},
            {"pos": "530", "new_name": "(20) 53.0E Express AM6"},
            {"pos": "549", "new_name": "(21) 54.9E G-Sat 16 : Yamal 402"},
            {"pos": "570", "new_name": "57.0E NSS 12"},
            {"pos": "585", "new_name": "58.5E KazSat 3"},
            {"pos": "620", "new_name": "(25) 62.0E Intelsat 39"},
            {"pos": "650", "new_name": "65.0E Amos 4"},
            {"pos": "660", "new_name": "(26) 66.0E Intelsat 17"},
            {"pos": "685", "new_name": "(27) 68.5E Intelsat 20/36"},
            {"pos": "705", "new_name": "(28) 70.5E Eutelsat 70B"},
            {"pos": "750", "new_name": "(29) 75.0E ABS 2/2A"},
            {"pos": "765", "new_name": "76.5E Apstar 7"},
            {"pos": "785", "new_name": "78.5E Thaicom 6/8"},
            {"pos": "800", "new_name": "(30) 80.0E Express 80"},
            {"pos": "830", "new_name": "83.0E G-Sat 10/24/30"},
            {"pos": "865", "new_name": "86.5E KazSat 2"},
            {"pos": "880", "new_name": "88.0E ST 2"},
            {"pos": "900", "new_name": "90.0E Yamal 401"}
        ]

        try:
            if self.s_replace.isChecked():
                 self._backup_file(file_path, "pre_replace")

            with open(file_path, 'r', encoding='iso-8859-1') as f:
                lines = f.readlines()

            new_lines = []
            skip_block = False
            rename_count = 0
            
            # --- Trimming Logic Restored ---
            trim1_start_marker = 'position="-1771"'
            trim1_end_keep_marker = 'position="-451"'
            trim2_start_delete_marker = 'position="1082"'
            trim2_end_keep_marker = '</satellites>'

            for line in lines:
                # 1. XML HEADER TRANSFORMATION
                # Replaces UTF-8 with iso-8859-1 to match our file encoding
                if '<?xml' in line and 'encoding="UTF-8"' in line:
                    line = line.replace('encoding="UTF-8"', 'encoding="iso-8859-1"')
                    header_updated = True

                # 2. Renaming Logic
                if '<sat' in line:
                    for item in conversions:
                        if f'position="{item["pos"]}"' in line:
                            new_line = re.sub(r'name=".*?"', f'name="{item["new_name"]}"', line)
                            if new_line != line:
                                rename_count += 1
                                line = new_line
                            break

                # 2. Trimming Logic
                # This logic removes satellites outside the desired range
                if trim1_start_marker in line and '<sat' in line:
                    skip_block = True
                if trim1_end_keep_marker in line and '<sat' in line:
                    skip_block = False
                if trim2_start_delete_marker in line and '<sat' in line:
                    skip_block = True
                if trim2_end_keep_marker in line:
                    skip_block = False

                if not skip_block:
                    new_lines.append(line)

            # Determine output path
            if self.s_replace.isChecked():
                output_path = file_path
            else:
                output_path = os.path.splitext(file_path)[0] + "_processed.xml"

            with open(output_path, 'w', encoding='iso-8859-1') as f:
                f.writelines(new_lines)

            self.log_msg(f"✅ Process Complete. Renamed {rename_count} satellites.")
            if self.s_replace.isChecked():
                self.log_msg(f"Original file replaced: {file_path}")
            else:
                self.log_msg(f"Saved to: {output_path}")
            self.show_log_popup()

        except Exception as e:
            self.log_msg(f"❌ Error: {e}")
            self.show_log_popup()

# ==============================================================================
# MAIN APPLICATION WINDOW
# ==============================================================================

class Enigma2Suite(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Enigma2 Suite v21.0 - Logic Restored")
        self.setMinimumSize(QSize(850, 600))
        self.setWindowState(Qt.WindowMaximized)
        
        # Global Log Filename
        ts = datetime.now().strftime("%Y%m%d_%H%M%S")
        self.log_filename = f"enigma2_suite_{ts}.log"
        
        self.init_ui()
        
        # Handle Ctrl+C Gracefully
        signal.signal(signal.SIGINT, self.handle_interrupt)
        # Timer needed to allow Python to check for signals during Qt event loop
        self.timer = QTimer()
        self.timer.start(100)
        self.timer.timeout.connect(self.check_interrupt)

    def check_interrupt(self):
        pass

    def handle_interrupt(self, signum, frame):
        print("\nInterrupt received. Closing application...")
        self.close()
        QApplication.quit()

    def init_ui(self):
        central = QWidget()
        self.setCentralWidget(central)
        main_layout = QVBoxLayout(central)

        self.tabs = QTabWidget()
        main_layout.addWidget(self.tabs)

        # Add Modular Widgets as Tabs
        self.tabs.addTab(LamedbMergerWidget(self.log_filename), "Lamedb Merger")
        self.tabs.addTab(SatellitesProcessorWidget(self.log_filename), "Satellites.xml Processor")

if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = Enigma2Suite()
    window.show()
    sys.exit(app.exec())
