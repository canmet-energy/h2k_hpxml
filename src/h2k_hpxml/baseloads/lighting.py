def get_lighting(h2k_dict, model_data):
    building_type = model_data.get_building_detail("building_type")

    # TODO: account for lighting fractions to change LightingType
    return {
        "LightingGroup": [
            {
                "SystemIdentifier": {"@id": "LightingGroup1"},
                "Location": "interior",
                # "FractionofUnitsInLocation": 1, #Not when kWh is specified
                # "LightingType": {"CompactFluorescent": None},
                "Load": {
                    "Units": "kWh/year",
                    "Value": 2.6 * 365 if building_type == "house" else 1.7 * 365,
                },
            },
            {
                "SystemIdentifier": {"@id": "LightingGroup2"},
                "Location": "exterior",
                # "FractionofUnitsInLocation": 1,#Not when kWh is specified
                # "LightingType": {"CompactFluorescent": None},
                "Load": {
                    "Units": "kWh/year",
                    "Value": 0.9 * 365 if building_type == "house" else 0.4 * 365,
                },
            },
        ]
    }


# FluorescentTube, CompactFluorescent, LightEmittingDiode
