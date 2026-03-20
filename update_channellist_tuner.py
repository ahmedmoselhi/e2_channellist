import urllib.request
import os
import sys
import zipfile
import time
import shutil
from datetime import datetime

# --- CONFIGURATION ---
SETTINGS_FILE = '/etc/enigma2/settings'
ENIGMA2_PATH = '/etc/enigma2/'
TUXBOX_PATH = '/etc/tuxbox/'
ASTRA_CONF_PATH = '/etc/astra/'
# Centralized backup directory
BACKUP_DIR = '/etc/enigma2/backups/'

# File definitions
LAMEDB_PATH = '/etc/enigma2/lamedb'
ASTRA_FILE_PATH = '/etc/astra/astra.conf'

CHANNELS_URL = 'https://github.com/ahmedmoselhi/e2_channellist/archive/refs/heads/master.zip'
TUNER_URL = 'https://github.com/ahmedmoselhi/e2_channellist/raw/refs/heads/tuner/tuner_backup.txt'
ASTRA_URL = 'https://raw.githubusercontent.com/ahmedmoselhi/e2_channellist/refs/heads/astra/astra.conf'

# --- HELPER FUNCTIONS ---

def print_banner(title):
    """
    Draws a formatted ASCII box around the title.
    """
    width = 50
    padding = width - 2 - len(title)
    left_pad = padding // 2
    right_pad = padding - left_pad
    
    print("\n" + "╔" + "═" * (width - 2) + "╗")
    print("║" + " " * left_pad + title + " " * right_pad + "║")
    print("╚" + "═" * (width - 2) + "╝")

def backup_file(filepath):
    """
    [HELPER] Automatically backs up a file if it exists.
    Saves to BACKUP_DIR with a timestamp.
    """
    if not os.path.exists(filepath):
        return

    try:
        # Create backup directory if it doesn't exist
        if not os.path.exists(BACKUP_DIR):
            os.makedirs(BACKUP_DIR)
            print("-> Created backup directory: {0}".format(BACKUP_DIR))

        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = os.path.basename(filepath)
        backup_name = "{0}_{1}".format(filename, timestamp)
        target_path = os.path.join(BACKUP_DIR, backup_name)
        
        shutil.copy2(filepath, target_path)
        print("-> [AUTO-BACKUP] Saved: {0}".format(backup_name))
        
    except Exception as e:
        print("-> [WARNING] Backup failed for {0}: {1}".format(filename, str(e)))

def stop_enigma2():
    """
    [HELPER] Stops the Enigma2 GUI process (init 4).
    """
    print("\n[!] CRITICAL: Stopping Enigma2 (init 4)...")
    os.system('init 4')
    time.sleep(5)

def start_enigma2():
    """
    [HELPER] Restarts the Enigma2 GUI (init 3).
    """
    print("\n[*] SUCCESS: Restarting Enigma2 (init 3)...")
    os.system('init 3')

# --- TASK FUNCTIONS ---

def download_astra_conf():
    """
    [TASK] Update Astra Configuration.
    Automatically backs up existing config before replacement.
    """
    print_banner("ASTRA CONFIGURATION UPDATE")

    try:
        # Auto-Backup existing file
        backup_file(ASTRA_FILE_PATH)

        if not os.path.exists(ASTRA_CONF_PATH):
            print("-> Creating directory {0}...".format(ASTRA_CONF_PATH))
            os.makedirs(ASTRA_CONF_PATH)

        print("-> Downloading astra.conf from GitHub...")
        urllib.request.urlretrieve(ASTRA_URL, ASTRA_FILE_PATH)

        os.chmod(ASTRA_FILE_PATH, 0o644)

        print("\n[✔] ASTRA CONFIGURATION UPDATED SUCCESSFULLY")
    except Exception as e:
        print("\n[✘] ERROR: Astra update failed -> {0}".format(str(e)))

def download_and_extract_channels():
    """
    [TASK] Update Channel List & Satellites.
    Automatically backs up lamedb before replacement.
    """
    tmp_zip = '/tmp/channels.zip'
    extract_to = '/tmp/channels_extracted'
    sat_xml_src = os.path.join(ENIGMA2_PATH, 'satellites.xml')
    sat_xml_dst = os.path.join(TUXBOX_PATH, 'satellites.xml')

    print_banner("CHANNEL LIST UPDATE PROCESS")

    stop_enigma2()
    
    try:
        # Auto-Backup lamedb
        backup_file(LAMEDB_PATH)

        print("-> Downloading latest channel database...")
        urllib.request.urlretrieve(CHANNELS_URL, tmp_zip)

        if os.path.exists(extract_to):
            shutil.rmtree(extract_to)
        
        with zipfile.ZipFile(tmp_zip, 'r') as zip_ref:
            zip_ref.extractall(extract_to)

        subfolders = [f for f in os.listdir(extract_to) if os.path.isdir(os.path.join(extract_to, f))]
        
        if subfolders:
            source_path = os.path.join(extract_to, subfolders[0])
            print("-> Synchronizing bouquet and service files...")
            for item in os.listdir(source_path):
                s, d = os.path.join(source_path, item), os.path.join(ENIGMA2_PATH, item)
                if os.path.isdir(s):
                    if os.path.exists(d):
                        shutil.rmtree(d)
                    shutil.copytree(s, d)
                else:
                    shutil.copy2(s, d)

            if os.path.exists(sat_xml_src):
                print("-> Mirroring satellites.xml to system folder...")
                shutil.copy2(sat_xml_src, sat_xml_dst)

        print("\n[✔] CHANNEL UPDATE COMPLETE")

    except Exception as e:
        print("\n[✘] ERROR: Update failed -> {0}".format(str(e)))
    
    finally:
        start_enigma2()

def update_tuner_settings():
    """
    [TASK] Advanced Tuner Configuration.
    Automatically backs up settings file before modification.
    """
    if not os.path.exists(SETTINGS_FILE):
        return

    print_banner("TUNER HARDWARE CONFIGURATION")

    choice = input("\n[?] Select Target Tuner [0: Tuner A | 1: Tuner B]: ").strip()
    if choice not in ['0', '1']:
        return

    other_tuner = '1' if choice == '0' else '0'

    print("\n[?] Select Firmware Logic:")
    print(" (1) OpenATV - Uses full '.dvbs.' tagging.")
    print(" (2) OpenPLi - Uses stripped path syntax.")
    fmt_choice = input("Choice [1/2]: ").strip()

    stop_enigma2()
    
    # UPDATED: Use the centralized backup function with timestamp
    backup_file(SETTINGS_FILE)

    try:
        print("-> Pulling source data from GitHub...")
        req = urllib.request.Request(TUNER_URL)
        with urllib.request.urlopen(req) as response:
            raw_content = response.read().decode('utf-8').splitlines()

        active_block = [
            "config.Nims.{0}.configMode=advanced".format(choice),
            "config.Nims.{0}.dvbs.configMode=advanced".format(choice)
        ]

        for line in raw_content:
            line = line.strip()
            if line.startswith('config.Nims.'):
                if '.advanced.' in line:
                    parts = line.split('.')
                    parts[2] = choice
                    entry = ".".join(parts)
                    if fmt_choice == '2':
                        entry = entry.replace('.dvbs.', '.').replace('.dvbs=', '=')
                    active_block.append(entry)

        inactive_block = [
            "config.Nims.{0}.dvbs.configMode=nothing".format(other_tuner)]

        with open(SETTINGS_FILE, 'r') as f:
            all_lines = [l.strip() for l in f.readlines()]
        clean_base = [l for l in all_lines if not l.startswith('config.Nims.')]

        with open(SETTINGS_FILE, 'w') as f:
            for line in clean_base:
                f.write(line + '\n')
            for line in active_block:
                f.write(line + '\n')
            for line in inactive_block:
                f.write(line + '\n')

        print(
            "\n[✔] TUNER {0} RECONFIGURED SUCCESSFULLY".format(
                "A" if choice == "0" else "B"))
    
    except Exception as e:
        print("\n[✘] ERROR: Tuner setup failed -> {0}".format(str(e)))

    finally:
        start_enigma2()

def main():
    print("\n" + "★" * 50)
    print("   _____       _                       ___  ")
    print("  |   __|___ _| |___ _ _ ___ ___ ___  |_  | ")
    print("  |   __|   | . | . | | |  _| .'|_ -|  _| |_")
    print("  |_____|_|_|___|_  |___|_| |__,|___| |_____|")
    print("                |___|  ULTIMATE UTILITY v6.4 ")
    print("★" * 50)

    print("\n[1] FULL CHANNEL UPDATE")
    print("    • Description: Downloads latest satellite & bouquet ZIP.")
    print("    • Auto-Backup: lamedb")

    print("\n[2] ADVANCED TUNER SETUP")
    print("    • Description: Injects LNB/Diseqc settings for your motor.")
    print("    • Auto-Backup: settings")

    print("\n[3] ASTRA CONFIGURATION")
    print("    • Description: Downloads astra.conf to /etc/astra/.") 
    print("    • Auto-Backup: astra.conf")

    print("\n[4] TOTAL SYSTEM REFRESH")
    print("    • Description: Performs Option 1, 2, and 3.")

    print("\n[5] EXIT")
    print("═" * 50)

    menu_choice = input("\n[?] Choose an action: ").strip()
    if menu_choice == '1':
        download_and_extract_channels()
    elif menu_choice == '2':
        update_tuner_settings()
    elif menu_choice == '3':
        download_astra_conf()
    elif menu_choice == '4':
        download_and_extract_channels()
        update_tuner_settings()
        download_astra_conf()
    else:
        sys.exit()

if __name__ == "__main__":
    main()
