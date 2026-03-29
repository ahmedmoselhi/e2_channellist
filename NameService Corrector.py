import os
import sys

def normalize_to_impl2(ns_hex):
	try:
		# Parse the hex string to an integer
		ns_int = int(ns_hex, 16)
		
		# Extract the upper 16 bits (Orbital Position)
		upper = ns_int >> 16
		
		# DETECT IF IT IS IMPL 1 (Two's Complement / DreamBoxEdit style)
		# If it's a high value like 0xFFAF (65455), it's a negative 
		# Two's Complement value (West).
		if 1800 < upper < 64000:
			# It's already Impl 2 West (e.g., 3519 for 8.1W)
			# or an East position (e.g., 192 for 19.2E). 
			new_upper = upper
		elif upper >= 64000:
			# It's Impl 1 West (Two's Complement). 
			# Convert to tenths (e.g., 65455 -> -81)
			tenths = upper - 65536
			# Convert -81 to Impl 2 (3600 - 81 = 3519)
			new_upper = 3600 + tenths 
		else:
			# It's an East position (0 to 1800)
			new_upper = upper

		# Reconstruct the namespace
		# Preserve the lower 16 bits (frequency/flags) to maintain service links
		lower = ns_int & 0xFFFF
		normalized_int = (new_upper << 16) | lower
		
		return format(normalized_int, '08x').lower()
	except:
		return ns_hex

def process_lamedb(file_path):
	"""
	Processes the lamedb file to normalize all namespaces to Implementation 2.
	:param file_path: Path to the lamedb file to be processed.
	"""
	if not os.path.exists(file_path):
		print("Error: File '%s' not found." % file_path)
		return

	print("Processing: %s" % file_path)
	
	try:
		with open(file_path, 'r') as f:
			lines = f.readlines()
	except Exception as e:
		print("Error reading file: %s" % str(e))
		return

	output_lines = []
	section = None # 'tp' for transponders, 'svc' for services

	for line in lines:
		line_s = line.strip()
		
		# Section Tracking
		if line_s == "transponders":
			section = "tp"
			output_lines.append(line)
			continue
		elif line_s == "services":
			section = "svc"
			output_lines.append(line)
			continue
		elif line_s == "end":
			section = None
			output_lines.append(line)
			continue

		# Process Transponder Keys (format: namespace:tsid:onid)
		if section == "tp" and ":" in line_s and not line_s.startswith("/"):
			parts = line_s.split(":")
			if len(parts) >= 3:
				parts[0] = normalize_to_impl2(parts[0])
				output_lines.append(":".join(parts) + "\n")
			else:
				output_lines.append(line)
		
		# Process Service References (format: sid:namespace:tsid:onid:type:num)
		elif section == "svc" and ":" in line_s:
			parts = line_s.split(":")
			if len(parts) > 1:
				parts[1] = normalize_to_impl2(parts[1])
				output_lines.append(":".join(parts) + "\n")
			else:
				output_lines.append(line)
		
		else:
			output_lines.append(line)

	# Generate output filename (e.g., lamedb -> lamedb.fixed)
	output_path = file_path + ".fixed"
	try:
		with open(output_path, 'w') as f:
			f.writelines(output_lines)
		print("Success! Normalized file created at: %s" % output_path)
	except Exception as e:
		print("Error writing file: %s" % str(e))

if __name__ == "__main__":
	# Usage: python script.py /path/to/lamedb
	if len(sys.argv) > 1:
		target_file = sys.argv[1]
	else:
		# Default fallback if no argument is provided
		target_file = "lamedb"
	
	process_lamedb(target_file)
