import os
import subprocess
import json
import configparser
from configparser import NoOptionError, NoSectionError


from h2ktohpxml import h2ktohpxml
from analysis import annual

config = configparser.ConfigParser()
config.read("conversionconfig.ini")

source_h2k_path = config.get("paths", "source_h2k_path")
hpxml_os_path = config.get("paths", "hpxml_os_path")
dest_hpxml_path = config.get("paths", "dest_hpxml_path")
dest_compare_data = config.get("paths", "dest_compare_data")

try:
    flags = config.get("simulation", "flags")

except (NoOptionError, NoSectionError):
    flags = ""
print("flags", flags)


# Determine whether to process as folder or single file
if ".h2k" in source_h2k_path.lower():
    # Single file
    # convert to array for consistent processing
    print("single file")
    h2k_files = [source_h2k_path]
else:
    # Folder
    # List folder and append to source path
    print("folder")
    h2k_files = [f"{source_h2k_path}/{x}" for x in os.listdir(source_h2k_path)]

print("h2k_files", h2k_files)


def run_hpxml_os(file="", path=""):
    path_to_log = f"{hpxml_os_path}/{path}/run"
    success = False
    result = {}
    try:
        result = subprocess.run(
            f"openstudio workflow/run_simulation.rb -x {path}/{file} {flags}",
            cwd=hpxml_os_path,
            check=True,
            # capture_output=True,
            # text=True,
        )
        success = True

    except subprocess.CalledProcessError:
        print("Error in input file, check logs")

    finally:
        return {"result": result, "success": success, "path_to_log": path_to_log}


print("h2k_files", h2k_files)
compare_dict_out = {}
for filepath in h2k_files:
    print("filepath", filepath)
    h2k_filename = filepath.split("/")[-1]
    hpxml_filename = h2k_filename.replace(".h2k", ".xml").replace(".H2K", ".xml")
    print(h2k_filename)

    try:
        with open(filepath, "r", encoding="utf-8") as f:
            h2k_string = f.read()

        hpxml_string = h2ktohpxml(h2k_string)

        with open(f"{hpxml_os_path}/{dest_hpxml_path}/{hpxml_filename}", "w") as f:
            f.write(hpxml_string)

        result = run_hpxml_os(hpxml_filename, dest_hpxml_path)

        print(result)
        os_results = annual.read_os_results(
            f"{hpxml_os_path}{dest_hpxml_path}", return_type="dict"
        )

        if os_results.get("Energy Use: Total (MBtu)", 0) == 0:
            # no results generated, check logs
            with open(
                f"{hpxml_os_path}{dest_hpxml_path}run/run.log", "r", encoding="utf-8"
            ) as f:
                logs_string = f.read()

            compare_dict_out[h2k_filename] = logs_string
            continue

        h2k_results, weather_location = annual.read_h2k_results(filepath)

        compare_dict = annual.compare_os_h2k_annual(h2k_results, os_results)
        compare_dict["location"] = weather_location

        compare_dict_out[h2k_filename] = compare_dict

    except Exception as error:
        compare_dict_out[h2k_filename] = {"error": f"{error}"}

print("DONE")
# print(compare_dict_out)


with open(f"{dest_compare_data}/compare_data.json", "w") as f:
    json.dump(compare_dict_out, f, indent=4)
