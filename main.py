import os
import sys
import configparser
from src.h2k_hpxml import h2ktohpxml

# print("Hello from main.py")

config = configparser.ConfigParser()
config.read("conversionconfig.ini")
# print(config.sections())

source_h2k_path = config.get("paths", "source_h2k_path")
hpxml_os_path = config.get("paths", "hpxml_os_path")
dest_hpxml_path = config.get("paths", "dest_hpxml_path")


try:
    translation_mode = config.get("translation", "mode")
except:
    translation_mode = "SOC"


# print(config.get("nonh2k", "operable_window_avail_days"))

# if __name__ == "__main__":
#     print("name is main")
#     try:
#         sourcepath = sys.argv[1]
#     except IndexError:
#         pass
#     print("sourcepath: " + sourcepath)


# Determine whether to process as folder or single file
if ".h2k" in source_h2k_path.lower():
    # Single file
    # convert to array for consistent processing
    # print("single file")
    h2k_files = [source_h2k_path]
else:
    # Folder
    # List folder and append to source path
    # print("folder")
    h2k_files = [f"{source_h2k_path}/{x}" for x in os.listdir(source_h2k_path)]

print("H2k Files:", h2k_files)

for filepath in h2k_files:
    print("================================================")
    print("File Path: ", filepath)

    with open(filepath, "r", encoding="utf-8") as f:
        h2k_string = f.read()

    hpxml_string = h2ktohpxml(h2k_string, {"translation_mode": translation_mode})

    # with open(f"./tests/files/{filepath.split("/")[-1].replace(".h2k",".xml")}", "w") as f:

    with open(
        f"{hpxml_os_path}/{dest_hpxml_path}/{filepath.split("/")[-1].replace(".h2k",".xml").replace(".H2K",".xml").replace(" ","-")}",
        "w",
    ) as f:
        f.write(hpxml_string)
