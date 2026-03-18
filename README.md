# 🛰️ T2-MI Ultimate DX Generator Suite
### *The Definitive Enigma2 Satellite Engineering Toolkit*

The **T2-MI Ultimate DX Generator Suite** is a professional collection of Python-based tools designed for Satellite DXers and Enigma2 enthusiasts. This suite automates the complex bridge between raw T2-MI transponder data and the Enigma2 Linux ecosystem (Vu+, DreamBox, Octagon, etc.), handling everything from `lamedb` service injection to `astra-sm` LUA configuration.

---

## 📖 The Three Pillars of the Suite

### 1. Standard Edition (The "Baseline")
**Focus:** Reliability & Fresh Installations.
The Standard Edition provides a clean, automated workflow for generating new database files. It is optimized for standard DVB-S/S2 T2-MI feeds where complexity is low but precision is required.
* **Core Logic:** A linear `Input ➔ Process ➔ Write` flow.
* **Database Style:** Appends new data to existing sections using safe marker detection.
* **Best For:** Quick setups and users targeting standard T2-MI packages.

### 2. Multistream Edition (The "Parameter Specialist")
**Focus:** Advanced DVB-S2X & Professional Feeds.
This version introduces support for **Root/Gold PLP IDs** and **Input Stream IDs (ISI)**. It is specifically tuned for professional multistream packages (e.g., RAI, TNT, or African feeds) that require specialized Namespace hex calculations to lock.
* **Core Logic:** Parameter-aware generation with **Visual File Management**.
* **Database Style:** Snapshot-based merging with automated timestamped backups.
* **Best For:** DXers targeting high-complexity professional multistream satellite signals.

### 3. Edit Edition (The "Architect")
**Focus:** Non-Destructive Live Database Management.
The flagship of the suite, featuring a **Surgical Injection Engine**. Unlike standard scripts that simply append data, the Architect reads your live database, identifies service headers, and performs a "smart merge."
* **Core Logic:** `Load ➔ Deduplicate ➔ Surgical Inject ➔ Live Swap`.
* **Database Style:** Real-time modification of `lamedb` with automatic old-entry deletion to prevent "ghost services."
* **Best For:** Power users maintaining large, custom service lists who require zero-risk live editing.

---

## 🛠️ Advanced Technical Features

### 💉 Surgical Merge Engine (Edit Edition Only)
The Architect doesn't just write text; it understands the `lamedb` structure. It identifies the `transponders` and `services` sections and injects new data at the top, ensuring Enigma2 parses the newest entries first while maintaining database integrity.

### 📂 Visual File Manager
Eliminate manual path typing. Both Multistream and Edit editions feature a built-in terminal file browser to navigate your receiver's directory structure via keyboard.

### 🔄 Live Swap Protocol & Safety
1.  **Auto-Backup:** A `.bak` file is created before any write operation.
2.  **Local Sync:** Changes are first saved to a local "safety" workspace.
3.  **Swap Verify:** The script asks for final confirmation before overwriting the live system file on your receiver.

### 📜 Categorized History
Isolated history buffers for **Frequency**, **SID**, and **PID**. Pressing "Up" in the SID field will only show previous SIDs—never frequencies or provider names.

---

## 📊 Feature Comparison Matrix

| Technical Feature | Standard | Multistream | Edit Edition |
| :--- | :---: | :---: | :---: |
| **T2-MI Service Generation** | ✅ | ✅ | ✅ |
| **Astra-SM LUA Generation** | ✅ | ✅ | ✅ |
| **Userbouquet Auto-Sync** | ✅ | ✅ | ✅ |
| **Progress Bar Visualization** | ✅ | ✅ | ✅ |
| **PLP / ISI Support** | ❌ | ✅ | ✅ |
| **Visual File Manager UI** | ❌ | ✅ | ✅ |
| **Timestamped Backups (.bak)** | ❌ | ✅ | ✅ |
| **Categorized Input History** | ❌ | ✅ | ✅ |
| **Surgical Header Injection** | ❌ | ❌ | ✅ |
| **Auto-Delete Duplicate SIDs** | ❌ | ❌ | ✅ |
| **Live Swap Protocol** | ❌ | ❌ | ✅ |

---

## 📐 Workflow Architecture

The suite follows a non-destructive lifecycle to ensure your satellite receiver's stability:



1.  **Selection:** Choose between "Modify" (Live Edit) or "Fresh Start."
2.  **Navigation:** Browse to your `lamedb` via the File Manager.
3.  **Ingestion:** Provide parameters with the help of Categorized History.
4.  **Processing:** The Engine cleans the data and prepares the hex Namespace.
5.  **Validation:** A backup is generated, and files are written to the local workspace.
6.  **Deployment:** Confirmed "Swap" to push changes to the live system.

---

## 📥 Installation & Usage

1.  **Clone the repository:**
    ```bash
    git clone [https://github.com/yourusername/t2mi-dx-generator.git](https://github.com/yourusername/t2mi-dx-generator.git)
    cd t2mi-dx-generator
    ```
2.  **Install Dependencies:**
    The scripts use `prompt_toolkit`. Install it via:
    ```bash
    pip install prompt_toolkit colorama
    ```
3.  **Run your preferred edition:**
    ```bash
    python "T2-MI Ultimate DX Generator (Edit Edition).py"
    ```
