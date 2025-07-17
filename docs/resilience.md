# Resilience CLI Tool - Quick Start Guide

## Overview

The Resilience CLI tool (`src/h2k_hpxml/cli/resilience.py`) analyzes building resilience by creating four scenarios that examine clothing factors and HVAC performance during power outages and extreme weather conditions. The tool converts H2K files to OpenStudio models and generates comprehensive resilience analysis outputs.

## Prerequisites

Before using the resilience tool, ensure you have:

1. **OpenStudio Python Bindings** - Required for model manipulation
2. **OpenStudio-HPXML** - Required for H2K to OSM conversion (must be installed at `/OpenStudio-HPXML/`)
3. **Python Dependencies** - Install via: `pip install -r requirements.txt`

The tool will automatically validate these dependencies and exit with clear error messages if they're missing.

## Quick Start

### Basic Usage

```bash
# Analyze a single H2K file (creates models only)
python src/h2k_hpxml/cli/resilience.py path/to/your/file.h2k

# Specify custom output location
python src/h2k_hpxml/cli/resilience.py path/to/your/file.h2k --output-path /custom/output/directory

# Run with full simulations
python src/h2k_hpxml/cli/resilience.py path/to/your/file.h2k --run-simulation
```

### Example Usage

```bash
# Basic analysis of example file
python src/h2k_hpxml/cli/resilience.py examples/WizardHouse.h2k --output-path examples

# Custom analysis with 14-day outage and different clothing factors
python src/h2k_hpxml/cli/resilience.py examples/WizardHouse.h2k \
  --output-path examples \
  --outage-days 14 \
  --clothing-factor-summer 0.3 \
  --clothing-factor-winter 1.2

# Full analysis with simulations
python src/h2k_hpxml/cli/resilience.py examples/WizardHouse.h2k \
  --output-path examples \
  --run-simulation
```

## Command Line Options

| Parameter | Type | Default | Range | Description |
|-----------|------|---------|-------|-------------|
| `h2k_path` | Required | - | - | Path to H2K XML file |
| `--outage-days` | Optional | 7 | 0-365 | Number of days for power outage analysis |
| `--output-path` | Optional | Same as H2K file | - | Output folder path |
| `--clothing-factor-summer` | Optional | 0.5 | 0.0-2.0 | Summer clothing insulation factor |
| `--clothing-factor-winter` | Optional | 1.0 | 0.0-2.0 | Winter clothing insulation factor |
| `--run-simulation` | Flag | False | - | Run full EnergyPlus simulations |
| `--help` | Flag | - | - | Show help message |
| `--version` | Flag | - | - | Show version information |

## Output Structure

The tool creates a project folder named after your H2K file with the following structure:

```
ProjectName/                             # Named after H2K file (no extension)
├── original.h2k                        # Copy of your original H2K file
├── original/                           # Original model outputs
│   ├── original.osm                    # OpenStudio model from H2K
│   ├── original.xml                    # Generated HPXML file
│   ├── hpxml_run/                      # OpenStudio-HPXML workflow files
│   └── [simulation files if --run-simulation used]
├── extreme_periods.yml                 # Hottest periods for outages
├── summer_period.yml                   # Summer season dates
├── outage_typical_year/                # Scenario 1: Power outage + normal weather
│   ├── outage_typical_year.osm
│   └── [simulation files if --run-simulation used]
├── outage_extreme_year/                # Scenario 2: Power outage + extreme weather
│   ├── outage_extreme_year.osm
│   └── [simulation files if --run-simulation used]
├── thermal_autonomy_typical_year/      # Scenario 3: No cooling + normal weather
│   ├── thermal_autonomy_typical_year.osm
│   └── [simulation files if --run-simulation used]
└── thermal_autonomy_extreme_year/      # Scenario 4: No cooling + extreme weather
    ├── thermal_autonomy_extreme_year.osm
    └── [simulation files if --run-simulation used]
```

## Analysis Scenarios

The tool generates four resilience scenarios:

| Scenario | Weather | Cooling Available | Power During Outage | Use Case |
|----------|---------|-------------------|---------------------|----------|
| `outage_typical_year` | CWEC (Normal) | ✓ Yes | ✗ No (during outage) | Power outage resilience in normal weather |
| `outage_extreme_year` | EWY (Extreme) | ✓ Yes | ✗ No (during outage) | Power outage resilience in extreme weather |
| `thermal_autonomy_typical_year` | CWEC (Normal) | ✗ No | ✓ Yes | Passive cooling in normal weather |
| `thermal_autonomy_extreme_year` | EWY (Extreme) | ✗ No | ✓ Yes | Passive cooling in extreme weather |

## What the Tool Does

1. **Validates Dependencies** - Checks for OpenStudio and OpenStudio-HPXML
2. **Converts H2K to Models** - Uses OpenStudio-HPXML workflow for realistic building models
3. **Downloads Weather Files** - Automatically gets CWEC and EWY weather data
4. **Analyzes Weather Patterns** - Identifies summer periods and hottest consecutive days
5. **Creates Scenarios** - Generates 4 models with different resilience conditions
6. **Applies Clothing Schedules** - Sets seasonal clothing insulation factors
7. **Configures HVAC Systems** - Enables/disables cooling and creates power failure schedules
8. **Adds Output Variables** - Includes thermal comfort monitoring variables
9. **Runs Simulations** - Optional full annual EnergyPlus simulations
10. **Validates Results** - Checks simulation success and output data

## Sample Workflow

```bash
# Step 1: Basic validation and model creation
python src/h2k_hpxml/cli/resilience.py examples/WizardHouse.h2k --output-path examples
# Output: ✓ OpenStudio-HPXML validated at: /OpenStudio-HPXML/
# Output: Resilience analysis completed successfully!

# Step 2: Check the generated structure
ls examples/WizardHouse/
# Output: original/ original.h2k extreme_periods.yml summer_period.yml 
#         outage_typical_year/ outage_extreme_year/ 
#         thermal_autonomy_typical_year/ thermal_autonomy_extreme_year/

# Step 3: Run with simulations for full analysis
python src/h2k_hpxml/cli/resilience.py examples/WizardHouse.h2k --output-path examples --run-simulation
# Output: [Full simulation execution with validation]
```

## Understanding the Output Files

### YAML Configuration Files

- **`extreme_periods.yml`** - Contains start dates for the hottest consecutive periods:
  ```yaml
  cwec_outage_start_date: '2023-07-14'
  ewy_outage_start_date: '2023-07-14'
  ```

- **`summer_period.yml`** - Contains summer season dates for clothing schedules:
  ```yaml
  cwec_summer_start: '06-14'
  cwec_summer_end: '08-31'
  ewy_summer_start: '06-14'
  ewy_summer_end: '08-31'
  ```

### Model Files

- **`.osm` files** - OpenStudio models for each scenario
- **`.xml` files** - HPXML building descriptions
- **`eplusout.sql`** - Simulation results database (if `--run-simulation` used)
- **`log.txt`** - Simulation logs with validation results

## Troubleshooting

### Common Error Messages

```bash
# OpenStudio-HPXML not found
ERROR: OpenStudio-HPXML not found at /OpenStudio-HPXML/
# Solution: Install OpenStudio-HPXML at the expected location

# OpenStudio Python bindings missing
Error: OpenStudio Python bindings are not available.
# Solution: Install OpenStudio with Python bindings

# H2K file not found
Error: H2K file not found: /path/to/file.h2k
# Solution: Check the file path and ensure the file exists
```

### Validation Checklist

Before running the tool, verify:

- [ ] H2K file exists and is readable
- [ ] OpenStudio Python bindings installed (`import openstudio` works)
- [ ] OpenStudio-HPXML installed at `/OpenStudio-HPXML/`
- [ ] Sufficient disk space for outputs
- [ ] Write permissions to output directory

## Advanced Usage

### Custom Clothing Factors

Clothing insulation factors affect thermal comfort calculations:

```bash
# Light summer clothing, heavy winter clothing
python src/h2k_hpxml/cli/resilience.py file.h2k --clothing-factor-summer 0.3 --clothing-factor-winter 1.5

# Business attire year-round
python src/h2k_hpxml/cli/resilience.py file.h2k --clothing-factor-summer 0.7 --clothing-factor-winter 1.0
```

### Extended Outage Analysis

```bash
# Analyze longer outages (up to 365 days)
python src/h2k_hpxml/cli/resilience.py file.h2k --outage-days 30

# Analyze short-term outages
python src/h2k_hpxml/cli/resilience.py file.h2k --outage-days 1
```

### Batch Processing

```bash
# Process multiple files
for file in *.h2k; do
    python src/h2k_hpxml/cli/resilience.py "$file" --output-path results/
done
```

## Next Steps

After running the resilience analysis:

1. **Review the scenarios** - Check the generated `.osm` files for model differences
2. **Analyze YAML files** - Understand the identified extreme periods and summer seasons
3. **Run simulations** - Use `--run-simulation` for detailed thermal comfort analysis
4. **Post-process results** - Query `eplusout.sql` for thermal comfort metrics
5. **Compare scenarios** - Evaluate building performance across different resilience conditions

## Getting Help

- Use `python src/h2k_hpxml/cli/resilience.py --help` for command-line help
- Check the main documentation in `/resilience.md` for detailed technical information
- Review log files in scenario folders for simulation details
- Validate OpenStudio-HPXML installation if conversion fails