import sys
import os
import subprocess
import shutil
import json
import re
from datetime import datetime

# ==============================================================================
# BOOTSTRAP: AUTOMATIC DEPENDENCY INSTALLATION
# ==============================================================================

def check_and_install_dependencies():
    try:
        import tkinter
        return True
    except ImportError:
        print("Tkinter module not found. Attempting automatic installation...")
        if not sys.platform.startswith("linux"):
            print("Error: Automatic installation is only supported on Linux/Debian systems.")
            sys.exit(1)
        if not shutil.which("apt-get"):
            print("Error: 'apt-get' package manager not found.")
            sys.exit(1)

        if os.geteuid() != 0:
            print("Root privileges required. Requesting sudo...")
            cmd = ['sudo', sys.executable] + sys.argv
            try:
                subprocess.call(cmd)
                sys.exit(0)
            except Exception as e:
                print(f"Failed to escalate privileges: {e}")
                sys.exit(1)
        else:
            print("Installing python3-tk...")
            try:
                subprocess.check_call(['apt-get', 'update', '-qq'])
                subprocess.check_call(['apt-get', 'install', '-y', 'python3-tk'])
                print("Installation successful.")
                original_user = os.environ.get('SUDO_USER')
                if original_user:
                    subprocess.call(['sudo', '-u', original_user, sys.executable] + sys.argv)
                    sys.exit(0)
            except subprocess.CalledProcessError as e:
                print(f"Installation failed: {e}")
                sys.exit(1)

check_and_install_dependencies()

# ==============================================================================
# MAIN APPLICATION
# ==============================================================================

import tkinter as tk
from tkinter import filedialog, scrolledtext, messagebox
from tkinter import ttk

CONFIG_FILE = "lamedb_merger_config.json"

class LamedbParser:
    """Handles the parsing and merging logic for Lamedb files."""
    
    HEADER_PATTERN = re.compile(r"^[0-9a-fA-F]+:[0-9a-fA-F]+:[0-9a-fA-F]+")

    @staticmethod
    def parse_file(filepath):
        transponders = {}
        services = {}
        
        current_mode = 0 
        current_header = None
        current_block_lines = []

        def save_block():
            nonlocal current_header, current_block_lines
            if current_header and current_block_lines:
                content = "".join(current_block_lines)
                if current_mode == 1:
                    transponders[current_header] = content
                elif current_mode == 2:
                    lines = content.splitlines()
                    s_name = ""
                    if len(lines) > 1:
                        s_name = lines[1].strip()
                    
                    services[current_header] = {
                        'content': content,
                        'name': s_name
                    }
            
            current_header = None
            current_block_lines = []

        try:
            with open(filepath, 'r', encoding='utf-8', errors='ignore') as f:
                lines = f.readlines()
        except Exception as e:
            raise Exception(f"Could not read file: {e}")

        for line in lines:
            stripped = line.strip()
            
            # Handle Section Headers
            if stripped == "transponders":
                save_block()
                current_mode = 1
                continue
            elif stripped == "services":
                save_block()
                current_mode = 2
                continue
            elif stripped == "end":
                save_block()
                current_mode = 0
                continue
            
            # Handle Transponder Separator
            if stripped == "/":
                save_block()
                continue

            # Detect Headers
            is_header = (not line.startswith('\t')) and LamedbParser.HEADER_PATTERN.match(stripped)

            if is_header:
                save_block()
                current_header = stripped
                current_block_lines = [line]
            else:
                # Append data lines. 
                # IMPORTANT: We do NOT skip empty lines here. 
                # An empty line inside a block represents an empty service name.
                if current_header:
                    current_block_lines.append(line)
        
        save_block()
                
        return transponders, services

    @staticmethod
    def merge_data(base_data, source_data, strict_name_check=False):
        merged = base_data.copy()
        new_count = 0
        
        for key, src_val in source_data.items():
            is_duplicate = False
            
            if key in merged:
                if strict_name_check:
                    base_name = merged[key]['name']
                    src_name = src_val['name']
                    if base_name == src_name:
                        is_duplicate = True
                else:
                    is_duplicate = True

            if not is_duplicate:
                merged[key] = src_val
                new_count += 1
                
        return merged, new_count

    @staticmethod
    def write_file(filepath, transponders, services, sort_services=False):
        try:
            with open(filepath, 'w', encoding='utf-8') as f:
                f.write("eDVB services /4/\n")
                
                # --- TRANSPONDERS ---
                f.write("transponders\n")
                for key in sorted(transponders.keys()):
                    content = transponders[key]
                    f.write(content)
                    # Ensure Transponders end with /
                    if not content.strip().endswith('/'):
                        f.write("/\n")
                f.write("end\n")
                
                # --- SERVICES ---
                f.write("services\n")
                
                keys = list(services.keys())
                
                if sort_services:
                    def get_sort_name(k):
                        val = services[k]
                        name = val['name']
                        # Empty names first
                        return (name != "", name.lower())
                    keys.sort(key=get_sort_name)
                else:
                    keys.sort()

                for key in keys:
                    content = services[key]['content']
                    
                    lines = content.splitlines()
                    
                    # SAFETY: Remove trailing '/' lines if they exist
                    # We must NOT remove empty lines, as they are valid names.
                    while lines and lines[-1].strip() == '/':
                        lines.pop()
                    
                    # Write lines
                    for line in lines:
                        f.write(line + "\n")
                    
                f.write("end\n")
                
            return True
        except Exception as e:
            raise Exception(f"Could not write file: {e}")


class LamedbMergerApp:
    """Main Graphical User Interface Class."""

    BG_COLOR = "#F0F2F5"
    ACCENT_COLOR = "#0078D4"
    TEXT_COLOR = "#1A1A1A"
    CARD_BG = "#FFFFFF"

    def __init__(self, root):
        self.root = root
        self.root.title("Enigma2 Lamedb Merger")
        self.root.geometry("850x750")
        self.root.configure(bg=self.BG_COLOR)
        
        # Create log filename immediately
        ts = datetime.now().strftime("%Y%m%d_%H%M%S")
        self.log_filename = f"lamedb_merger_{ts}.log"
        
        self.file1_path = tk.StringVar()
        self.file2_path = tk.StringVar()
        self.dest_path = tk.StringVar()
        self.sort_services_var = tk.BooleanVar(value=False)
        self.strict_duplicate_var = tk.BooleanVar(value=False)

        self._setup_styles()
        self._setup_ui()
        self._load_config()

    def _setup_styles(self):
        style = ttk.Style()
        if 'clam' in style.theme_names():
            style.theme_use('clam')
        
        style.configure("TLabel", background=self.BG_COLOR, foreground=self.TEXT_COLOR, font=("Segoe UI", 11))
        style.configure("TFrame", background=self.BG_COLOR)
        style.configure("Card.TLabelframe", background=self.CARD_BG)
        style.configure("Card.TLabelframe.Label", background=self.CARD_BG, foreground=self.TEXT_COLOR, font=("Segoe UI", 11, "bold"))
        style.configure("TButton", font=("Segoe UI", 10), padding=10)
        style.configure("Accent.TButton", background=self.ACCENT_COLOR, foreground="white", font=("Segoe UI", 11, "bold"), padding=15)
        style.map("Accent.TButton", background=[('active', '#005A9E')])
        style.configure("TCheckbutton", background=self.BG_COLOR, foreground=self.TEXT_COLOR, font=("Segoe UI", 10))
        style.map("TCheckbutton", background=[('active', self.BG_COLOR)])

    def _setup_ui(self):
        container = tk.Frame(self.root, bg=self.BG_COLOR)
        container.pack(fill="both", expand=True, padx=30, pady=30)

        header_frame = tk.Frame(container, bg=self.BG_COLOR)
        header_frame.pack(fill="x", pady=(0, 15))
        tk.Label(header_frame, text="Lamedb Merger Suite", font=("Segoe UI", 24, "bold"), bg=self.BG_COLOR, fg="#004578").pack(side="left")
        tk.Label(header_frame, text="v13.0 (Structure Fix)", font=("Segoe UI", 12), bg=self.BG_COLOR, fg="gray").pack(side="left", padx=10, pady=(10,0))

        files_frame = tk.Frame(container, bg=self.BG_COLOR)
        files_frame.pack(fill="x", pady=5)

        self._create_modern_file_row(files_frame, "File 1 (Source)", "New items to add.", self.file1_path, 0)
        self._create_modern_file_row(files_frame, "File 2 (Destination)", "The main file to be updated.", self.file2_path, 1)
        self._create_modern_file_row(files_frame, "Output File", "Auto-generated name.", self.dest_path, 2, is_save=True)

        opts_frame = tk.Frame(container, bg=self.BG_COLOR)
        opts_frame.pack(fill="x", pady=15)
        
        ttk.Checkbutton(opts_frame, text="Sort Services Alphabetically (Empty names first)", variable=self.sort_services_var).pack(anchor="w")
        ttk.Checkbutton(opts_frame, text="Strict Duplicate Check (Match ID + Name exactly)", variable=self.strict_duplicate_var).pack(anchor="w", pady=5)

        action_frame = tk.Frame(container, bg=self.BG_COLOR)
        action_frame.pack(pady=20)
        ttk.Button(action_frame, text="MERGE FILES", command=self.run_merge_process, style="Accent.TButton", width=30).pack()

        log_frame = ttk.LabelFrame(container, text=f"Process Log: {self.log_filename}", style="Card.TLabelframe", padding=10)
        log_frame.pack(fill="both", expand=True, pady=(10, 0))
        
        self.log_area = scrolledtext.ScrolledText(log_frame, height=12, font=("Consolas", 10), bg="#F8F9FA", relief="flat", borderwidth=0, highlightthickness=1, highlightbackground="#E0E0E0")
        self.log_area.pack(fill="both", expand=True)
        self.log_area.bind("<Key>", lambda e: "break")

    def _create_modern_file_row(self, parent, title, subtitle, variable, row_index, is_save=False):
        card = tk.Frame(parent, bg=self.CARD_BG, padx=20, pady=15)
        card.pack(fill="x", pady=5)
        
        text_frame = tk.Frame(card, bg=self.CARD_BG)
        text_frame.pack(side="left", fill="y")
        tk.Label(text_frame, text=title, bg=self.CARD_BG, fg=self.TEXT_COLOR, font=("Segoe UI", 12, "bold")).pack(anchor="w")
        tk.Label(text_frame, text=subtitle, bg=self.CARD_BG, fg="gray", font=("Segoe UI", 9)).pack(anchor="w")

        input_frame = tk.Frame(card, bg=self.CARD_BG)
        input_frame.pack(side="right", fill="x", expand=True, padx=(20, 0))
        
        ttk.Entry(input_frame, textvariable=variable, font=("Segoe UI", 10)).pack(side="left", fill="x", expand=True, padx=(0, 10))
        
        btn_text = "Save As..." if is_save else "Browse"
        cmd = lambda: self._browse_save_file(variable) if is_save else self._browse_file(variable)
        ttk.Button(input_frame, text=btn_text, command=cmd, width=12).pack(side="right")

    def _load_config(self):
        if os.path.exists(CONFIG_FILE):
            try:
                with open(CONFIG_FILE, 'r') as f:
                    data = json.load(f)
                    self.file1_path.set(data.get('file1', ''))
                    self.file2_path.set(data.get('file2', ''))
            except Exception:
                pass

    def _save_config(self):
        data = {
            'file1': self.file1_path.get(),
            'file2': self.file2_path.get()
        }
        try:
            with open(CONFIG_FILE, 'w') as f:
                json.dump(data, f)
        except Exception:
            pass

    def _browse_file(self, variable):
        path = filedialog.askopenfilename(title="Select Lamedb File", filetypes=[("Lamedb files", "lamedb"), ("All files", "*.*")])
        if path:
            variable.set(path)
            self._save_config()
            
            if variable == self.file2_path:
                self._auto_fill_destination()

    def _auto_fill_destination(self):
        f2 = self.file2_path.get()
        if f2:
            ts = datetime.now().strftime("%Y%m%d_%H%M%S")
            base_dir = os.path.dirname(f2)
            default_name = f"lamedb_merged_{ts}"
            self.dest_path.set(os.path.join(base_dir, default_name))

    def _browse_save_file(self, variable):
        if not self.dest_path.get():
             self._auto_fill_destination()
             
        path = filedialog.asksaveasfilename(title="Save Merged File", initialfile=os.path.basename(self.dest_path.get()), defaultextension="", filetypes=[("Lamedb files", "lamedb"), ("All files", "*.*")])
        if path:
            variable.set(path)

    def log(self, message):
        timestamp = datetime.now().strftime("%H:%M:%S")
        log_entry = f"  [{timestamp}] {message}"
        
        self.log_area.config(state='normal')
        self.log_area.insert(tk.END, log_entry + "\n")
        self.log_area.see(tk.END)
        self.log_area.config(state='disabled')
        
        try:
            with open(self.log_filename, 'a', encoding='utf-8') as f:
                f.write(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] {message}\n")
        except Exception:
            pass

    def _backup_file(self, filepath, prefix):
        if not filepath or not os.path.exists(filepath):
            return
        
        backup_dir = os.path.join(os.path.dirname(filepath), "backups")
        try:
            if not os.path.exists(backup_dir):
                os.makedirs(backup_dir)
            
            ts = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = os.path.basename(filepath)
            backup_name = f"{filename}_{prefix}_{ts}.bak"
            backup_path = os.path.join(backup_dir, backup_name)
            
            shutil.copy2(filepath, backup_path)
            self.log(f"Backup created: {backup_name}")
        except Exception as e:
            self.log(f"Warning: Failed to create backup - {e}")

    def run_merge_process(self):
        f1 = self.file1_path.get()
        f2 = self.file2_path.get()
        dest = self.dest_path.get()
        
        if not dest or dest == f2:
            self.log("Destination invalid or matches input. Auto-generating output filename...")
            self._auto_fill_destination()
            dest = self.dest_path.get()

        sort_opt = self.sort_services_var.get()
        strict_opt = self.strict_duplicate_var.get()

        if not all([f1, f2, dest]):
            messagebox.showwarning("Input Missing", "Please select Source and Destination files.")
            return

        self.log("-" * 20)
        self.log("Starting merge process...")
        
        try:
            self.log("Creating backups...")
            self._backup_file(f1, "source")
            self._backup_file(f2, "dest")

            self.log(f"Parsing Source File: {os.path.basename(f1)}...")
            src_t, src_s = LamedbParser.parse_file(f1)
            
            self.log(f"Parsing Destination File: {os.path.basename(f2)}...")
            base_t, base_s = LamedbParser.parse_file(f2)

            mode_str = "Strict (ID + Name)" if strict_opt else "Standard (ID only)"
            self.log(f"Calculating merge (Mode: {mode_str})...")
            
            merged_t, new_t = LamedbParser.merge_data(base_t, src_t)
            merged_s, new_s = LamedbParser.merge_data(base_s, src_s, strict_name_check=strict_opt)
            
            src_t_count = len(src_t)
            base_t_count = len(base_t)
            merged_t_count = len(merged_t)
            dup_t_count = src_t_count - new_t
            
            src_s_count = len(src_s)
            base_s_count = len(base_s)
            merged_s_count = len(merged_s)
            dup_s_count = src_s_count - new_s

            self.log(f"Writing merged database to: {os.path.basename(dest)}")
            LamedbParser.write_file(dest, merged_t, merged_s, sort_services=sort_opt)
            
            self._save_config()

            self.log("-" * 50)
            self.log("JOB SUMMARY")
            self.log("-" * 50)
            self.log(f"Total Transponders:")
            self.log(f"  Source File      : {src_t_count}")
            self.log(f"  Destination File : {base_t_count}")
            self.log(f"  Merged File      : {merged_t_count}")
            self.log(f"  Duplicates Found : {dup_t_count}")
            self.log("")
            self.log(f"Total Services:")
            self.log(f"  Source File      : {src_s_count}")
            self.log(f"  Destination File : {base_s_count}")
            self.log(f"  Merged File      : {merged_s_count}")
            self.log(f"  Duplicates Found : {dup_s_count}")
            self.log("-" * 50)
            self.log("✅ Merge completed successfully!")

            messagebox.showinfo("Merge Report", 
                f"Merge Successful!\n\n"
                f"Transponders:\n"
                f"  Source: {src_t_count} | Dest: {base_t_count} | Merged: {merged_t_count}\n"
                f"  Duplicates Ignored: {dup_t_count}\n\n"
                f"Services:\n"
                f"  Source: {src_s_count} | Dest: {base_s_count} | Merged: {merged_s_count}\n"
                f"  Duplicates Ignored: {dup_s_count}"
            )

        except Exception as e:
            self.log(f"❌ ERROR: {str(e)}")
            messagebox.showerror("Error", f"An error occurred:\n{str(e)}")

if __name__ == "__main__":
    root = tk.Tk()
    app = LamedbMergerApp(root)
    root.mainloop()
