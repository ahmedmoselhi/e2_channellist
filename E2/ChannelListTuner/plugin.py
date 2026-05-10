# -*- coding: utf-8 -*-
import os
import sys
import zipfile
import time
import shutil
import argparse
from datetime import datetime

try:
    from Plugins.Plugin import PluginDescriptor
    from Screens.ChoiceBox import ChoiceBox
except ImportError:
    PluginDescriptor = None
    ChoiceBox = None


# --- PYTHON 2/3 COMPATIBILITY ---
try:
    # Python 3
    import urllib.request
    urlretrieve = urllib.request.urlretrieve
    urlopen = urllib.request.urlopen
    Request = urllib.request.Request
except ImportError:
    # Python 2
    import urllib2
    import urllib
    urlretrieve = urllib.urlretrieve
    urlopen = urllib2.urlopen
    Request = urllib2.Request

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
    print("\n[!] CRITICAL: Stopping Enigma2 (init 4)...")
    os.system('init 4')
    time.sleep(5)

def start_enigma2():
    print("\n[*] SUCCESS: Restarting Enigma2 (init 3)...")
    os.system('init 3')

def verify_file_integrity(filepath, is_zip=False):
    """
    [HELPER] Verifies a file exists and is not empty.
    If is_zip=True, also validates ZIP header.
    """
    if not os.path.exists(filepath):
        raise IOError("File not created: {0}".format(filepath))
    
    if os.path.getsize(filepath) == 0:
        os.remove(filepath) 
        raise IOError("Downloaded file is empty (possible network error): {0}".format(filepath))
    
    if is_zip:
        if not zipfile.is_zipfile(filepath):
            os.remove(filepath)
            raise IOError("Downloaded file is not a valid ZIP archive.")
    
    print("-> [VERIFY] File integrity check passed.")
    return True

# --- TASK FUNCTIONS ---

def export_tuner_config():
    """
    [TASK] Backup current tuner configuration to tuner_backup.txt.
    Extracts lines starting with 'config.Nims.' from settings.
    """
    print_banner("TUNER CONFIGURATION BACKUP")

    if not os.path.exists(SETTINGS_FILE):
        print("-> [ERROR] Settings file not found at {0}".format(SETTINGS_FILE))
        return

    # Ensure backup directory exists
    if not os.path.exists(BACKUP_DIR):
        os.makedirs(BACKUP_DIR)

    target_file = os.path.join(BACKUP_DIR, 'tuner_backup.txt')
    tmp_file = target_file + ".tmp"
    
    try:
        tuner_lines = []
        with open(SETTINGS_FILE, 'r') as f:
            for line in f:
                # Capture only tuner configuration lines
                if line.strip().startswith('config.Nims.'):
                    tuner_lines.append(line.strip())
        
        if not tuner_lines:
            print("-> [INFO] No tuner configuration data found in settings file.")
            return

        # Atomic Write
        with open(tmp_file, 'w') as f:
            for line in tuner_lines:
                f.write(line + '\n')
        
        # Verify write before moving (Removed redundant os.remove)
        shutil.move(tmp_file, target_file)

        print("-> [SUCCESS] Exported {0} tuner lines to:".format(len(tuner_lines)))
        print("   {0}".format(target_file))

    except Exception as e:
        print("-> [ERROR] Backup failed: {0}".format(str(e)))
        if os.path.exists(tmp_file): os.remove(tmp_file)

def download_astra_conf():
    """
    [TASK] Update Astra Configuration.
    """
    print_banner("ASTRA CONFIGURATION UPDATE")

    tmp_file = ASTRA_FILE_PATH + ".tmp"

    try:
        backup_file(ASTRA_FILE_PATH)

        if not os.path.exists(ASTRA_CONF_PATH):
            print("-> Creating directory {0}...".format(ASTRA_CONF_PATH))
            os.makedirs(ASTRA_CONF_PATH)

        print("-> Downloading astra.conf from GitHub...")
        urlretrieve(ASTRA_URL, tmp_file)

        verify_file_integrity(tmp_file)
        shutil.move(tmp_file, ASTRA_FILE_PATH)
        
        os.chmod(ASTRA_FILE_PATH, 0o644)

        print("\n[✔] ASTRA CONFIGURATION UPDATED SUCCESSFULLY")
    except Exception as e:
        print("\n[✘] ERROR: Astra update failed -> {0}".format(str(e)))
        if os.path.exists(tmp_file): os.remove(tmp_file)

def download_and_extract_channels(manage_e2_state=True):
    """
    [TASK] Update Channel List & Satellites.
    """
    tmp_zip = '/tmp/channels.zip'
    extract_to = '/tmp/channels_extracted'
    sat_xml_src = os.path.join(ENIGMA2_PATH, 'satellites.xml')
    sat_xml_dst = os.path.join(TUXBOX_PATH, 'satellites.xml')

    print_banner("CHANNEL LIST UPDATE PROCESS")

    if manage_e2_state:
        stop_enigma2()
    
    try:
        backup_file(LAMEDB_PATH)

        print("-> Downloading latest channel database...")
        urlretrieve(CHANNELS_URL, tmp_zip)

        verify_file_integrity(tmp_zip, is_zip=True)

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
        if manage_e2_state:
            start_enigma2()

def update_tuner_settings(tuner_target=None, firmware_logic=None, manage_e2_state=True):
    """
    [TASK] Advanced Tuner Configuration (Restore/Inject).
    Accepts arguments to bypass prompts during parameterised runs.
    """
    if not os.path.exists(SETTINGS_FILE):
        return

    print_banner("TUNER HARDWARE CONFIGURATION")

    get_input = raw_input if sys.version_info[0] == 2 else input

    if tuner_target is not None:
        choice = str(tuner_target)
    else:
        choice = get_input("\n[?] Select Target Tuner [0: Tuner A | 1: Tuner B]: ").strip()
    
    if choice not in ['0', '1']:
        print("-> [ERROR] Invalid tuner choice. Aborting.")
        return

    other_tuner = '1' if choice == '0' else '0'

    if firmware_logic is not None:
        fmt_choice = str(firmware_logic)
    else:
        print("\n[?] Select Firmware Logic:")
        print(" (1) OpenATV - Uses full '.dvbs.' tagging.")
        print(" (2) OpenPLi - Uses stripped path syntax.")
        
        fmt_choice = get_input("Choice [1/2]: ").strip()

    if fmt_choice not in ['1', '2']:
        print("-> [ERROR] Invalid firmware logic choice. Aborting.")
        return

    if manage_e2_state:
        stop_enigma2()
    
    backup_file(SETTINGS_FILE)

    tmp_settings = SETTINGS_FILE + ".tmp"

    try:
        print("-> Pulling source data from GitHub...")
        req = Request(TUNER_URL)
        
        # Python 2 backward compatibility fix for urlopen context manager
        response = urlopen(req)
        try:
            raw_content = response.read().decode('utf-8').splitlines()
        finally:
            response.close()

        if not raw_content:
            raise ValueError("Tuner configuration source is empty.")

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
            
        # Target specific tuner removal to avoid deleting completely unrelated tuners (e.g. Tuner C)
        clean_base = [l for l in all_lines if not (l.startswith('config.Nims.{0}.'.format(choice)) or l.startswith('config.Nims.{0}.'.format(other_tuner)))]

        print("-> Writing configuration atomically...")
        with open(tmp_settings, 'w') as f:
            for line in clean_base:
                f.write(line + '\n')
            for line in active_block:
                f.write(line + '\n')
            for line in inactive_block:
                f.write(line + '\n')
        
        if os.path.getsize(tmp_settings) == 0:
            raise IOError("Generated settings file is empty. Aborting to prevent data loss.")

        shutil.move(tmp_settings, SETTINGS_FILE)

        print(
            "\n[✔] TUNER {0} RECONFIGURED SUCCESSFULLY".format(
                "A" if choice == "0" else "B"))
    
    except Exception as e:
        print("\n[✘] ERROR: Tuner setup failed -> {0}".format(str(e)))
        if os.path.exists(tmp_settings):
            os.remove(tmp_settings)

    finally:
        if manage_e2_state:
            start_enigma2()

def run_interactive_menu():
    """
    Renders the interactive menu and handles user input.
    """
    print("\n" + "★" * 50)
    print("   _____       _                       ___  ")
    print("  |   __|___ _| |___ _ _ ___ ___ ___  |_  | ")
    print("  |   __|   | . | . | | |  _| .'|_ -|  _| |_")
    print("  |_____|_|_|___|_  |___|_| |__,|___| |_____|")
    print("                |___|  ULTIMATE UTILITY v6.6 ")
    print("★" * 50)

    print("\n[1] FULL CHANNEL UPDATE")
    print("    • Description: Downloads latest satellite & bouquet ZIP.")
    print("    • Auto-Backup: lamedb")

    print("\n[2] BACKUP TUNER CONFIGURATION")
    print("    • Description: Saves current tuner settings to tuner_backup.txt.")
    print("    • Target: /etc/enigma2/backups/")

    print("\n[3] ADVANCED TUNER SETUP")
    print("    • Description: Injects LNB/Diseqc settings for your motor.")
    print("    • Auto-Backup: settings")

    print("\n[4] ASTRA CONFIGURATION")
    print("    • Description: Downloads astra.conf to /etc/astra/.") 
    print("    • Auto-Backup: astra.conf")

    print("\n[5] TOTAL SYSTEM REFRESH")
    print("    • Description: Performs Option 1, 3, and 4.")

    print("\n[6] EXIT")
    print("═" * 50)

    get_input = raw_input if sys.version_info[0] == 2 else input
    
    menu_choice = get_input("\n[?] Choose an action: ").strip()
    if menu_choice == '1':
        download_and_extract_channels()
    elif menu_choice == '2':
        export_tuner_config()
    elif menu_choice == '3':
        update_tuner_settings()
    elif menu_choice == '4':
        download_astra_conf()
    elif menu_choice == '5':
        stop_enigma2()
        download_and_extract_channels(manage_e2_state=False)
        update_tuner_settings(manage_e2_state=False)
        download_astra_conf()
        start_enigma2()
    else:
        sys.exit()

def main():
    # Setup argparse for command line functionality
    parser = argparse.ArgumentParser(
        description="Ultimate Utility v6.6 - Enigma2 Management Tool",
        epilog="""
Examples of Parameterised Usage:
  python update_channellist_tuner.py -c                         # Run Full Channel Update only
  python update_channellist_tuner.py -b                         # Backup Tuner Configuration
  python update_channellist_tuner.py -t --tuner-target 0 --firmware-logic 1 # Advanced setup for Tuner A on OpenATV
  python update_channellist_tuner.py -a                         # Astra Configuration update
  python update_channellist_tuner.py --all --tuner-target 1 --firmware-logic 2 # Total System Refresh specifying Tuner B and OpenPLi
        """,
        formatter_class=argparse.RawTextHelpFormatter
    )

    parser.add_argument('-c', '--channels', action='store_true', help='Execute Full Channel Update')
    parser.add_argument('-b', '--backup', action='store_true', help='Backup Tuner Configuration')
    parser.add_argument('-t', '--tuner', action='store_true', help='Execute Advanced Tuner Setup')
    parser.add_argument('--tuner-target', choices=['0', '1'], help='Target Tuner [0: Tuner A | 1: Tuner B]')
    parser.add_argument('--firmware-logic', choices=['1', '2'], help='Firmware Logic [1: OpenATV | 2: OpenPLi]')
    parser.add_argument('-a', '--astra', action='store_true', help='Execute Astra Configuration Update')
    parser.add_argument('--all', action='store_true', help='Execute Total System Refresh (Channels, Tuner, Astra)')

    # If no arguments are passed, fall back to interactive menu
    if len(sys.argv) == 1:
        run_interactive_menu()
    else:
        args = parser.parse_args()

        # Enforce required secondary arguments if tuner setup is triggered in parameter mode
        if args.all or args.tuner:
            if not args.tuner_target or not args.firmware_logic:
                parser.error("Advanced Tuner Setup (--tuner or --all) requires --tuner-target and --firmware-logic to be specified.")

        if args.all:
            stop_enigma2()
            download_and_extract_channels(manage_e2_state=False)
            update_tuner_settings(tuner_target=args.tuner_target, firmware_logic=args.firmware_logic, manage_e2_state=False)
            download_astra_conf()
            start_enigma2()
        else:
            if args.channels:
                download_and_extract_channels()
            if args.backup:
                export_tuner_config()
            if args.tuner:
                update_tuner_settings(tuner_target=args.tuner_target, firmware_logic=args.firmware_logic)
            if args.astra:
                download_astra_conf()

def _run_selected_action(session, selection):
    if not selection:
        return

    choice = selection[1]
    if choice == 'channels':
        download_and_extract_channels()
    elif choice == 'backup':
        export_tuner_config()
    elif choice == 'tuner_a_openatv':
        update_tuner_settings(tuner_target='0', firmware_logic='1')
    elif choice == 'tuner_b_openatv':
        update_tuner_settings(tuner_target='1', firmware_logic='1')
    elif choice == 'tuner_a_openpli':
        update_tuner_settings(tuner_target='0', firmware_logic='2')
    elif choice == 'tuner_b_openpli':
        update_tuner_settings(tuner_target='1', firmware_logic='2')
    elif choice == 'astra':
        download_astra_conf()
    elif choice == 'refresh_a_openatv':
        stop_enigma2()
        download_and_extract_channels(manage_e2_state=False)
        update_tuner_settings(tuner_target='0', firmware_logic='1', manage_e2_state=False)
        download_astra_conf()
        start_enigma2()
    elif choice == 'refresh_b_openatv':
        stop_enigma2()
        download_and_extract_channels(manage_e2_state=False)
        update_tuner_settings(tuner_target='1', firmware_logic='1', manage_e2_state=False)
        download_astra_conf()
        start_enigma2()


def main_plugin(session, **kwargs):
    if ChoiceBox is None:
        main()
        return

    choices = [
        ("Full Channel Update", 'channels'),
        ("Backup Tuner Configuration", 'backup'),
        ("Advanced Tuner Setup: A/OpenATV", 'tuner_a_openatv'),
        ("Advanced Tuner Setup: B/OpenATV", 'tuner_b_openatv'),
        ("Advanced Tuner Setup: A/OpenPLi", 'tuner_a_openpli'),
        ("Advanced Tuner Setup: B/OpenPLi", 'tuner_b_openpli'),
        ("Astra Configuration Update", 'astra'),
        ("Total Refresh: A/OpenATV", 'refresh_a_openatv'),
        ("Total Refresh: B/OpenATV", 'refresh_b_openatv'),
    ]

    session.openWithCallback(
        lambda selection: _run_selected_action(session, selection),
        ChoiceBox,
        title="Channel List & Tuner Settings Updater",
        list=choices
    )


def Plugins(**kwargs):
    if PluginDescriptor is None:
        return []

    return [
        PluginDescriptor(
            name="Channel List & Tuner Settings Updater",
            description="Channel list & tuner settings updater",
            where=[PluginDescriptor.WHERE_PLUGINMENU],
            fnc=main_plugin
        )
    ]


if __name__ == "__main__":
    main()
