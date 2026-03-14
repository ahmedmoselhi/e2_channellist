# 🛰️ Satellite DX Toolchain

[![Python 3.7+](https://img.shields.io/badge/python-3.7+-blue.svg)](https://www.python.org/downloads/)
[![Platform](https://img.shields.io/badge/platform-Windows%20%7C%20Linux%20%7C%20macOS-lightgrey)]()
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

Welcome to the ultimate toolchain for Satellite DXers and IPTV/Astra enthusiasts! This repository contains two powerful, synergistic tools designed to automate the extraction and processing of complex T2-MI satellite data.

---

## 📑 Table of Contents
1. [LyngSat DX Master Suite (v17.13)](#-lyngsat-dx-master-suite---v1713)
2. [T2-MI Ultimate DX Generator (v15.5)](#-t2-mi-ultimate-dx-generator---v155)

---

# 🛰️ LyngSat DX Master Suite - (v17.13)

## 📖 Overview
**LyngSat DX Master Suite** is a high-performance, recursive web scraper designed to extract satellite transponder data and channel lineups from LyngSat.com. It is specifically engineered to handle **T2-MI (DVB-T2)** modulations, extracting complex PLP (Physical Layer Pipe) and ISI (Input Stream Identifier) data often missed by standard scrapers.

## ✨ Key Features
* **T2-MI Deep Scan:** Automatically detects and parses T2-MI markers (`PLP`, `Stream`, `PID`) to build accurate PID/PLP matrices.
* **Intelligent Filtering:** Automatically drops transponders that yield zero channels, ensuring clean output data.
* **Robust Link Detection:** Uses a multi-pass algorithm to find mux links (handling both absolute `/muxes/` paths and relative filenames).
* **C-Band Logic:** Automatically detects C-Band frequencies and applies the `+0.1` degree indexing standard.
* **URL History Management:** Saves processed satellites to `url.txt` with position labels, allowing for "Set and Forget" batch processing.
* **Smart Provider Extraction:** Prioritizes provider names from specific HTML headers to avoid capturing navigation noise.
* **Silent Auditing:** Keeps the console clean by hiding verbose "Queueing/Rejected" logs (viewable only in session logs).

## ⚙️ Requirements & Installation

* **Python:** 3.7+
* **OS:** Windows, Linux, or macOS.

The script relies on `curl_cffi` for robust TLS fingerprinting (to avoid bot detection) and `beautifulsoup4` for parsing.

```bash
pip install curl-cffi beautifulsoup4
```

To run the suite:

```bash
python "LYNGSAT DX MASTER SUITE.py"
```

## 📘 User Guide

Upon launching, you will be greeted with a banner and a menu:

1.  **Session Logging:** `❓ Enable session logging? (y/n)`
    * **Yes (`y`):** Creates a timestamped log file (e.g., `DX_LOG_20231027_123456.log`) recording every action.
    * **No (`n`):** Outputs only essential information to the console.
2.  **Source Selection:**
    * **Batch Mode:** Reads the `url.txt` file in the same directory. You can process specific satellites or all at once. If a position is provided (e.g., `...url, 78.5E`), it skips manual band selection.
    * **Manual Mode:** Paste URLs one by one. Press `Enter` on an empty line to finish.
3.  **Band Configuration (Manual Mode):**
    * **C-BAND (3000-4999 MHz):** Auto-suggested. You have 10 seconds to change the choice. C-Band is auto-indexed by `+0.1` degrees (e.g., `78.5E` -> `78.6E`).
    * **KU-BAND (10000+ MHz):** Auto-suggested.

### 🔍 The Scan Process
1.  **Discovery:** Scans the main page for frequency links.
2.  **Filtering:** Visits each Mux link. Rejects standard DVB-S2 immediately if no `PLP` markers are found.
3.  **Extraction:** Extracts the PID/PLP Matrix and Provider info.
4.  **Drill-Down & Verification:** Downloads the channel list and drops the frequency if it contains 0 channels.

## 📂 File Structure & CSV Output

The script generates a precise directory structure:

```text
<Script_Directory>/
├── url.txt                 # History of processed satellites
├── frequencies/            # Master frequency lists (e.g., f78.6E.csv)
├── channellist/            # Detailed channel lists
│   └── 78.6E/              # Folder per satellite
│       └── 3970H11664PLP0PID4097.csv  
└── DX_LOG_...log           # Session logs (if enabled)
```

### Frequency List (`frequencies/f[POS].csv`)

| Column | Description | Example |
| :--- | :--- | :--- |
| **Freq** | Frequency in MHz | `3970` |
| **Pol** | Polarization | `0` (0=H, 1=V, 2=L, 3=R) |
| **SR** | Symbol Rate | `11664` |
| **Pos** | Orbital Position | `78.6` |
| **pids-plps** | PID/PLP Matrix | `{4097,0;4099,2}` |
| **isi** | Input Stream Identifiers | `171,173` |
| **prov** | Provider Name | `MyProvider` |

*Note: Channel List CSVs are standard service lists containing SID, Name, and Type (1=TV, 2=Radio).*

---

# 📡 T2-MI Ultimate DX Generator - (v15.5)
> **Automated Edition**

## 📖 Overview
The **Universal Architect** is a Python-based console application designed to streamline the process of receiving T2-MI satellite feeds and converting them into standard HTTP streaming endpoints using Astra. It automates the creation of three critical components:

1.  **Enigma2 Database (`lamedb`):** Defines satellite transponders and services.
2.  **Bouquet Files (`.tv`):** Creates user-friendly channel lists.
3.  **Astra Configuration (`astra.conf`):** Scripts the T2-MI decapsulation logic.

## ⚙️ Prerequisites & Setup

* **Python:** 3.8+ recommended.
* **Dependencies:** `prompt_toolkit`. (The script attempts to auto-install this). If it fails, run:
    ```bash
    pip install prompt_toolkit
    ```

### Required Directory Structure
The script expects (and creates) the following environment:

```text
./
├── T2-MI Ultimate DX Generator.py
├── frequencies/              <-- INPUT: Your transponder CSVs (e.g., 8.1W.csv)
├── channellist/              <-- INPUT: Service lists per stream
│   └── 8.1W/
│       └── 3732L7325PLP0PID4097.csv
└── workspace/                <-- OUTPUT & CACHE
    ├── lamedb                <-- Generated Database
    ├── userbouquet.*.tv      <-- Generated Bouquet
    ├── astra/astra.conf      <-- Generated Astra Script
    └── architect.log         <-- Debug Log
```

## 📄 Input File Formats

### 1. Frequency CSVs (`frequencies/`)
Defines the physical satellite parameters. 
**Naming Convention:** `[Position][Dir].csv` (e.g., `8.1W.csv`). Sorting is automated (West -> East).

* **Required Columns:** `Freq`, `Pol` (H,V,L,R or 0,1,2,3), `SR`, `Pos`, `Dir` (W/E), `Inv` (2=Auto), `FEC` (9=Auto), `Sys` (1=DVB-S2), `Mod` (2=8PSK), `RO` (0), `Pilot` (2=Auto).
* **Optional Columns:** `prov` (Used to deduce Relay Path), `Provider` (Fallback), `isi`, `pids-plps` (e.g., `{pid,plp;pid,plp}`), `PID`, `PLP`.

### 2. Channel Lists (`channellist/`)
Maps the services inside the T2-MI stream. Headerless CSV format.
**Naming Convention:** `[Freq][Pol][SR]PLP[plp]PID[pid]_ISI[isi].csv` (e.g., `3732L7325PLP0PID4097_ISI171.csv`)

* **Col 1:** Service ID (Decimal)
* **Col 2:** Channel Name
* **Col 3:** Service Type (1=TV, 2=Radio) *(Optional)*

## 🔄 Operation Modes & Main Menu

Upon starting the script, select your desired workflow:

### Mode Selection
* **Mode A (Modify/Append):** Reads existing `workspace` files, adds new entries, prevents duplicates. Ideal for adding a new satellite.
* **Mode B (Fresh Start):** Wipes `lamedb`, `astra/`, and `*.tv` files to build a clean database. Preserves `.dx_history_*` and logs.

### Main Menu
1.  **Manual Entry:** Best for testing single transponders. You verify physical details, enter provider paths, and build manually.
2.  **Batch Import:** Processes a specific `.csv` file in `frequencies/` to create markers and services for that entire file.
3.  **Fully Automated Mode (One-Click):** Scans `frequencies/` West to East, processes every CSV, compiles outputs into `workspace/`, overwrites the source `lamedb`, and exits automatically.

## 🧠 Output Logic

* **Relay Path Deduction:** Automatically creates the URL path based on the `prov` column (e.g., "RTRS" -> `/rtrs/`, "Vidi Tv" -> `/viditv/`). Falls back to user input if unknown.
* **Service Naming:**
    * *Bouquet Marker:* `⚙ 8.1W-Provider@PID4096PLP0 [ISI 171 FEED]`
    * *Channel Name:* `▶ Channel Name`
* **Astra Configuration:** Generates two blocks per stream:
    1.  `make_t2mi_decap`: Listens to Enigma2 stream (`127.0.0.1:8001`).
    2.  `make_channel`: Outputs clean HTTP stream (`0.0.0.0:9999`).

## 📂 The File Manager
A custom CLI File Manager is used to select the target `lamedb`.
* **Up/Down Arrows:** Navigate.
* **Space:** Move selection down.
* **Enter:** Select item / Enter folder.
* **Escape:** Cancel and use default.

## 🚀 Workflow Example (Automated)
1. Prepare CSVs in `frequencies/` and service lists in `channellist/`.
2. Run `python "T2-MI Ultimate DX Generator (Automated Edition).py"`.
3. Choose **FRESH START**.
4. Select target `lamedb` (default is `workspace/lamedb`).
5. Choose **FULLY AUTOMATED MODE**.
6. Enter Default Provider.
7. Wait for `ALL FILES SYNCHRONIZED SUCCESSFULLY`.
8. Deploy `workspace/` contents to your receiver/server!

## ⚠️ Troubleshooting

| Issue | Quick Fix |
| :--- | :--- |
| **ImportError: prompt_toolkit** | Run `pip install prompt_toolkit` manually. |
| **File Manager freezes** | Press `Esc` to default or `Enter` to confirm. Ensure your terminal supports mouse/utf-8 input. |
| **Channels missing in Bouquet** | Check `channellist/` folder structure. Ensure filenames exactly match the `[Freq][Pol][SR]PLP...` format. |
| **lamedb didn't update** | Ensure the target `lamedb` selected matches your intended output location. Check file permissions. |
| **Service ID conflicts** | Use the "Starting SID" prompt to set a unique base ID (e.g., `8000`) if defaults overlap. |

---

*Disclaimer: These scripts are intended for educational and personal archival purposes. Data is sourced from publicly available information on LyngSat.com. Please respect their terms of service. The developers are not responsible for any misuse of this software.*
