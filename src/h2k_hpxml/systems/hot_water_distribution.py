import math

from ..utils import obj, h2k


def get_hot_water_distribution(h2k_dict, model_data):
    dwhr_dict = {}

    dwhr_system_primary = model_data.get_building_detail("dwhr_system_primary")

    if dwhr_system_primary != {} and dwhr_system_primary != None:
        # Description of "EqualFlow":
        # EqualFlow should be true if the DWHR supplies pre-heated water to both the fixture cold water piping and the hot water heater potable supply piping.
        # I believe this meaning aligns with the system configuration specification in h2k
        dwhr_configuration = obj.get_val(dwhr_system_primary, "@preheatShowerTank")

        dwhr_efficiency = h2k.get_number_field(dwhr_system_primary, "dwhr_efficiency")
        dwhr_dict = {
            "FacilitiesConnected": "all",
            "EqualFlow": dwhr_configuration,
            "Efficiency": dwhr_efficiency,
        }

    return {
        "SystemIdentifier": {"@id": model_data.get_system_id("dhw_distribution")},
        "SystemType": {"Standard": None},
        "PipeInsulation": {"PipeRValue": 0},
        **({"DrainWaterHeatRecovery": dwhr_dict} if dwhr_dict != {} else {}),
    }
