import sys
import subprocess
import os
import re

def install_and_import(package):
    try:
        __import__(package)
    except ImportError:
        print(f"Installing {package}...")
        # Bypassing Ubuntu PEP 668 restriction
        subprocess.check_call([sys.executable, "-m", "pip", "install", package, "--break-system-packages"])

# Ensure PySide6 is installed
install_and_import('PySide6')

from PySide6.QtWidgets import QApplication, QFileDialog, QMessageBox
from PySide6.QtCore import Qt

def process_satellite_file():
    # 1. Initialize Qt Application
    app = QApplication(sys.argv)

    # 2. File Dialog with Maximized State
    # In Qt, we create the dialog object first so we can manipulate it
    dialog = QFileDialog()
    dialog.setWindowTitle("Select satellites.xml")
    dialog.setNameFilters(["XML files (*.xml)", "All files (*)"])
    dialog.setFileMode(QFileDialog.ExistingFile)
    
    # Force the dialog to be maximized
    dialog.setWindowState(Qt.WindowMaximized)
    
    if dialog.exec():
        selected_files = dialog.selectedFiles()
        file_path = selected_files[0]
    else:
        return

    # 3. Conversions Mapping (Name updates)
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
        with open(file_path, 'r', encoding='iso-8859-1') as f:
            lines = f.readlines()

        new_lines = []
        skip_block = False
        
        # Position-based Trim Markers
        trim1_start_marker = 'position="-1771"'
        trim1_end_keep_marker = 'position="-451"'
        trim2_start_delete_marker = 'position="1082"'
        trim2_end_keep_marker = '</satellites>'

        for line in lines:
            # Update names
            for item in conversions:
                if f'position="{item["pos"]}"' in line and '<sat' in line:
                    line = re.sub(r'name=".*?"', f'name="{item["new_name"]}"', line)

            # Trimming Logic
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

        # Write output
        output_path = os.path.splitext(file_path)[0] + "_processed.xml"
        with open(output_path, 'w', encoding='iso-8859-1') as f:
            f.writelines(new_lines)

        # Show Success Dialog (also maximized)
        msg = QMessageBox()
        msg.setWindowTitle("Process Complete")
        msg.setText(f"File processed successfully!\n\nSaved as: {output_path}")
        msg.setWindowState(Qt.WindowMaximized)
        msg.exec()

    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    process_satellite_file()
