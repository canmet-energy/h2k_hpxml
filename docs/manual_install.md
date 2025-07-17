Translator functions to convert h2k files to HPXML format, run files via OpenStudio workflow, and compare results.

Compatible Software Versions:
HOT2000 v11.10, v11.11 and v11.12
OpenStudio 3.9.0 - https://github.com/NREL/OpenStudio/releases/tag/v3.9.0
OpenStudio-HPXML 1.9.1 - https://github.com/NREL/OpenStudio-HPXML/releases


# Setup
1. Ensure that the software versions above are installed
2. Add "C:/openstudio-3.9.0/bin to your PATH environment variables, and ensure no older versions of OS are referenced. 
3. Clone or download this repository
4. Download the required CWEC .epw weather files for Canada or by province (https://climate.weather.gc.ca/prods_servs/engineering_e.html)
5. Add the Canadian weather files to the "weather" folder in the OpenStudio-HPXML directory (e.g. C:\OpenStudio-HPXML-v1.9.1\OpenStudio-HPXML\weather)



### conversionconfig.ini
Use the conversionconfig.ini to specify the file or folder path of the h2k file(s) you would like to convert to HPXML.
This file can also be used to define non-h2k parameters for the translation process.


# Running the translator
1. Ensure the virtual environment is activated (run `.\.venv\Scripts\Activate.ps1`) and the required packages are installed (`pip install -r .\requirements.txt`)
2. Run the CLI tool (`h2k2hpxml run`) to translate and simulate H2K files with full options, or use `python scripts/compare.py` for legacy config-based batch processing
3. Run legacy simulation script (`python scripts/run.py`) to run specific HPXML files through OpenStudio workflow (prefer h2k2hpxml CLI)
4. Run simulateh2k.py (`py simulateh2k.py`) to translate a file and simulate it using the HPXML-OS workflow
