# -*- coding: utf-8 -*-
import argparse, sys
from .tasks import *


def run_interactive_menu():
    get_input = raw_input if sys.version_info[0] == 2 else input
    menu_choice = get_input("\n[?] Choose an action: ").strip()
    if menu_choice == '1': download_and_extract_channels()
    elif menu_choice == '2': export_tuner_config()
    elif menu_choice == '3': update_tuner_settings()
    elif menu_choice == '4': download_astra_conf()
    elif menu_choice == '5':
        stop_enigma2(); download_and_extract_channels(False); update_tuner_settings(manage_e2_state=False); download_astra_conf(); start_enigma2()
    else: sys.exit()


def main():
    parser = argparse.ArgumentParser(description='Channel List & Tuner Settings Updater')
    parser.add_argument('-c', '--channels', action='store_true')
    parser.add_argument('-b', '--backup', action='store_true')
    parser.add_argument('-t', '--tuner', action='store_true')
    parser.add_argument('--tuner-target', choices=['0', '1'])
    parser.add_argument('--firmware-logic', choices=['1', '2'])
    parser.add_argument('-a', '--astra', action='store_true')
    parser.add_argument('--all', action='store_true')
    if len(sys.argv) == 1: return run_interactive_menu()
    args = parser.parse_args()
    if args.all:
        stop_enigma2(); download_and_extract_channels(False); update_tuner_settings(args.tuner_target, args.firmware_logic, False); download_astra_conf(); start_enigma2(); return
    if args.channels: download_and_extract_channels()
    if args.backup: export_tuner_config()
    if args.tuner: update_tuner_settings(args.tuner_target, args.firmware_logic)
    if args.astra: download_astra_conf()
