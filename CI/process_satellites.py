import os
import re
import sys
import shutil
import argparse
import xml.etree.ElementTree as ET
from datetime import datetime

class SatellitesProcessor:
    def __init__(self, file_path, log_filename="process_satellites.log"):
        self.file_path = file_path
        self.log_filename = log_filename
        self.log_buffer = []

    def log_msg(self, message):
        timestamp = datetime.now().strftime("%H:%M:%S")
        entry = f"[{timestamp}] {message}"
        
        # Print to standard output so GitHub Actions captures it in the run logs
        print(entry)
        
        self.log_buffer.append(entry)
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
            self.log_msg(f"Backup created: {backup_name}")
        except Exception as e:
            self.log_msg(f"Warning: Backup failed - {e}")

    def verify_xml_integrity(self, filepath):
        """Parses the XML file to ensure it is well-formed."""
        self.log_msg(f"Running integrity check on {os.path.basename(filepath)}...")
        try:
            ET.parse(filepath)
            self.log_msg("✅ Integrity Check Passed: XML is well-formed.")
            return True
        except ET.ParseError as e:
            self.log_msg(f"❌ Integrity Check Failed: Malformed XML - {e}")
            return False
        except Exception as e:
            self.log_msg(f"❌ Integrity Check Failed: System Error - {e}")
            return False

    def run_process(self):
        if not self.file_path or not os.path.exists(self.file_path):
            self.log_msg(f"Error: File not found at {self.file_path}")
            sys.exit(1) # Fail the GitHub action if file is missing
        
        self.log_msg(f"Processing {self.file_path}...")
        
        # --- Full Conversion List ---
        conversions = [
            {"pos": "192", "new_name": "(1) 19.2E KU-band Astra 1KR/1M/1N/1P"},
            {"pos": "201", "new_name": "(100) 20.0E C-band Arabsat 5C"},
            {"pos": "215", "new_name": "(2) 21.5E KU-band Eutelsat 21B"},
            {"pos": "235", "new_name": "(3) 23.5E KU-band Astra 3B/3C"},
            {"pos": "255", "new_name": "(4) 25.5E KU-band Es'hail 1"},
            {"pos": "261", "new_name": "(101) 26.0E C-band Badr 5 / Badr 7/8 &amp; Es'hail 2"},
            {"pos": "260", "new_name": "(5) 26.0E KU-band Badr 5 / Badr 7/8 &amp; Es'hail 2"},
            {"pos": "283", "new_name": "(6) 28.3E KU-band Astra 2E/2F/2G"},
            {"pos": "305", "new_name": "(7) 30.5E KU-band Arabsat 5A/6A"},
            {"pos": "310", "new_name": "(8) 31.0E KU-band Türksat 5A"},
            {"pos": "330", "new_name": "(9) 33.0E KU-band Eutelsat 33F"},
            {"pos": "360", "new_name": "(10) 36.0E KU-band Eutelsat 36D &amp; Express AMU1"},
            {"pos": "382", "new_name": "(102) 38.1E C-band Paksat 1R/MM1"},
            {"pos": "381", "new_name": "(11) 38.1E KU-band Paksat 1R/MM1"},
            {"pos": "390", "new_name": "(12) 39.0E KU-band Hellas Sat 3/4"},
            {"pos": "401", "new_name": "(103) 40.0E C-band Express AM7"},
            {"pos": "400", "new_name": "(13) 40.0E KU-band Express AM7"},
            {"pos": "420", "new_name": "(14) 42.0E KU-band Türksat 3A/4A/5B/6A"},
            {"pos": "426", "new_name": "(104) 42.5E C-band NigComSat 1R"},
            {"pos": "425", "new_name": "(15) 42.5E KU-band NigComSat 1R"},
            {"pos": "452", "new_name": "(105) 45.1E C-band Cosmos 2520 &amp; Azerspace 2/Intelsat 38"},
            {"pos": "451", "new_name": "(16) 45.1E KU-band Cosmos 2520 &amp; Azerspace 2/Intelsat 38"},
            {"pos": "461", "new_name": "(106) 46.0E C-band Azerspace 1"},
            {"pos": "460", "new_name": "(17) 46.0E KU-band Azerspace 1"},
            {"pos": "491", "new_name": "(107) 49.0E C-band Yamal 601"},
            {"pos": "500", "new_name": "(18) 50.0E KU-band Türksat 4B"},
            {"pos": "516", "new_name": "(108) 51.5E C-band Belintersat 1"},
            {"pos": "515", "new_name": "(19) 51.5E KU-band Belintersat 1"},
            {"pos": "520", "new_name": "(20) 52.0E KU-band TurkmenÄlem/MonacoSat"},
            {"pos": "525", "new_name": "(21) 52.5E KU-band Al Yah 1"},
            {"pos": "530", "new_name": "(22) 53.0E KU-band Express AM6"},
            {"pos": "549", "new_name": "(23) 54.9E KU-band G-Sat 16 &amp; Yamal 402"},
            {"pos": "571", "new_name": "(109) 57.0E C-band NSS 12"},
            {"pos": "570", "new_name": "(24) 57.0E KU-band NSS 12"},
            {"pos": "585", "new_name": "(25) 58.5E KU-band KazSat 3"},
            {"pos": "621", "new_name": "(110) 62.0E C-band Intelsat 39"},
            {"pos": "620", "new_name": "(26) 62.0E KU-band Intelsat 39"},
            {"pos": "650", "new_name": "(27) 65.0E KU-band Amos 4"},
            {"pos": "661", "new_name": "(111) 66.0E C-band Intelsat 17"},
            {"pos": "660", "new_name": "(28) 66.0E KU-band Intelsat 17"},
            {"pos": "686", "new_name": "(112) 68.5E C-band Intelsat 20/36"},
            {"pos": "685", "new_name": "(29) 68.5E KU-band Intelsat 20/36"},
            {"pos": "705", "new_name": "(30) 70.5E KU-band Eutelsat 70B"},
            {"pos": "722", "new_name": "(113) 72.1E C-band Intelsat 22"},
            {"pos": "741", "new_name": "(114) 74.0E C-band G-Sat 7R / G-Sat 18"},
            {"pos": "740", "new_name": "(31) 74.0E KU-band G-Sat 7R / G-Sat 18"},
            {"pos": "751", "new_name": "(115) 75.0E C-band ABS 2/2A"},
            {"pos": "750", "new_name": "(32) 75.0E KU-band ABS 2/2A"},
            {"pos": "766", "new_name": "(116) 76.5E C-band Apstar 7"},
            {"pos": "765", "new_name": "(33) 76.5E KU-band Apstar 7"},
            {"pos": "786", "new_name": "(117) 78.5E C-band Thaicom 6/8"},
            {"pos": "785", "new_name": "(34) 78.5E KU-band Thaicom 6/8"},
            {"pos": "800", "new_name": "(35) 80.0E KU-band Express 80"},
            {"pos": "831", "new_name": "(118) 83.0E C-band G-Sat 10/24/30"},
            {"pos": "830", "new_name": "(36) 83.0E KU-band G-Sat 10/24/30"},
            {"pos": "865", "new_name": "(37) 86.5E KU-band KazSat 2"},
            {"pos": "876", "new_name": "(119) 87.5E C-band ChinaSat 12"},
            {"pos": "881", "new_name": "(120) 88.0E C-band ST 2"},
            {"pos": "880", "new_name": "(38) 88.0E KU-band ST 2"},
            {"pos": "901", "new_name": "(121) 90.0E C-band Yamal 401"},
            {"pos": "900", "new_name": "(39) 90.0E KU-band Yamal 401"},
            {"pos": "916", "new_name": "(122) 91.5E C-band Measat 3b/3d"},
            {"pos": "915", "new_name": "(40) 91.5E KU-band Measat 3b/3d"},
            {"pos": "922", "new_name": "(41) 92.2E KU-band ChinaSat 9 / ChinaSat 9C"},
            {"pos": "936", "new_name": "(123) 93.5E C-band G-Sat 15/17"},
            {"pos": "935", "new_name": "(42) 93.5E KU-band G-Sat 15/17"},
            {"pos": "950", "new_name": "(43) 95.0E KU-band SES 8 / SES 12"},
            {"pos": "966", "new_name": "(124) 96.5E C-band Express 103"},
            {"pos": "973", "new_name": "(44) 97.3E KU-band G-Sat 9"},
            {"pos": "981", "new_name": "(125) 98.0E C-band ChinaSat 11"},
            {"pos": "1006", "new_name": "(126) 100.5E C-band AsiaSat 5"},
            {"pos": "1005", "new_name": "(45) 100.5E KU-band AsiaSat 5"},
            {"pos": "1014", "new_name": "(46) 101.4E KU-band ChinaSat 9B"},
            {"pos": "1031", "new_name": "(127) 103.0E C-band Express AMU3"},
            {"pos": "1030", "new_name": "(47) 103.0E KU-band Express AMU3"},
            {"pos": "1055", "new_name": "(128) 105.4E C-band AsiaSat 7/8"},
            {"pos": "1054", "new_name": "(48) 105.4E KU-band AsiaSat 7/8"},
            {"pos": "1082", "new_name": "(129) 108.1E C-band SES 7/9 &amp; Merah Putih"},
            {"pos": "1081", "new_name": "(49) 108.1E KU-band SES 7/9 &amp; Merah Putih"},
            {"pos": "-451", "new_name": "(130) 45.0W C-band Intelsat 14"},
            {"pos": "-450", "new_name": "(50) 45.0W KU-band Intelsat 14"},
            {"pos": "-431", "new_name": "(51) 43.1W KU-band Sky Brasil 1"},
            {"pos": "-406", "new_name": "(131) 40.5W C-band SES 6"},
            {"pos": "-405", "new_name": "(52) 40.5W KU-band SES 6"},
            {"pos": "-375", "new_name": "(132) 37.4W C-band NSS 10 / Telstar 11N"},
            {"pos": "-374", "new_name": "(53) 37.4W KU-band NSS 10 / Telstar 11N"},
            {"pos": "-346", "new_name": "(133) 34.5W C-band Intelsat 35e"},
            {"pos": "-345", "new_name": "(54) 34.5W KU-band Intelsat 35e"},
            {"pos": "-300", "new_name": "(55) 30.0W KU-band SpainSat / Hispasat 30W-5/30W-6"},
            {"pos": "-245", "new_name": "(56) 24.5W KU-band Astra 1L / Alcomsat 1"},
            {"pos": "-221", "new_name": "(134) 22.0W C-band SES 4"},
            {"pos": "-220", "new_name": "(57) 22.0W KU-band SES 4"},
            {"pos": "-181", "new_name": "(135) 18.0W C-band Intelsat 37e"},
            {"pos": "-150", "new_name": "(58) 15.0W KU-band Telstar 12 Vantage"},
            {"pos": "-141", "new_name": "(136) 14.0W C-band Express AM8"},
            {"pos": "-140", "new_name": "(59) 14.0W KU-band Express AM8"},
            {"pos": "-111", "new_name": "(137) 11.0W C-band Express AM44"},
            {"pos": "-81", "new_name": "(138) 8.0W C-band Eutelsat 8 West B"},
            {"pos": "-80", "new_name": "(60) 8.0W KU-band Eutelsat 8 West B"},
            {"pos": "-71", "new_name": "(61) 7.1W KU-band Nilesat 201/301 &amp; Eutelsat 7 West A"},
            {"pos": "-50", "new_name": "(62) 5.0W KU-band Eutelsat 5 West B"},
            {"pos": "-40", "new_name": "(63) 4.0W KU-band Amos 3 &amp; Dror 1"},
            {"pos": "-31", "new_name": "(139) 3.0W C-band ABS 3A"},
            {"pos": "-30", "new_name": "(64) 3.0W KU-band ABS 3A"},
            {"pos": "-9", "new_name": "(140) 0.8W C-band Thor 5/6/7 &amp; Intelsat 10-02"},
            {"pos": "-8", "new_name": "(65) 0.8W KU-band Thor 5/6/7 &amp; Intelsat 10-02"},
            {"pos": "19", "new_name": "(66) 1.9E KU-band BulgariaSat 1"},
            {"pos": "31", "new_name": "(141) 3.0E C-band Eutelsat 3B &amp; Rascom QAF 1R"},
            {"pos": "30", "new_name": "(67) 3.0E KU-band Eutelsat 3B &amp; Rascom QAF 1R"},
            {"pos": "50", "new_name": "(142) 4.9E C-band Astra 4A &amp; SES 5"},
            {"pos": "49", "new_name": "(68) 4.9E KU-band Astra 4A &amp; SES 5"},
            {"pos": "70", "new_name": "(69) 7.0E KU-band Eutelsat 7B/7C"},
            {"pos": "90", "new_name": "(70) 9.0E KU-band Eutelsat 9B &amp; Ka-Sat 9A"},
            {"pos": "101", "new_name": "(143) 10.0E C-band Eutelsat 10B"},
            {"pos": "100", "new_name": "(71) 10.0E KU-band Eutelsat 10B"},
            {"pos": "130", "new_name": "(72) 13.0E KU-band Hotbird 13F/13G"},
            {"pos": "160", "new_name": "(73) 16.0E KU-band Eutelsat 16A"},
            {"pos": "171", "new_name": "(144) 17.0E C-band Amos 17"},
            {"pos": "170", "new_name": "(74) 17.0E KU-band Amos 17"}
        ]

        try:
            # Always back up the file prior to overriding in the workflow
            self._backup_file(self.file_path, "pre_replace")

            with open(self.file_path, 'r', encoding='iso-8859-1') as f:
                lines = f.readlines()

            new_lines = []
            skip_block = False
            rename_count = 0
            header_updated = False
            
            # --- Trimming Markers ---
            trim1_start_marker = 'position="-1771"'
            trim1_end_keep_marker = 'position="-451"'
            trim2_start_delete_marker = 'position="1082"'
            trim2_end_keep_marker = '</satellites>'

            for line in lines:
                # 1. XML Header Transformation
                if '<?xml' in line and 'encoding="UTF-8"' in line:
                    line = line.replace('encoding="UTF-8"', 'encoding="iso-8859-1"')
                    header_updated = True

                # 2. Renaming Logic
                if '<sat' in line:
                    for item in conversions:
                        if f'position="{item["pos"]}"' in line:
                            new_line = re.sub(r'name=".*?"', f'name="{item["new_name"]}"', line)
                            if new_line != line:
                                rename_count += 1
                                line = new_line
                            break

                # 3. Trimming Logic
                if trim1_start_marker in line and '<sat' in line:
                    skip_block = True
                if trim1_end_keep_marker in line and '<sat' in line:
                    skip_block = False
                if trim2_start_delete_marker in line and '<sat' in line:
                    skip_block = True
                if trim2_end_keep_marker in line:
                    skip_block = False

                if not skip_block:
                    new_lines.append(line)

            # Modify the same file directly
            output_path = self.file_path

            # Save file
            with open(output_path, 'w', encoding='iso-8859-1') as f:
                f.writelines(new_lines)

            # Integrity Check
            is_valid = self.verify_xml_integrity(output_path)
            
            # Final Logging
            if header_updated:
                self.log_msg("Updated XML header encoding declaration.")
            
            if not is_valid:
                self.log_msg("⚠️ WARNING: The output file contains syntax errors.")
                sys.exit(1) # Fail workflow to prevent bad XML from being committed
            
            self.log_msg(f"✅ Process Complete. Renamed {rename_count} satellites.")
            self.log_msg(f"Original file replaced in place: {self.file_path}")

        except Exception as e:
            self.log_msg(f"❌ Error: {e}")
            sys.exit(1)

if __name__ == "__main__":
    # Setup Argument Parser for CLI usage
    parser = argparse.ArgumentParser(description="Headless Satellites XML Processor")
    parser.add_argument("file", help="Path to the satellites.xml file to process")
    args = parser.parse_args()

    # Run the processor
    processor = SatellitesProcessor(args.file)
    processor.run_process()
