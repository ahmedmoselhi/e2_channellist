import os

def sort_satellite_file(filename):
    if not os.path.exists(filename):
        print(f"Error: {filename} not found.")
        return

    # 1. Read the data
    with open(filename, 'r') as f:
        # filter(None, ...) removes any empty lines at the end of the file
        lines = [line.strip() for line in f if line.strip()]

    def get_coordinate_value(line):
        try:
            # Extract coordinate (e.g., "18.1W")
            coord_str = line.split(',')[-1].strip()
            # Separate number from direction
            value = float(coord_str[:-1])
            direction = coord_str[-1].upper()
            
            # West is negative, East is positive
            return -value if direction == 'W' else value
        except (ValueError, IndexError):
            # If a line is malformed, we keep it at the end (or skip it)
            return float('inf')

    # 2. Sort the data
    sorted_lines = sorted(lines, key=get_coordinate_value)

    # 3. Write back to the same file
    with open(filename, 'w') as f:
        for line in sorted_lines:
            f.write(line + '\n')
    
    print(f"Successfully sorted {len(sorted_lines)} entries in {filename}.")

# Execute the script
if __name__ == "__main__":
    sort_satellite_file('url.txt')
