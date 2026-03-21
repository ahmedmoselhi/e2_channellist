#!/usr/bin/env python3
import os
import sys
import subprocess
import time

# [ 🎨 PRESERVED GRAPHICS ENGINE v5.0 ]


class Color:
    BLUE = '\033[94m'
    CYAN = '\033[96m'
    GREEN = '\033[92m'
    YELLOW = '\033[93m'
    RED = '\033[91m'
    BOLD = '\033[1m'
    END = '\033[0m'


def toggle_maximized():
    """Attempts to maximize the terminal window on Linux/X11/Wayland."""
    try:
        subprocess.run(["wmctrl",
                        "-r",
                        ":ACTIVE:",
                        "-b",
                        "add,maximized_vert,maximized_horz"],
                       capture_output=True)
    except FileNotFoundError:
        sys.stdout.write("\033[8;50;150t")
        sys.stdout.flush()


def print_header():
    os.system('clear')
    print(f"{Color.BLUE}{Color.BOLD}" + "=" * 80)
    print(r"""
  _______ ___       __  __ ___   _   _ _   _ _   _ __  __  _   _____ _____
 |__   __|__ \     |  \/  |_ _| | | | | | | | | | |  \/  |/ \ |_   _| ____|
    | |     ) |____| |\/| || |  | | | | | | | | | | |\/| / _ \  | | |  _|
    | |    / /|____| |  | || |  | |_| | |_| | |_| | |  |/ ___ \ | | | |___
    |_|   |___|    |_|  |_|___|  \___/ \___/ \___/|_|  /_/   \_\|_| |_____|

              [ MASTER COMMAND & CONTROL CENTER ]
    """)
    print("=" * 80 + f"{Color.END}")


def get_choice():
    options = [
        ("1",
         "LYNGSAT DX MASTER SUITE",
         "Full satellite web-scraping and frequency extraction."),
        ("2",
         "T2-MI DX GENERATOR (Automated)",
         "Automated decap engine for T2-MI stream generation."),
        ("3",
         "URL.TXT ORBITAL SORTER",
         "Sort url.txt entries by satellite position (West -> East)."),
        # NEW OPTION 4
        ("4",
         "LAMEDB MERGER SUITE",
         "Merge Enigma2 lamedb files with GUI interface."),
        ("Q",
         "QUIT",
         "Exit the suite.")]

    print(f"\n{Color.YELLOW}AVAILABLE DX MODULES:{Color.END}")
    for key, title, desc in options:
        print(f"  {Color.CYAN}[{key}]{Color.END} {Color.BOLD}{title.ljust(35)}{Color.END} - {desc}")

    return input(f"\n{Color.YELLOW}Selection > {Color.END}").upper()


def run_script(script_name):
    script_dir = os.path.dirname(os.path.abspath(__file__))
    full_path = os.path.join(script_dir, script_name)

    if os.path.exists(full_path):
        # Added a loop here to allow reloading the same script
        while True:
            try:
                subprocess.run([sys.executable, full_path], cwd=script_dir)

                # Post-execution Choice
                print(
                    f"\n{Color.BLUE}┌──────────────────────────────────────────────────────────────────────────┐")
                print(
                    f"│ {Color.BOLD}TASK COMPLETED.{Color.END} What would you like to do?                               │")
                print(
                    f"└──────────────────────────────────────────────────────────────────────────┘{Color.END}")

                # Updated prompt to include 'R'
                final_choice = input(f"{Color.YELLOW}Enter 'M' for Main Menu, 'R' to Reload script, or 'Q' to Quit: {Color.END}").upper()
                
                if final_choice == 'R':
                    print(f"\n{Color.GREEN}Restarting {script_name}...{Color.END}")
                    time.sleep(1)
                    continue # This loops back to the start of 'while True' to run the script again
                elif final_choice == 'Q':
                    return 'Q'
                else:
                    return 'M' # Default to Main Menu

            except KeyboardInterrupt:
                # HANDLE CTRL + C HERE
                print(f"\n\n{Color.RED}[!] PROCESS INTERRUPTED BY USER (Ctrl+C){Color.END}")
                while True:
                    interrupt_choice = input(f"{Color.YELLOW}Enter 'M' to go back to Main Menu or 'Q' to Quit: {Color.END}").upper()
                    if interrupt_choice == 'M':
                        return 'M'
                    elif interrupt_choice == 'Q':
                        return 'Q'
                    else:
                        print(f"{Color.RED}Invalid selection. Please enter 'M' or 'Q'.{Color.END}")

            except Exception as e:
                print(f"{Color.RED}Execution Error: {e}{Color.END}")
                input("Press Enter to continue...")
                return 'M'
    else:
        print(f"{Color.RED}Error: {script_name} not found!{Color.END}")
        input("Press Enter to continue...")
        return 'M'


def main():
    toggle_maximized()

    scripts = {
        "1": "LYNGSAT DX MASTER SUITE.py",
        "2": "T2-MI Ultimate DX Generator (Automated Edition).py",
        "3": "Url.txt Order.py",
        # NEW SCRIPT REFERENCE
        "4": "Lamedb Merger.py"
    }

    while True:
        print_header()
        print(
            f"{Color.BLUE}┌─────────────────────────────────────────────────────────────────────────────┐")
        print(
            f"│ {Color.BOLD}INSTRUCTIONS:{Color.END} Select a module to launch. Each module opens in this window.  │")
        print(
            f"└─────────────────────────────────────────────────────────────────────────────┘{Color.END}")

        try:
            choice = get_choice()

            if choice == 'Q':
                break
            elif choice in scripts:
                after_action = run_script(scripts[choice])
                if after_action == 'Q':
                    break
            else:
                print(f"{Color.RED}Invalid Selection.{Color.END}")
                time.sleep(1)
        
        except KeyboardInterrupt:
            # HANDLE CTRL + C AT MAIN MENU
            print(f"\n\n{Color.RED}[!] Keyboard Interrupt detected.{Color.END}")
            confirm = input(f"{Color.YELLOW}Return to Menu (M) or Quit (Q)? [M]: {Color.END}").upper()
            if confirm == 'Q':
                break
            else:
                continue

    print(f"\n{Color.GREEN}Exiting DX Master Suite. Goodbye!{Color.END}")


if __name__ == "__main__":
    main()
