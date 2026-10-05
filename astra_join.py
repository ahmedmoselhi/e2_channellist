import os


def join_astra_files():
    file1_path = "astra.part1"
    file2_path = "astra.part2"
    output_path = "astra.conf"

    # Read content from the first part
    with open(file1_path, "r", encoding="utf-8") as f1:
        content1 = f1.read()

    # Read content from the second part
    with open(file2_path, "r", encoding="utf-8") as f2:
        content2 = f2.read()

    # Join contents separated by two empty lines (\n\n\n)
    merged_content = (
        content1.rstrip("\r\n") + "\n\n\n" + content2.lstrip("\r\n")
    )

    # Overwrite astra.conf with the merged content
    with open(output_path, "w", encoding="utf-8") as fout:
        fout.write(merged_content)


if __name__ == "__main__":
    join_astra_files()