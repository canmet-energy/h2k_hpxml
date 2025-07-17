import os
import subprocess
import sys
import configparser
from configparser import NoOptionError, NoSectionError

# Add project root to path so we can import from src
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, project_root)

from src.h2k_hpxml.analysis import annual

config = configparser.ConfigParser()
config.read(os.path.join(project_root, "conversionconfig.ini"))

source_h2k_path = config.get("paths", "source_h2k_path")
hpxml_os_path = config.get("paths", "hpxml_os_path")
dest_hpxml_path = config.get("paths", "dest_hpxml_path")

try:
    flags = config.get("simulation", "flags")

except (NoOptionError, NoSectionError):
    flags = ""
print("flags", flags)


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


# result = run_hpxml_os("base.xml", "workflow/translated_h2ks")
# filename = "NRCan-arch1_1000sf_1storey_fullBsmt.xml"
filename = "SimpleBoxModel-USpec.xml"
result = run_hpxml_os(filename, "workflow/translated_h2ks")


# print("result:", result)
# # print("output:", result.output)
