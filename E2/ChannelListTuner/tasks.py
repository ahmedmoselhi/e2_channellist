# -*- coding: utf-8 -*-
import os, sys, zipfile, time, shutil
from datetime import datetime
from .compat import urlretrieve, urlopen, Request, get_input_func
from .constants import *


def print_banner(title):
    width = 50
    padding = width - 2 - len(title)
    left_pad = padding // 2
    right_pad = padding - left_pad
    print("\n" + "╔" + "═" * (width - 2) + "╗")
    print("║" + " " * left_pad + title + " " * right_pad + "║")
    print("╚" + "═" * (width - 2) + "╝")


def detect_firmware_logic():
    for path in ['/etc/issue', '/etc/image-version', SETTINGS_FILE]:
        if not os.path.exists(path):
            continue
        try:
            with open(path, 'r') as handle:
                content = handle.read().lower()
        except Exception:
            continue
        if 'openpli' in content or 'openbh' in content or 'openhdf' in content:
            print("-> [DETECT] OpenPLi-based image detected via {0}.".format(path))
            return '2'
        if 'openatv' in content or 'openvix' in content or 'egami' in content:
            print("-> [DETECT] OpenATV-based image detected via {0}.".format(path))
            return '1'
        if 'config.nims.0.dvbs.' in content or 'config.nims.1.dvbs.' in content:
            return '1'
        if 'config.nims.0.advanced.' in content or 'config.nims.1.advanced.' in content:
            return '2'
    return None


def backup_file(filepath):
    if not os.path.exists(filepath):
        return
    if not os.path.exists(BACKUP_DIR):
        os.makedirs(BACKUP_DIR)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = os.path.basename(filepath)
    shutil.copy2(filepath, os.path.join(BACKUP_DIR, "%s_%s" % (filename, timestamp)))


def stop_enigma2():
    os.system('init 4'); time.sleep(5)

def start_enigma2():
    os.system('init 3')


def verify_file_integrity(filepath, is_zip=False):
    if not os.path.exists(filepath):
        raise IOError("File not created: {0}".format(filepath))
    if os.path.getsize(filepath) == 0:
        os.remove(filepath); raise IOError("Downloaded file is empty: {0}".format(filepath))
    if is_zip and not zipfile.is_zipfile(filepath):
        os.remove(filepath); raise IOError("Downloaded file is not a valid ZIP archive.")


def export_tuner_config():
    print_banner("TUNER CONFIGURATION BACKUP")
    if not os.path.exists(SETTINGS_FILE):
        return
    if not os.path.exists(BACKUP_DIR):
        os.makedirs(BACKUP_DIR)
    target_file = os.path.join(BACKUP_DIR, 'tuner_backup.txt')
    tmp_file = target_file + ".tmp"
    tuner_lines = []
    with open(SETTINGS_FILE, 'r') as f:
        for line in f:
            if line.strip().startswith('config.Nims.'):
                tuner_lines.append(line.strip())
    if not tuner_lines:
        return
    with open(tmp_file, 'w') as f:
        for line in tuner_lines:
            f.write(line + '\n')
    shutil.move(tmp_file, target_file)


def download_astra_conf():
    print_banner("ASTRA CONFIGURATION UPDATE")
    tmp_file = ASTRA_FILE_PATH + ".tmp"
    backup_file(ASTRA_FILE_PATH)
    if not os.path.exists(ASTRA_CONF_PATH):
        os.makedirs(ASTRA_CONF_PATH)
    urlretrieve(ASTRA_URL, tmp_file)
    verify_file_integrity(tmp_file)
    shutil.move(tmp_file, ASTRA_FILE_PATH)
    os.chmod(ASTRA_FILE_PATH, 0o644)


def download_and_extract_channels(manage_e2_state=True):
    tmp_zip = '/tmp/channels.zip'; extract_to = '/tmp/channels_extracted'
    sat_xml_src = os.path.join(ENIGMA2_PATH, 'satellites.xml'); sat_xml_dst = os.path.join(TUXBOX_PATH, 'satellites.xml')
    print_banner("CHANNEL LIST UPDATE PROCESS")
    if manage_e2_state: stop_enigma2()
    try:
        backup_file(LAMEDB_PATH); urlretrieve(CHANNELS_URL, tmp_zip); verify_file_integrity(tmp_zip, is_zip=True)
        if os.path.exists(extract_to): shutil.rmtree(extract_to)
        with zipfile.ZipFile(tmp_zip, 'r') as zip_ref: zip_ref.extractall(extract_to)
        subfolders = [f for f in os.listdir(extract_to) if os.path.isdir(os.path.join(extract_to, f))]
        if subfolders:
            source_path = os.path.join(extract_to, subfolders[0])
            for item in os.listdir(source_path):
                s, d = os.path.join(source_path, item), os.path.join(ENIGMA2_PATH, item)
                if os.path.isdir(s):
                    if os.path.exists(d): shutil.rmtree(d)
                    shutil.copytree(s, d)
                else:
                    shutil.copy2(s, d)
            if os.path.exists(sat_xml_src): shutil.copy2(sat_xml_src, sat_xml_dst)
    finally:
        if manage_e2_state: start_enigma2()


def update_tuner_settings(tuner_target=None, firmware_logic=None, manage_e2_state=True):
    if not os.path.exists(SETTINGS_FILE):
        return
    get_input = get_input_func()
    choice = str(tuner_target) if tuner_target is not None else get_input("\n[?] Select Target Tuner [0: Tuner A | 1: Tuner B]: ").strip()
    if choice not in ['0', '1']:
        return
    other_tuner = '1' if choice == '0' else '0'
    if firmware_logic is not None:
        fmt_choice = str(firmware_logic)
    else:
        fmt_choice = detect_firmware_logic() or get_input("Choice [1/2]: ").strip()
    if fmt_choice not in ['1', '2']:
        return
    if manage_e2_state: stop_enigma2()
    backup_file(SETTINGS_FILE)
    tmp_settings = SETTINGS_FILE + '.tmp'
    try:
        response = urlopen(Request(TUNER_URL))
        try: raw_content = response.read().decode('utf-8').splitlines()
        finally: response.close()
        active_block = ["config.Nims.{0}.configMode=advanced".format(choice), "config.Nims.{0}.dvbs.configMode=advanced".format(choice)]
        for line in raw_content:
            line = line.strip()
            if line.startswith('config.Nims.') and '.advanced.' in line:
                parts = line.split('.'); parts[2] = choice; entry = '.'.join(parts)
                if fmt_choice == '2': entry = entry.replace('.dvbs.', '.').replace('.dvbs=', '=')
                active_block.append(entry)
        inactive_block = ["config.Nims.{0}.dvbs.configMode=nothing".format(other_tuner)]
        with open(SETTINGS_FILE, 'r') as f: all_lines = [l.strip() for l in f.readlines()]
        clean_base = [l for l in all_lines if not (l.startswith('config.Nims.{0}.'.format(choice)) or l.startswith('config.Nims.{0}.'.format(other_tuner)))]
        with open(tmp_settings, 'w') as f:
            for line in clean_base + active_block + inactive_block: f.write(line + '\n')
        shutil.move(tmp_settings, SETTINGS_FILE)
    finally:
        if manage_e2_state: start_enigma2()
