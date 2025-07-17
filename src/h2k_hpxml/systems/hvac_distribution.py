import math
from collections import OrderedDict
from ..utils import obj, h2k


# Returns the HVAC distribution system based on the specified type
# "air"
# "hydronic"
# Distribution System Efficiency (DSE) is NOT SUPPORTED (no h2k representation)
# This function must run after heating/cooling/heat pump systems are built
def get_hvac_distribution(h2k_dict, model_data):

    heating_dist_type = model_data.get_heating_distribution_type()
    ac_hp_dist_type = model_data.get_ac_hp_distribution_type()
    supplemental_heating_dist_types = (
        model_data.get_suppl_heating_distribution_types()
    )  # A list
    primary_heating_id = model_data.get_system_id("primary_heating")
    air_conditioning_id = model_data.get_system_id("air_conditioning")
    air_heat_pump_id = model_data.get_system_id("air_heat_pump")
    ground_heat_pump_id = model_data.get_system_id("ground_heat_pump")
    water_heat_pump_id = model_data.get_system_id("water_heat_pump")

    # TODO: Better handle determination of which floor areas to include here (total area assumed)
    ag_heated_floor_area = model_data.get_building_detail("ag_heated_floor_area")
    bg_heated_floor_area = model_data.get_building_detail("bg_heated_floor_area")

    hvac_dist_systems = []

    # We have already "activated" distribution system types with the model_data.set_xx_distribution_type() method
    # We combine them here and loop through them, removing duplicates such that if two systems call for the same
    # type of distribution they will use the same one.
    # This behaviour is supported by the pre-defined distribution system ids set up at the beginning of the get_systems() function
    for hvac_dist_type in list(
        OrderedDict.fromkeys(
            [heating_dist_type, ac_hp_dist_type, *supplemental_heating_dist_types]
        )
    ):
        if "air_" in str(hvac_dist_type):
            # “regular velocity”, “gravity”, or “fan coil” are the supported types
            # Not all of these are defined in h2k
            [base_type, sub_type] = hvac_dist_type.split("_")
            # Currently only handling regular velocity with default duct inputs
            hvac_dist_dict = {
                "SystemIdentifier": {
                    "@id": model_data.get_system_id("hvac_air_distribution")
                },
                "DistributionSystemType": {
                    "AirDistribution": {
                        "AirDistributionType": sub_type,
                        "DuctLeakageMeasurement": [
                            {
                                "DuctType": "supply",
                                "DuctLeakage": {
                                    "Units": "CFM25",
                                    "Value": 0,
                                    "TotalOrToOutside": "to outside",
                                },
                            },
                            {
                                "DuctType": "return",
                                "DuctLeakage": {
                                    "Units": "CFM25",
                                    "Value": 0,
                                    "TotalOrToOutside": "to outside",
                                },
                            },
                        ],
                        "Ducts": [
                            {
                                "SystemIdentifier": {"@id": "Ducts1"},
                                "DuctType": "supply",
                                "DuctInsulationRValue": 0.0,
                            },
                            {
                                "SystemIdentifier": {"@id": "Ducts2"},
                                "DuctType": "return",
                                "DuctInsulationRValue": 0.0,
                            },
                        ],
                    }
                },
                "ConditionedFloorAreaServed": ag_heated_floor_area
                + bg_heated_floor_area,
            }

            hvac_dist_systems = [*hvac_dist_systems, hvac_dist_dict]

        elif "hydronic_" in str(hvac_dist_type):
            # HydronicDistributionType choices are “radiator”, “baseboard”, “radiant floor”, “radiant ceiling”, or “water loop”.
            # However, h2k does not include sufficient information to determine which is used, so we default to "radiator" (without radiant floor explicitly defined)

            [base_type, sub_type] = hvac_dist_type.split("_")

            # If the file has radiant heating specified then use that instead of the default sub_type ("radiator")
            radiant_type = get_radiant_heating_type(h2k_dict, model_data)

            hvac_dist_dict = {
                "SystemIdentifier": {
                    "@id": model_data.get_system_id("hvac_hydronic_distribution")
                },
                "DistributionSystemType": {
                    "HydronicDistribution": {
                        "HydronicDistributionType": (
                            radiant_type if radiant_type != None else sub_type
                        ),
                    }
                },
                "ConditionedFloorAreaServed": ag_heated_floor_area
                + bg_heated_floor_area,
            }

            hvac_dist_systems = [*hvac_dist_systems, hvac_dist_dict]

    return hvac_dist_systems


radiant_map = [
    {"AtticCeiling": "radiant ceiling"},
    {"FlatRoof": "radiant ceiling"},
    {"AboveCrawlspace": "radiant floor"},
    {"SlabOnGrade": "radiant floor"},
    {"AboveBasement": "radiant floor"},
    {"Basement": "radiant floor"},
]


def get_radiant_heating_type(h2k_dict, model_data):
    if (
        "RadiantHeating"
        not in obj.get_val(h2k_dict, "HouseFile,House,HeatingCooling").keys()
    ):
        return None

    radiant_heating = obj.get_val(
        h2k_dict, "HouseFile,House,HeatingCooling,RadiantHeating"
    )

    fraction_area_list = []
    for location in radiant_map:
        fraction_area_list = [
            *fraction_area_list,
            float(radiant_heating[list(location.keys())[0]]["@fractionOfArea"]),
        ]

    largest_type_index = fraction_area_list.index(max(fraction_area_list))

    radiant_type = list(radiant_map[largest_type_index].values())[0]

    return radiant_type
