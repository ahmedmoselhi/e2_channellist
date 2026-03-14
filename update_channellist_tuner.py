import urllib.request
import os
import sys
import zipfile
import time
import shutil

# --- CONFIGURATION ---
SETTINGS_FILE = '/etc/enigma2/settings'
BACKUP_FILE = '/etc/enigma2/settings.bak'
ENIGMA2_PATH = '/etc/enigma2/'
TUXBOX_PATH = '/etc/tuxbox/'
CHANNELS_URL = 'https://github.com/ahmedmoselhi/e2_channellist/archive/refs/heads/master.zip'
TUNER_URL = 'https://github.com/ahmedmoselhi/e2_channellist/raw/refs/heads/tuner/tuner_backup.txt'

def stop_enigma2():
    """Completely stops Enigma2 to prevent memory settings from overwriting files."""
    print("\n[!] Stopping Enigma2 (init 4)...")
    os.system('init 4')
    time.sleep(5) 

def start_enigma2():
    """Restarts the Enigma2 service."""
    print("\n[*] Restarting Enigma2 (init 3)...")
    os.system('init 3')

def download_and_extract_channels():
    """
    HELPER: This option downloads the latest channel list ZIP from GitHub, 
    extracts it, updates your /etc/enigma2/ directory, and automatically 
    syncs your satellites.xml to /etc/tuxbox/ for system-wide compatibility.
    """
    tmp_zip = '/tmp/channels.zip'
    extract_to = '/tmp/channels_extracted'
    critical_file = os.path.join(ENIGMA2_PATH, 'lamedb')
    sat_xml_src = os.path.join(ENIGMA2_PATH, 'satellites.xml')
    sat_xml_dst = os.path.join(TUXBOX_PATH, 'satellites.xml')
    
    print("\n" + "="*40)
    print("      CHANNEL LIST UPDATE STARTED      ")
    print("="*40)
    
    stop_enigma2()
    
    try:
        print("-> Downloading latest master branch...")
        urllib.request.urlretrieve(CHANNELS_URL, tmp_zip)
        
        if os.path.exists(extract_to):
            shutil.rmtree(extract_to)
        
        print("-> Extracting files and cleaning structure...")
        with zipfile.ZipFile(tmp_zip, 'r') as zip_ref:
            zip_ref.extractall(extract_to)
        
        subfolders = [f for f in os.listdir(extract_to) if os.path.isdir(os.path.join(extract_to, f))]
        
        if subfolders:
            source_path = os.path.join(extract_to, subfolders[0])
            print("-> Merging files into {0}...".format(ENIGMA2_PATH))
            
            for item in os.listdir(source_path):
                s = os.path.join(source_path, item)
                d = os.path.join(ENIGMA2_PATH, item)
                if os.path.isdir(s):
                    if os.path.exists(d):
                        shutil.rmtree(d)
                    shutil.copytree(s, d)
                else:
                    shutil.copy2(s, d)
            
            # Automated satellites.xml sync
            if os.path.exists(sat_xml_src):
                print("-> Syncing satellites.xml to /etc/tuxbox/...")
                shutil.copy2(sat_xml_src, sat_xml_dst)

            print("-> Verifying system integrity...")
            if os.path.exists(critical_file) and os.path.getsize(critical_file) > 0:
                print("[SUCCESS] 'lamedb' verified. Finalizing...")
                start_enigma2()
            else:
                print("!! WARNING !!: 'lamedb' is missing. Manual check required.")
        else:
            print("[ERROR] Downloaded zip was empty.")
            start_enigma2()

        if os.path.exists(tmp_zip): os.remove(tmp_zip)
        if os.path.exists(extract_to): shutil.rmtree(extract_to)

    except Exception as e:
        print("[ERROR] Channel update failed: {0}".format(str(e)))
        start_enigma2()

def update_tuner_settings():
    """
    HELPER: This option downloads specific tuner configurations from the latest 
    GitHub commit. It allows you to map settings to Tuner A or B and converts 
    the format specifically for OpenATV or OpenPLi images.
    """
    if not os.path.exists(SETTINGS_FILE):
        print("[ERROR] Settings file not found at {0}".format(SETTINGS_FILE))
        return

    print("\n" + "="*40)
    print("      TUNER SETTINGS CONFIGURATION     ")
    print("="*40)
    
    choice = input("Select Target Tuner [0: Tuner A | 1: Tuner B]: ").strip()
    if choice not in ['0', '1']:
        print("[!] Invalid choice. Aborting tuner update.")
        return

    print("\nSelect Image Format:")
    print(" 1. OpenATV (Standard .dvbs tags)")
    print(" 2. OpenPLi (Cleaned format - removes .dvbs)")
    fmt_choice = input("Choice [1/2]: ").strip()

    stop_enigma2()

    # Create Backup
    os.system('cp {0} {1}'.format(SETTINGS_FILE, BACKUP_FILE))
    
    try:
        print("-> Fetching tuner data from repository...")
        req = urllib.request.Request(TUNER_URL)
        with urllib.request.urlopen(req) as response:
            raw_content = response.read().decode('utf-8').splitlines()

        processed_settings = []
        for line in raw_content:
            line = line.strip()
            if line.startswith('config.Nims.'):
                parts = line.split('.')
                if len(parts) > 2:
                    parts[2] = choice 
                    new_line = ".".join(parts)
                    
                    if fmt_choice == '2':
                        new_line = new_line.replace('.dvbs.', '.').replace('.dvbs=', '=')
                    
                    processed_settings.append(new_line)

        with open(SETTINGS_FILE, 'r') as f:
            clean_lines = [l.strip() for l in f.readlines() if not l.startswith('config.Nims')]
        
        with open(SETTINGS_FILE, 'w') as f:
            for line in clean_lines: f.write(line + '\n')
            for line in processed_settings: f.write(line + '\n')

        print("[SUCCESS] Tuner {0} updated for {1}.".format(
            choice, "OpenPLi" if fmt_choice == '2' else "OpenATV"
        ))
    except Exception as e:
        print("[ERROR] Tuner update failed: {0}".format(str(e)))
    
    start_enigma2()

def main():
    print("\n" + "*"*45)
    print("   _____       _                       ___  ")
    print("  |   __|___ _| |___ _ _ ___ ___ ___  |_  | ")
    print("  |   __|   | . | . | | |  _| .'|_ -|  _| |_")
    print("  |_____|_|_|___|_  |___|_| |__,|___| |_____|")
    print("                |___|  UPDATE UTILITY v5.1 ")
    print("*"*45)
    
    print("\n[1] UPDATE CHANNEL LIST (ZIP)")
    print("    - Downloads latest bouquets and lamedb.")
    print("    - Automatically syncs satellites.xml to /etc/tuxbox/.")
    
    print("\n[2] UPDATE TUNER SETTINGS (TXT)")
    print("    - Downloads tuner config from latest commit.")
    print("    - Customizes index (A/B) and Image format (ATV/PLi).")
    
    print("\n[3] FULL SYSTEM UPDATE")
    print("    - Runs both Channel and Tuner updates sequentially.")
    
    print("\n[4] EXIT")
    print("-" * 45)
    
    menu_choice = input("Select an option [1-4]: ").strip()

    if menu_choice == '1':
        download_and_extract_channels()
    elif menu_choice == '2':
        update_tuner_settings()
    elif menu_choice == '3':
        download_and_extract_channels()
        update_tuner_settings()
    else:
        print("\nExiting. No changes made.")
        sys.exit()

if __name__ == "__main__":
    main()
