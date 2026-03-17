#!/usr/bin/env python3
import os
import sys
import subprocess

# [ 🎨 PRESERVED GRAPHICS ENGINE v5.0 ]
class Color:
    BLUE = '\033[94m'
    CYAN = '\033[96m'
    GREEN = '\033[92m'
    YELLOW = '\033[93m'
    RED = '\033[91m'
    BOLD = '\033[1m'
    END = '\033[0m'

def print_header():
    os.system('clear')
    print(f"{Color.BLUE}{Color.BOLD}" + "="*80)
    print(r"""
  _______ ___       __  __ ___   _   _ _   _ _   _ __  __  _   _____ _____ 
 |__   __|__ \     |  \/  |_ _| | | | | | | | | | |  \/  |/ \ |_   _| ____|
    | |     ) |____| |\/| || |  | | | | | | | | | | |\/| / _ \  | | |  _|  
    | |    / /|____| |  | || |  | |_| | |_| | |_| | |  |/ ___ \ | | | |___ 
    |_|   |___|    |_|  |_|___|  \___/ \___/ \___/|_|  /_/   \_\|_| |_____|
                                                                           
              [ MASTER COMMAND & CONTROL CENTER ]
    """)
    print("="*80 + f"{Color.END}")

def get_choice():
    # Human-readable illustrative text for each script
    options = [
        ("1", "LYNGSAT DX MASTER SUITE", "Full satellite web-scraping and frequency extraction."),
        ("2", "T2-MI DX GENERATOR (Standard)", "Standard decap engine for T2-MI stream generation."),
        ("3", "T2-MI DX GENERATOR (Multistream)", "Advanced mode for MIS/PLS multistream transponders."),
        ("4", "T2-MI DX GENERATOR (Edit)", "Modify/Append existing Astra and LameDB entries."),
        ("Q", "QUIT", "Exit the suite.")
    ]

    print(f"\n{Color.YELLOW}AVAILABLE DX MODULES:{Color.END}")
    for key, title, desc in options:
        print(f"  {Color.CYAN}[{key}]{Color.END} {Color.BOLD}{title.ljust(35)}{Color.END} - {desc}")
    
    return input(f"\n{Color.YELLOW}Selection > {Color.END}").upper()

def run_script(script_name):
    # Change directory to script location to ensure relative paths work
    script_dir = os.path.dirname(os.path.abspath(__file__))
    if os.path.exists(os.path.join(script_dir, script_name)):
        try:
            # Re-uses the current Python environment (important for prompt_toolkit)
            subprocess.run([sys.executable, os.path.join(script_dir, script_name)], cwd=script_dir)
        except Exception as e:
            print(f"{Color.RED}Execution Error: {e}{Color.END}")
            input("Press Enter to continue...")
    else:
        print(f"{Color.RED}Error: {script_name} not found!{Color.END}")
        input("Press Enter to continue...")

def main():
    scripts = {
        "1": "LYNGSAT DX MASTER SUITE.py",
        "2": "T2-MI Ultimate DX Generator (Standard Edition).py",
        "3": "T2-MI Ultimate DX Generator (Multistream Edition).py",
        "4": "T2-MI Ultimate DX Generator (Edit Edition).py"
    }

    while True:
        print_header()
        # Restore helper text block
        print(f"{Color.BLUE}┌──────────────────────────────────────────────────────────────────────────┐")
        print(f"│ {Color.BOLD}INSTRUCTIONS:{Color.END} Select a module to launch. Each module opens in this window. │")
        print(f"└──────────────────────────────────────────────────────────────────────────┘{Color.END}")
        
        choice = get_choice()
        if choice == 'Q': break
        elif choice in scripts: run_script(scripts[choice])
        else:
            print(f"{Color.RED}Invalid Selection.{Color.END}")
            time.sleep(1)

if __name__ == "__main__":
    main()
