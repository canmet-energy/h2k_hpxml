from ..utils import obj, h2k


def get_plug_loads(h2k_dict, model_data):
    building_type = model_data.get_building_detail("building_type")
    common_space_area = model_data.get_building_detail("common_space_area", 0)  # [ft2]
    hpxml_plug_loads = {
        "PlugLoad": [
            {
                "SystemIdentifier": {"@id": "PlugLoad1"},
                "PlugLoadType": "other",
                "Load": {
                    "Units": "kWh/year",
                    "Value": 9.7 * 365 if building_type == "house" else 4.4 * 365,
                },
            },
        ]
    }

    if common_space_area > 0:
        hpxml_plug_loads["PlugLoad"].append(
            {
                "SystemIdentifier": {"@id": "PlugLoad2"},
                "PlugLoadType": "other",
                "Load": {
                    "Units": "kWh/year",
                    "Value": 0.086 * common_space_area * (1 / 10.7639) * 365,
                },
            }
        )

    return hpxml_plug_loads


def get_fuel_loads(h2k_dict, model_data):
    return {
        "FuelLoad": [
            {
                # "SystemIdentifier": {"@id": "PlugLoad1"},
                # "PlugLoadType": "TV other",
                # "Load": {"Units": "kWh/year", "Value": "620.0"},
            },
        ]
    }
