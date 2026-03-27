#!/bin/sh
# ==============================================================================
# Script: Update satellites.xml
# Purpose: Fetches the latest satellites.xml and deploys it to Enigma2 directories
# ==============================================================================

# Helper Text: Define the source URL for the satellites.xml file.
# Note: Ensure the URL points to the raw file for a direct download.
URL="https://github.com/ahmedmoselhi/e2_channellist/raw/refs/heads/scripts/satellites.xml"

# Helper Text: Define the temporary download location.
TMP_FILE="/tmp/satellites.xml"

# Helper Text: Define the target destination paths for Enigma2 and Tuxbox.
DEST1="/etc/enigma2/satellites.xml"
DEST2="/etc/tuxbox/satellites.xml"

# Helper Text: Step 1 - Fetch the file and save it to the temporary directory.
# The '-q' flag keeps the output quiet, and '-O' directs it to the specific file.
echo "Downloading satellites.xml to /tmp..."
wget -qO "$TMP_FILE" "$URL"

# Helper Text: Verify if the download was successful before proceeding.
# The '-f' checks if the file exists, and '-s' checks if it has a size greater than zero.
if [ -f "$TMP_FILE" ] && [ -s "$TMP_FILE" ]; then
    echo "Download successful. Proceeding with deployment."

    # Helper Text: Step 2 - Copy the file to the required Enigma2 locations.
    # Overwrites any existing files in those locations automatically.
    cp "$TMP_FILE" "$DEST1"
    cp "$TMP_FILE" "$DEST2"

    echo "File successfully copied to /etc/enigma2 and /etc/tuxbox."

    # Helper Text: Clean up the temporary file after successful deployment to free up space.
    rm "$TMP_FILE"
else
    echo "Error: Failed to download the file or the file is empty."
    exit 1
fi

# Helper Text: Script execution completed successfully.
echo "Update process finished."
exit 0
