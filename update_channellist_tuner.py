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
# Fetches the latest code directly from the master branch archive
CHANNELS_URL = 'https://github.com/ahmedmoselhi/e2_channellist/archive/refs/heads/master.zip'
TUNER_URL = 'https://raw.githubusercontent.com/ahmedmoselhi/e2_channellist/refs/heads/tuner/tuner_backup_20251027_201613.txt'

def stop_enigma2():
    """Completely stops Enigma2 to prevent memory settings from overwriting files."""
    print("\nStopping Enigma2 (init 4)...")
    os.system('init 4')
    time.sleep(5) 

def start_enigma2():
    """Restarts the Enigma2 service."""
    print("\nRestarting Enigma2 (init 3)...")
    os.system('init 3')

def download_and_extract_channels():
    """Downloads master zip, handles GitHub's subfolder, and verifies lamedb before restart."""
    tmp_zip = '/tmp/channels.zip'
    extract_to = '/tmp/channels_extracted'
    critical_file = os.path.join(ENIGMA2_PATH, 'lamedb')
    
    print("\n--- Channel List Update ---")
    
    stop_enigma2()
    
    try:
        # 1. Download from Master Branch
        print("Downloading latest master branch from GitHub...")
        urllib.request.urlretrieve(CHANNELS_URL, tmp_zip)
        
        # 2. Extract to a temporary folder
        if os.path.exists(extract_to):
            shutil.rmtree(extract_to)
        
        print("Extracting and cleaning up directory structure...")
        with zipfile.ZipFile(tmp_zip, 'r') as zip_ref:
            zip_ref.extractall(extract_to)
        
        # 3. Handle GitHub's automatic subfolder (e.g., repo-master/)
        subfolders = [f for f in os.listdir(extract_to) if os.path.isdir(os.path.join(extract_to, f))]
        
        if subfolders:
            source_path = os.path.join(extract_to, subfolders[0])
            print("Moving files from {0} to {1}...".format(subfolders[0], ENIGMA2_PATH))
            
            # Move each file/folder individually to merge with existing /etc/enigma2/
            for item in os.listdir(source_path):
                s = os.path.join(source_path, item)
                d = os.path.join(ENIGMA2_PATH, item)
                if os.path.isdir(s):
                    if os.path.exists(d):
                        shutil.rmtree(d)
                    shutil.copytree(s, d)
                else:
                    shutil.copy2(s, d)
            
            # 4. Critical File Verification
            print("Verifying system integrity...")
            if os.path.exists(critical_file) and os.path.getsize(critical_file) > 0:
                print("Success: 'lamedb' verified. Proceeding to restart.")
                start_enigma2()
            else:
                print("!! WARNING !!: 'lamedb' is missing or empty in {0}.".format(ENIGMA2_PATH))
                print("Enigma2 will NOT be restarted automatically to allow for manual repair.")
        else:
            print("Error: No content found in the downloaded zip.")
            start_enigma2()

        # Cleanup /tmp
        if os.path.exists(tmp_zip): os.remove(tmp_zip)
        if os.path.exists(extract_to): shutil.rmtree(extract_to)

    except Exception as e:
        print("Error updating channels: {0}".format(str(e)))
        start_enigma2()

def update_tuner_settings():
    """Downloads tuner settings and converts format for OpenATV or OpenPLi compatibility."""
    if not os.path.exists(SETTINGS_FILE):
        print("Error: Settings file not found at {0}".format(SETTINGS_FILE))
        return

    print("\n--- Tuner Settings Update ---")
    
    choice = input("Enter target tuner index (0 for Tuner A, 1 for Tuner B): ").strip()
    if choice not in ['0', '1']:
        print("Invalid choice. Skipping tuner update.")
        return

    print("\nSelect Image Format:")
    print("1. OpenATV (Standard .dvbs format)")
    print("2. OpenPLi (Cleaned format - remove .dvbs from keys)")
    fmt_choice = input("Choice [1/2]: ").strip()

    stop_enigma2()

    # Create Backup
    os.system('cp {0} {1}'.format(SETTINGS_FILE, BACKUP_FILE))
    
    try:
        print("Downloading tuner settings...")
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
            for line in clean_lines:
                f.write(line + '\n')
            for line in processed_settings:
                f.write(line + '\n')

        print("Success: Tuner {0} settings updated for {1} format.".format(
            choice, "OpenPLi" if fmt_choice == '2' else "OpenATV"
        ))
    except Exception as e:
        print("An error occurred during tuner update: {0}".format(str(e)))
    
    start_enigma2()

def main():
    print("====================================")
    print("  Enigma2 Update & Tuner Utility    ")
    print("====================================")
    print("1. Update Channel List (Zip)")
    print("2. Update Tuner Settings (Txt)")
    print("3. Full Update (Both)")
    print("4. Exit")
    
    menu_choice = input("\nSelect an option: ").strip()

    if menu_choice == '1':
        download_and_extract_channels()
    elif menu_choice == '2':
        update_tuner_settings()
    elif menu_choice == '3':
        download_and_extract_channels()
        update_tuner_settings()
    else:
        print("Exiting.")
        sys.exit()

if __name__ == "__main__":
    main()
