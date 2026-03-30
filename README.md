# 🛰️ Satellite DX Toolchain

[![Python 3.7+](https://img.shields.io/badge/python-3.7+-blue.svg)](https://www.python.org/downloads/)
[![Platform](https://img.shields.io/badge/platform-Windows%20%7C%20Linux%20%7C%20macOS-lightgrey)]()
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

This repository contains scraping, transformation, generation, and utility tools for Enigma2 satellite workflows.

---

## 📑 Table of Contents
1. [Quick Start](#-quick-start)
2. [Script Catalog (Detailed)](#-script-catalog-detailed)
3. [Input/Output Directory Expectations](#-inputoutput-directory-expectations)
4. [Typical End-to-End Workflow](#-typical-end-to-end-workflow)
5. [Troubleshooting](#-troubleshooting)

---

## 🚀 Quick Start

Install common dependencies first:

```bash
pip install beautifulsoup4 requests cloudscraper curl-cffi prompt_toolkit
```

For GUI tooling:

```bash
pip install PySide6
```

Launch all major modules from one menu:

```bash
python launcher.py
```

---

## 📚 Script Catalog (Detailed)

> Each entry below includes: purpose, required parameters, exact execution command, and expected results.

### 1) `launcher.py`

**Purpose**
- Main command center to launch major modules:
  - LyngSat DX Master Suite
  - T2-MI Generator
  - URL sorter
  - Enigma2 Suite GUI

**Required parameters**
- None.

**How to execute**
```bash
python launcher.py
```

**Expected results**
- Interactive terminal menu appears.
- Selecting a module runs the target script.
- After completion, you can return to menu, reload the same module, or quit.

---

### 2) `LYNGSAT DX MASTER SUITE.py`

**Purpose**
- Deep LyngSat scraper for T2-MI-aware transponder extraction.
- Produces frequency CSVs and per-stream channel lists.

**Required parameters**
- None via CLI arguments.
- Runtime interactive inputs are required:
  - Logging on/off
  - Batch/manual source selection
  - URL input (manual mode)
  - Band selection if needed

**How to execute**
```bash
python "LYNGSAT DX MASTER SUITE.py"
```

**Expected results**
- Creates/updates:
  - `url.txt`
  - `frequencies/f*.csv`
  - `channellist/<position>/*.csv`
  - Optional `DX_LOG_*.log`
- Skips transponders that resolve to zero channels.

---

### 3) `T2-MI Ultimate DX Generator (Automated Edition).py`

**Purpose**
- Converts scraped frequency/channel inputs into:
  - `lamedb`
  - bouquet files
  - `astra.conf`

**Required parameters**
- None via CLI arguments.
- Runtime interactive inputs are required (mode selection, file paths, provider defaults, etc.).

**How to execute**
```bash
python "T2-MI Ultimate DX Generator (Automated Edition).py"
```

**Expected results**
- Creates/updates `workspace/` outputs including Enigma2 database artifacts and Astra config.
- Supports append mode and fresh rebuild mode.

---

### 4) `Url.txt Order.py`

**Purpose**
- Sorts `url.txt` entries by orbital coordinate (West to East).

**Required parameters**
- None (always targets `url.txt` in current working directory).

**How to execute**
```bash
python "Url.txt Order.py"
```

**Expected results**
- `url.txt` is rewritten in sorted order.
- Console reports count of sorted entries.

---

### 5) `Satellites.xml-Scraper.py`

**Purpose**
- Interactive LyngSat-to-`satellites.xml` scraper.
- Supports position range selection, C/KU separation, and advanced MIS/PLS/T2-MI fields.

**Required parameters**
- None via CLI arguments.
- Runtime interactive inputs are required:
  - Start position (default `45.0W`)
  - End position (default `108.2E`)
  - Separate C/KU bands (Y/N)
  - Include advanced params (Y/N)

**How to execute**
```bash
python "Satellites.xml-Scraper.py"
```

**Expected results**
- Writes `satellites.xml` in the current directory.
- Outputs operation summary with total satellites and transponders.

---

### 6) `Enigma2 Suite.py`

**Purpose**
- Desktop GUI (PySide6) with two major tools:
  - Lamedb merger
  - satellites.xml processor

**Required parameters**
- None.
- Runtime GUI selection of input/output files is required.

**How to execute**
```bash
python "Enigma2 Suite.py"
```

**Expected results**
- Opens a maximized GUI window.
- Generates merged/processed files based on tab operations.
- Writes timestamped logs (e.g., `enigma2_suite_*.log`).

---

### 7) `NameService Corrector.py`

**Purpose**
- Normalizes lamedb namespace format to implementation-2 style.

**Required parameters**
- Optional positional path argument:
  - `python "NameService Corrector.py" /path/to/lamedb`
- If omitted, defaults to `lamedb` in current directory.

**How to execute**
```bash
python "NameService Corrector.py" /path/to/lamedb
```

or

```bash
python "NameService Corrector.py"
```

**Expected results**
- Creates a new file beside source: `<original>.fixed`.
- Original source file remains unchanged.

---

### 8) `Password Generator.py`

**Purpose**
- Interactive password generator constrained to a limited character set.

**Required parameters**
- None.

**How to execute**
```bash
python "Password Generator.py"
```

**Expected results**
- Interactive menu allows length/type toggles.
- Generates and prints a password.

---

### 9) `CI/orion_ci.py`

**Purpose**
- Non-interactive/CI version of satellites scraping to produce `satellites.xml`.

**Required parameters**
- All parameters are optional (script has defaults):
  - `--start` (default: `45.0W`)
  - `--end` (default: `108.2E`)
  - `--separate` (flag)
  - `--advanced` (flag)

**How to execute**
```bash
python CI/orion_ci.py --start 45.0W --end 108.2E --separate --advanced
```

**Expected results**
- Writes `satellites.xml` in current working directory.
- Suitable for automation pipelines.

---

### 10) `CI/process_satellites.py`

**Purpose**
- Post-processes an existing `satellites.xml`:
  - renames satellites based on position map
  - trims predefined position blocks
  - validates XML integrity

**Required parameters**
- One required positional argument:
  - path to target XML file

**How to execute**
```bash
python CI/process_satellites.py satellites.xml
```

**Expected results**
- Modifies the provided XML in place.
- Creates backup file under sibling `backups/` directory.
- Fails with non-zero exit code if output XML is malformed.

---

### 11) `E2/update_channellist_tuner.py`

**Purpose**
- Receiver-side maintenance utility for Enigma2 images:
  - full channel update from GitHub ZIP
  - tuner config backup
  - advanced tuner setup injection
  - Astra config update

**Required parameters**
- None via CLI.
- Runtime menu/input required.
- Must run in an environment where `/etc/enigma2`, `/etc/tuxbox`, and `/etc/astra` exist and where `init 3/4` is available.

**How to execute**
```bash
python E2/update_channellist_tuner.py
```

**Expected results**
- Depending on selected option:
  - updates `/etc/enigma2/lamedb` and bouquet files
  - writes `/etc/enigma2/backups/*`
  - updates `/etc/astra/astra.conf`
  - restarts Enigma2 service via init commands

---

## 📂 Input/Output Directory Expectations

Common directories used by these tools:

```text
./
├── frequencies/                 # Input/Output transponder CSVs
├── channellist/                 # Per-satellite service CSVs
├── workspace/                   # Generator outputs and history
├── CI/                          # Automation-friendly scripts
└── E2/                          # Receiver-side maintenance scripts
```

---

## 🔄 Typical End-to-End Workflow

1. Scrape data from LyngSat:
   - `python "LYNGSAT DX MASTER SUITE.py"`
2. (Optional) Sort history input file:
   - `python "Url.txt Order.py"`
3. Generate Enigma2 + Astra artifacts:
   - `python "T2-MI Ultimate DX Generator (Automated Edition).py"`
4. (Optional) Build/refresh `satellites.xml`:
   - interactive: `python "Satellites.xml-Scraper.py"`
   - CI: `python CI/orion_ci.py ...`
5. (Optional) Post-process satellites naming profile:
   - `python CI/process_satellites.py satellites.xml`
6. Deploy to receiver and optionally run:
   - `python E2/update_channellist_tuner.py`

---

## ⚠️ Troubleshooting

- **`ModuleNotFoundError`**: install missing dependency with `pip` (see Quick Start).
- **GUI fails to start**: ensure `PySide6` and desktop/X11/Wayland environment are available.
- **No channels generated**: verify naming conventions under `frequencies/` and `channellist/`.
- **Receiver script fails on desktop PC**: `E2/update_channellist_tuner.py` is designed for Enigma2 filesystem/service layout.
- **CI XML processing fails**: validate input XML and check `process_satellites.log`.

---

*Disclaimer: These scripts are intended for educational and personal archival purposes. Data is sourced from publicly available information. Please respect upstream data provider terms of service.*
