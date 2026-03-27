import secrets
import os

def clear_screen():
    os.system('cls' if os.name == 'nt' else 'clear')

def generate_password(length, use_upper, use_lower, use_digits, use_special):
    pool = ""
    # Strictly using your requested letters/digits
    if use_upper: pool += "AB" 
    if use_lower: pool += "ab"
    if use_digits: pool += "012"
    # Strictly using ONLY the forum-allowed special characters
    if use_special: pool += "@#!%*-_"
    
    if not pool:
        return "Error: No characters selected!"
    if length < 8:
        return "Error: Length must be at least 8!"

    # Ensure the password has at least one of each selected type to prevent errors
    password = []
    if use_upper: password.append(secrets.choice("AB"))
    if use_lower: password.append(secrets.choice("ab"))
    if use_digits: password.append(secrets.choice("012"))
    if use_special: password.append(secrets.choice("@#!%*-_"))
    
    # Fill the remaining length
    while len(password) < length:
        password.append(secrets.choice(pool))
    
    # Shuffle for randomness
    secrets.SystemRandom().shuffle(password)
    return ''.join(password)

def main():
    length = 12 # Default to safe length
    settings = {
        "Upper (A, B)": True,
        "Lower (a, b)": True,
        "Digits (0, 1, 2)": True,
        "Forum Specials (@#!%*-_)": True
    }

    while True:
        clear_screen()
        print("========================================")
        print("      FORUM-READY PASS GENERATOR        ")
        print("========================================")
        print(f"  1. Set Length (Min 8) [ Current: {length} ]")
        
        keys = list(settings.keys())
        for i, key in enumerate(keys, start=2):
            status = "[ ON ]" if settings[key] else "[ OFF ]"
            print(f"  {i}. Toggle {key.ljust(20)} {status}")
            
        print("  6. GENERATE PASSWORD")
        print("  Q. Quit")
        print("----------------------------------------")
        
        choice = input("Select an option: ").upper()

        if choice == '1':
            try:
                val = int(input("Enter new length: "))
                length = val if val >= 8 else 8
            except ValueError:
                pass
        elif choice in ['2', '3', '4', '5']:
            idx = int(choice) - 2
            key = keys[idx]
            settings[key] = not settings[key]
        elif choice == '6':
            pwd = generate_password(
                length, 
                settings["Upper (A, B)"], 
                settings["Lower (a, b)"], 
                settings["Digits (0, 1, 2)"], 
                settings["Forum Specials (@#!%*-_)"]
            )
            print(f"\nNEW PASSWORD: {pwd}")
            print("(Characters strictly limited to forum rules)")
            input("\nPress Enter to return to menu...")
        elif choice == 'Q':
            break

if __name__ == "__main__":
    main()
