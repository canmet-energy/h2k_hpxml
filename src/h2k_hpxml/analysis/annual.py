import os
import pandas as pd
import xmltodict
from collections.abc import MutableMapping


def flatten(dictionary, parent_key="", separator="_"):
    items = []
    for key, value in dictionary.items():
        new_key = parent_key + separator + key if parent_key else key
        if isinstance(value, MutableMapping):
            items.extend(flatten(value, new_key, separator=separator).items())
        else:
            items.append((new_key, value))
    return dict(items)


def read_os_results(path="", return_type="dict"):
    if path == "":
        return {}

    results_folder_path = f"{path}run/"

    dir_contents = os.listdir(results_folder_path)

    if "results_annual.csv" not in dir_contents:
        return {}

    columns = ["parameter", "value"]
    res_df = pd.read_csv(
        f"{results_folder_path}results_annual.csv", header=None, names=columns
    )

    if return_type == "dict":
        return dict(zip(res_df.parameter, res_df.value))

    else:
        return res_df


def read_h2k_results(path="", case="Base", operating_conditions="SOC"):
    # Note, if SOC operating conditions are not present we will return "general results"
    # Options for case: "Base", "AllUpgrades"
    # Options for operating_conditions: "SOC", "UserHouse", "Reference", "ROC", "HCV", "HOC", "General"
    if path == "":
        return {}

    with open(path, "r", encoding="utf-8") as f:
        h2k_string = f.read()

    h2k_dict = xmltodict.parse(h2k_string)

    weather_location = (
        h2k_dict.get("HouseFile", {})
        .get("ProgramInformation", {})
        .get("Weather", {})
        .get("Location", {})
        .get("English", {})
    )

    hot_water_load_Lperday = float(
        h2k_dict.get("HouseFile", {})
        .get("House", {})
        .get("BaseLoads", {})
        .get("Summary", {})
        .get("@hotWaterLoad", {})
    )

    all_results = h2k_dict.get("HouseFile", {}).get("AllResults", {}).get("Results", [])

    if not all_results:
        return {}

    all_results = all_results if isinstance(all_results, list) else [all_results]

    # Find correct results case
    matching_res_set = {}
    for res_set in all_results:
        case_match = ((case == "Base") and ("type" not in res_set.keys())) or (
            (res_set.get("@type", None) == case)
        )

        op_cond_match = res_set.get("@houseCode", None) == operating_conditions

        if case_match and op_cond_match:
            matching_res_set = res_set

    return matching_res_set, weather_location, hot_water_load_Lperday


def compare_os_h2k_annual(h2k_results={}, os_results={}):
    compare_dict = {
        "total_annual_consumption_GJ": {
            "h2k": float(
                h2k_results.get("Annual", {}).get("Consumption", {}).get("@total", 0)
            ),
            "hpxml": os_results.get("Energy Use: Total (MBtu)", 0)
            * (1.0550558526 / 1),  # [MBtu -> GJ]
        },
        "heating_sys_energy_delivered_GJ": {
            "h2k": float(
                h2k_results.get("Annual", {}).get("Load", {}).get("@auxiliaryEnergy", 0)
            )
            / 1000,  # [GJ]
            "hpxml": os_results.get("Load: Heating: Delivered (MBtu)", 0)
            * (1.0550558526 / 1),  # [MBtu -> GJ]
        },
        "cooling_sys_energy_delivered_GJ": {
            "h2k": 0,
            "hpxml": os_results.get("Load: Cooling: Delivered (MBtu)", 0)
            * (1.0550558526 / 1),  # [MBtu -> GJ]
        },
        "peak_heating_load_W": {
            "h2k": float(h2k_results.get("Other", {}).get("@designHeatLossRate", 0)),
            "hpxml": os_results.get("HVAC Design Load: Heating: Total (Btu/h)", 0)
            * (1 / 3.41),  # [Btu/h -> W]
        },
        "peak_cooling_load_W": {
            "h2k": float(h2k_results.get("Other", {}).get("@designCoolLossRate", 0)),
            "hpxml": (
                os_results.get("HVAC Design Load: Cooling Sensible: Total (Btu/h)", 0)
                + os_results.get("HVAC Design Load: Cooling Latent: Total (Btu/h)", 0)
            )
            * (1 / 3.41),  # [Btu/h -> W]
        },
    }

    os_heat_loss_roofs = os_results.get("Component Load: Heating: Roofs (MBtu)", 0) * (
        1.0550558526 / 1
    )  # [MBtu -> GJ]

    os_heat_loss_ceilings = os_results.get(
        "Component Load: Heating: Ceilings (MBtu)", 0
    ) * (
        1.0550558526 / 1
    )  # [MBtu -> GJ]

    os_heat_loss_walls = os_results.get("Component Load: Heating: Walls (MBtu)", 0) * (
        1.0550558526 / 1
    )  # [MBtu -> GJ]

    os_heat_loss_rim_joists = os_results.get(
        "Component Load: Heating: Rim Joists (MBtu)", 0
    ) * (
        1.0550558526 / 1
    )  # [MBtu -> GJ]

    os_heat_loss_windows = os_results.get(
        "Component Load: Heating: Windows Conduction (MBtu)", 0
    ) * (
        1.0550558526 / 1
    )  # [MBtu -> GJ]
    os_heat_loss_skylights = os_results.get(
        "Component Load: Heating: Skylights Conduction (MBtu)", 0
    ) * (
        1.0550558526 / 1
    )  # [MBtu -> GJ]

    os_heat_loss_doors = os_results.get("Component Load: Heating: Doors (MBtu)", 0) * (
        1.0550558526 / 1
    )  # [MBtu -> GJ]

    os_heat_loss_floors = os_results.get(
        "Component Load: Heating: Floors (MBtu)", 0
    ) * (
        1.0550558526 / 1
    )  # [MBtu -> GJ]

    os_heat_loss_foundation_walls = os_results.get(
        "Component Load: Heating: Foundation Walls (MBtu)", 0
    ) * (
        1.0550558526 / 1
    )  # [MBtu -> GJ]

    os_heat_loss_slabs = os_results.get("Component Load: Heating: Slabs (MBtu)", 0) * (
        1.0550558526 / 1
    )  # [MBtu -> GJ]

    os_heat_loss_infiltration = os_results.get(
        "Component Load: Heating: Infiltration (MBtu)", 0
    ) * (
        1.0550558526 / 1
    )  # [MBtu -> GJ]

    os_heat_loss_nat_ventilation = os_results.get(
        "Component Load: Heating: Natural Ventilation (MBtu)", 0
    ) * (
        1.0550558526 / 1
    )  # [MBtu -> GJ]

    os_heat_loss_mech_vent = os_results.get(
        "Component Load: Heating: Mechanical Ventilation (MBtu)", 0
    ) * (
        1.0550558526 / 1
    )  # [MBtu -> GJ]

    # H2k results
    # This one sometimes shows up as 0 in the h2k
    # h2k_gross_heat_loss = float(
    #     h2k_results.get("Annual", {}).get("HeatLoss", {}).get("@total", 0)
    # )
    h2k_gross_heat_loss = float(
        h2k_results.get("Annual", {}).get("Load", {}).get("@grossHeating", 0)
    )
    h2k_heat_loss_ceiling = float(
        h2k_results.get("Annual", {}).get("HeatLoss", {}).get("@ceiling", 0)
    )
    h2k_heat_loss_walls = float(
        h2k_results.get("Annual", {}).get("HeatLoss", {}).get("@mainWalls", 0)
    )  # Includes headers on main walls
    h2k_heat_loss_windows = float(
        h2k_results.get("Annual", {}).get("HeatLoss", {}).get("@windows", 0)
    )
    h2k_heat_loss_doors = float(
        h2k_results.get("Annual", {}).get("HeatLoss", {}).get("@doors", 0)
    )
    h2k_heat_loss_exp_floors = float(
        h2k_results.get("Annual", {}).get("HeatLoss", {}).get("@exposedFloors", 0)
    )
    h2k_heat_loss_crawlspace = float(
        h2k_results.get("Annual", {}).get("HeatLoss", {}).get("@crawlspace", 0)
    )
    h2k_heat_loss_slab = float(
        h2k_results.get("Annual", {}).get("HeatLoss", {}).get("@slab", 0)
    )
    h2k_heat_loss_basement_bg_walls = float(
        h2k_results.get("Annual", {})
        .get("HeatLoss", {})
        .get("@basementBelowGradeWall", 0)
    )
    h2k_heat_loss_basement_ag_walls = float(
        h2k_results.get("Annual", {})
        .get("HeatLoss", {})
        .get("@basementAboveGradeWall", 0)
    )
    h2k_heat_loss_basement_floor_headers = float(
        h2k_results.get("Annual", {})
        .get("HeatLoss", {})
        .get("@basementFloorHeaders", 0)
    )  # add this to main walls
    h2k_heat_loss_pony_wall = float(
        h2k_results.get("Annual", {}).get("HeatLoss", {}).get("@ponyWall", 0)
    )
    h2k_heat_loss_basement_floors_above = float(
        h2k_results.get("Annual", {}).get("HeatLoss", {}).get("@floorsAboveBasement", 0)
    )
    h2k_heat_loss_air_leakage = float(
        h2k_results.get("Annual", {})
        .get("HeatLoss", {})
        .get("@airLeakageAndNaturalVentilation", 0)
    )

    h2k_heat_loss_ag_walls_total = (
        h2k_heat_loss_walls
        + h2k_heat_loss_basement_floor_headers
        + h2k_heat_loss_pony_wall
    )
    os_heat_loss_ag_walls_total = os_heat_loss_walls + os_heat_loss_rim_joists

    os_gross_heat_loss = (
        os_heat_loss_infiltration
        + os_heat_loss_nat_ventilation
        + os_heat_loss_ag_walls_total
        + os_heat_loss_roofs
        + os_heat_loss_ceilings
        + os_heat_loss_doors
        + os_heat_loss_windows
        + os_heat_loss_skylights
        + os_heat_loss_floors
        + os_heat_loss_foundation_walls
        + os_heat_loss_slabs
    )

    compare_dict["gross_heat_loss_GJ"] = {
        "h2k": h2k_gross_heat_loss,
        "hpxml": os_gross_heat_loss,
    }

    compare_dict["heat_loss_walls_GJ"] = {
        "h2k": h2k_heat_loss_ag_walls_total,
        "hpxml": os_heat_loss_ag_walls_total,
    }

    compare_dict["heat_loss_ceilings_GJ"] = {
        "h2k": h2k_heat_loss_ceiling,
        "hpxml": os_heat_loss_roofs + os_heat_loss_ceilings,
    }

    compare_dict["heat_loss_doors_GJ"] = {
        "h2k": h2k_heat_loss_doors,
        "hpxml": os_heat_loss_doors,
    }

    compare_dict["heat_loss_windows_GJ"] = {
        "h2k": h2k_heat_loss_windows,
        "hpxml": os_heat_loss_windows + os_heat_loss_skylights,
    }

    compare_dict["heat_loss_floors_GJ"] = {
        "h2k": h2k_heat_loss_exp_floors,
        "hpxml": os_heat_loss_floors,
    }

    compare_dict["heat_loss_foundation_GJ"] = {
        "h2k": h2k_heat_loss_crawlspace
        + h2k_heat_loss_slab
        + h2k_heat_loss_basement_bg_walls
        + h2k_heat_loss_basement_ag_walls,
        "hpxml": os_heat_loss_foundation_walls + os_heat_loss_slabs,
    }

    compare_dict["heat_loss_air_leakage_GJ"] = {
        "h2k": h2k_heat_loss_air_leakage,
        "hpxml": os_heat_loss_infiltration + os_heat_loss_nat_ventilation,
    }

    compare_dict["hot_water_usage_Lperday"] = {
        "h2k": -1,
        "hpxml": (
            os_results.get("Hot Water: Clothes Washer (gal)", 0)
            + os_results.get("Hot Water: Dishwasher (gal)", 0)
            + os_results.get("Hot Water: Fixtures (gal)", 0)
            + os_results.get("Hot Water: Distribution Waste (gal)", 0)
        )
        * 3.78541
        / 365,
    }

    # Fuel use
    fuel_compare_dict = {
        "space_heating_elec_GJ": {
            "h2k": float(
                h2k_results.get("Annual", {})
                .get("Consumption", {})
                .get("Electrical", {})
                .get("@spaceHeating", 0)
            ),
            "hpxml": (
                os_results.get("End Use: Electricity: Heating (MBtu)", 0)
                + os_results.get("End Use: Electricity: Heating Fans/Pumps (MBtu)", 0)
                + os_results.get(
                    "End Use: Electricity: Heating Heat Pump Backup (MBtu)", 0
                )
                + os_results.get(
                    "End Use: Electricity: Heating Heat Pump Backup Fans/Pumps (MBtu)",
                    0,
                )
            )
            * (1.0550558526 / 1),  # [MBtu -> GJ]
        },
        "space_heating_ng_GJ": {
            "h2k": float(
                h2k_results.get("Annual", {})
                .get("Consumption", {})
                .get("NaturalGas", {})
                .get("@spaceHeating", 0)
            ),
            "hpxml": (
                os_results.get("End Use: Natural Gas: Heating (MBtu)", 0)
                + os_results.get(
                    "End Use: Natural Gas: Heating Heat Pump Backup (MBtu)", 0
                )
            )
            * (1.0550558526 / 1),  # [MBtu -> GJ]
        },
        "space_heating_oil_GJ": {
            "h2k": float(
                h2k_results.get("Annual", {})
                .get("Consumption", {})
                .get("Oil", {})
                .get("@spaceHeating", 0)
            ),
            "hpxml": (
                os_results.get("End Use: Fuel Oil: Heating (MBtu)", 0)
                + os_results.get(
                    "End Use: Fuel Oil: Heating Heat Pump Backup (MBtu)", 0
                )
            )
            * (1.0550558526 / 1),  # [MBtu -> GJ]
        },
        "space_heating_propane_GJ": {
            "h2k": float(
                h2k_results.get("Annual", {})
                .get("Consumption", {})
                .get("Propane", {})
                .get("@spaceHeating", 0)
            ),
            "hpxml": (
                os_results.get("End Use: Propane: Heating (MBtu)", 0)
                + os_results.get("End Use: Propane: Heating Heat Pump Backup (MBtu)", 0)
            )
            * (1.0550558526 / 1),  # [MBtu -> GJ]
        },
        "space_heating_wood_GJ": {
            "h2k": float(
                h2k_results.get("Annual", {})
                .get("Consumption", {})
                .get("Wood", {})
                .get("@spaceHeating", 0)
            ),
            "hpxml": (
                os_results.get("End Use: Wood Cord: Heating (MBtu)", 0)
                + os_results.get(
                    "End Use: Wood Cord: Heating Heat Pump Backup (MBtu)", 0
                )
                + os_results.get("End Use: Wood Pellets: Heating (MBtu)", 0)
                + os_results.get(
                    "End Use: Wood Pellets: Heating Heat Pump Backup (MBtu)", 0
                )
            )
            * (1.0550558526 / 1),  # [MBtu -> GJ]
        },
        "hot_water_elec_GJ": {
            "h2k": float(
                h2k_results.get("Annual", {})
                .get("Consumption", {})
                .get("Electrical", {})
                .get("HotWater", {})
                .get("@dhw", 0)
            ),
            "hpxml": (
                os_results.get("End Use: Electricity: Hot Water (MBtu)", 0)
                + os_results.get(
                    "End Use: Electricity: Hot Water Recirc Pump (MBtu)", 0
                )
                + os_results.get(
                    "End Use: Electricity: Hot Water Solar Thermal Pump (MBtu)", 0
                )
            )
            * (1.0550558526 / 1),  # [MBtu -> GJ]
        },
        "hot_water_ng_GJ": {
            "h2k": float(
                h2k_results.get("Annual", {})
                .get("Consumption", {})
                .get("NaturalGas", {})
                .get("@hotWater", 0)
            ),
            "hpxml": (os_results.get("End Use: Natural Gas: Hot Water (MBtu)", 0))
            * (1.0550558526 / 1),  # [MBtu -> GJ]
        },
        "hot_water_oil_GJ": {
            "h2k": float(
                h2k_results.get("Annual", {})
                .get("Consumption", {})
                .get("Oil", {})
                .get("@hotWater", 0)
            ),
            "hpxml": (os_results.get("End Use: Fuel Oil: Hot Water (MBtu)", 0))
            * (1.0550558526 / 1),  # [MBtu -> GJ]
        },
        "hot_water_propane_GJ": {
            "h2k": float(
                h2k_results.get("Annual", {})
                .get("Consumption", {})
                .get("Propane", {})
                .get("@hotWater", 0)
            ),
            "hpxml": (os_results.get("End Use: Propane: Hot Water (MBtu)", 0))
            * (1.0550558526 / 1),  # [MBtu -> GJ]
        },
        "hot_water_wood_GJ": {
            "h2k": float(
                h2k_results.get("Annual", {})
                .get("Consumption", {})
                .get("Wood", {})
                .get("@hotWater", 0)
            ),
            "hpxml": (
                os_results.get("End Use: Wood Cord: Hot Water (MBtu)", 0)
                + os_results.get("End Use: Wood Pellets: Hot Water (MBtu)", 0)
            )
            * (1.0550558526 / 1),  # [MBtu -> GJ]
        },
        "ventilation_elec_GJ": {
            "h2k": float(
                h2k_results.get("Annual", {})
                .get("Consumption", {})
                .get("Electrical", {})
                .get("@ventilation", 0)
            ),
            "hpxml": (
                os_results.get("End Use: Electricity: Mech Vent (MBtu)", 0)
                + os_results.get("End Use: Electricity: Mech Vent Preheating (MBtu)", 0)
                + os_results.get("End Use: Electricity: Mech Vent Precooling (MBtu)", 0)
                + os_results.get("End Use: Electricity: Whole House Fan (MBtu)", 0)
            )
            * (1.0550558526 / 1),  # [MBtu -> GJ]
        },
        "cooling_elec_GJ": {
            "h2k": float(
                h2k_results.get("Annual", {})
                .get("Consumption", {})
                .get("Electrical", {})
                .get("@spaceCooling", 0)
            ),
            "hpxml": (
                os_results.get("End Use: Electricity: Cooling (MBtu)", 0)
                + os_results.get("End Use: Electricity: Cooling Fans/Pumps (MBtu)", 0)
            )
            * (1.0550558526 / 1),  # [MBtu -> GJ]
        },
        "baseloads_elec_GJ": {
            "h2k": float(
                h2k_results.get("Annual", {})
                .get("Consumption", {})
                .get("Electrical", {})
                .get("@baseload", 0)
            ),
            "hpxml": (
                os_results.get("End Use: Electricity: Lighting Interior (MBtu)", 0)
                + os_results.get("End Use: Electricity: Lighting Garage (MBtu)", 0)
                + os_results.get("End Use: Electricity: Lighting Exterior (MBtu)", 0)
                + os_results.get("End Use: Electricity: Refrigerator (MBtu)", 0)
                + os_results.get("End Use: Electricity: Freezer (MBtu)", 0)
                + os_results.get("End Use: Electricity: Dehumidifier (MBtu)", 0)
                + os_results.get("End Use: Electricity: Dishwasher (MBtu)", 0)
                + os_results.get("End Use: Electricity: Clothes Washer (MBtu)", 0)
                + os_results.get("End Use: Electricity: Clothes Dryer (MBtu)", 0)
                + os_results.get("End Use: Electricity: Range/Oven (MBtu)", 0)
                + os_results.get("End Use: Electricity: Ceiling Fan (MBtu)", 0)
                + os_results.get("End Use: Electricity: Television (MBtu)", 0)
                + os_results.get("End Use: Electricity: Plug Loads (MBtu)", 0)
                + os_results.get("End Use: Electricity: Well Pump (MBtu)", 0)
                + os_results.get("End Use: Electricity: Pool Heater (MBtu)", 0)
                + os_results.get("End Use: Electricity: Pool Pump (MBtu)", 0)
                + os_results.get("End Use: Electricity: Permanent Spa Heater (MBtu)", 0)
                + os_results.get("End Use: Electricity: Permanent Spa Pump (MBtu)", 0)
            )
            * (1.0550558526 / 1),  # [MBtu -> GJ]
        },
    }

    compare_dict = {**compare_dict, **fuel_compare_dict}

    return flatten(compare_dict)


def get_ashrae_140_results(os_results={}):

    # Heating Load
    heating_load = os_results.get("Load: Heating: Delivered (MBtu)", 0)
    # Cooling Load
    cooling_load = os_results.get("Load: Cooling: Delivered (MBtu)", 0)

    return {"HeatingLoadMBtu": heating_load, "CoolingLoadMBtu": cooling_load}
