import math

from ..utils import obj, h2k


def get_ventilation_systems(h2k_dict, model_data):
    # Get overall parameters
    vent_hours_per_day = h2k.get_number_field(h2k_dict, "whole_house_vent_schedule")

    # Get the four main ventilator objects (HRVs) & arrays (BaseVentilators)
    whole_house_ventilators = obj.get_val(
        h2k_dict, "HouseFile,House,Ventilation,WholeHouseVentilatorList"
    )
    whole_house_ventilators = (
        {} if whole_house_ventilators == None else whole_house_ventilators
    )

    whole_house_hrv = whole_house_ventilators.get("Hrv", {})
    whole_house_base_vent = whole_house_ventilators.get("BaseVentilator", [])
    whole_house_base_vent = (
        whole_house_base_vent
        if isinstance(whole_house_base_vent, list)
        else [whole_house_base_vent]
    )

    supplemental_ventilators = obj.get_val(
        h2k_dict, "HouseFile,House,Ventilation,SupplementalVentilatorList"
    )

    supplemental_ventilators = (
        {} if supplemental_ventilators == None else supplemental_ventilators
    )

    # Dryers are handled in the appliances.py file, which includes their exhaust flow rate
    supplemental_hrv = supplemental_ventilators.get("Hrv", {})
    supplemental_base_vent = supplemental_ventilators.get("BaseVentilator", [])
    supplemental_base_vent = (
        supplemental_base_vent
        if isinstance(supplemental_base_vent, list)
        else [supplemental_base_vent]
    )

    ventilation_fan_list = []
    i = 1
    for whole_vent in whole_house_base_vent:
        whole_vent_res = get_ventilator(
            whole_vent, i, vent_hours_per_day, True, model_data
        )
        ventilation_fan_list = [*ventilation_fan_list, whole_vent_res]
        i += 1

    for suppl_vent in supplemental_base_vent:
        suppl_vent_res = get_ventilator(
            suppl_vent, i, vent_hours_per_day, False, model_data
        )
        ventilation_fan_list = [*ventilation_fan_list, suppl_vent_res]
        i += 1

    ventilation_fan_list = [
        *ventilation_fan_list,
        get_hrv(whole_house_hrv, vent_hours_per_day, True, model_data),
        get_hrv(supplemental_hrv, vent_hours_per_day, False, model_data),
    ]

    ventilation_fan_list = [x for x in ventilation_fan_list if x != {}]

    return ventilation_fan_list


def get_ventilator(sys_data, ind, vent_hours_per_day, is_whole_house, model_data):
    if sys_data == {}:
        return {}

    fan_power = h2k.get_number_field(sys_data, "ventilator_fan_power")
    supply_flow_rate = h2k.get_number_field(sys_data, "ventilator_supply_flowrate")
    exhaust_flow_rate = h2k.get_number_field(sys_data, "ventilator_exhaust_flowrate")

    if (supply_flow_rate == 0) & (exhaust_flow_rate == 0):
        return {}

    supplemental_vent_hours_per_day = h2k.get_number_field(
        sys_data, "supplemental_vent_schedule"
    )
    ventilator_type = h2k.get_selection_field(sys_data, "base_ventilator_type")

    rated_flow_rate = max(supply_flow_rate, exhaust_flow_rate)
    fan_type = "exhaust only"  # most common type
    if (
        abs(supply_flow_rate - exhaust_flow_rate)
        / max(supply_flow_rate, exhaust_flow_rate)
        <= 0.05
    ):
        # Checks if supply and exhaust are within 5% (arbitrary %) to determine if balanced
        fan_type = "balanced"
    elif supply_flow_rate > exhaust_flow_rate:
        fan_type = "supply only"

    ventilator = {}
    if ventilator_type in ["bath", "kitchen"]:
        ventilator = {
            "SystemIdentifier": {"@id": f"VentilationFan{ind}"},
            "FanType": fan_type,  # "exhaust only", "supply only", "balanced"
            "RatedFlowRate": rated_flow_rate,
            "HoursInOperation": (
                vent_hours_per_day
                if is_whole_house
                else supplemental_vent_hours_per_day
            ),
            "FanLocation": ventilator_type,
            "UsedForLocalVentilation": True,
            "FanPower": fan_power,
        }

    elif ventilator_type == "utility" and is_whole_house:
        ventilator = {
            "SystemIdentifier": {"@id": f"VentilationFan{ind}"},
            "FanType": fan_type,  # "exhaust only", "supply only", "balanced"
            "RatedFlowRate": rated_flow_rate,
            "HoursInOperation": (
                vent_hours_per_day
                if is_whole_house
                else supplemental_vent_hours_per_day
            ),
            "UsedForWholeBuildingVentilation": is_whole_house,
            "FanPower": fan_power,
        }

    elif ventilator_type == "utility" and not is_whole_house:
        model_data.add_warning_message(
            {
                "message": "A utility fan has been modelled as a supplementary fan, which does not have an HPXML representation. A whole house fan without heat recovery has been modelled as an approximation."
            }
        )
        ventilator = {
            "SystemIdentifier": {"@id": f"VentilationFan{ind}"},
            "FanType": fan_type,  # "exhaust only", "supply only", "balanced"
            "RatedFlowRate": rated_flow_rate,
            "HoursInOperation": (
                vent_hours_per_day
                if is_whole_house
                else supplemental_vent_hours_per_day
            ),
            "UsedForWholeBuildingVentilation": True,
            "FanPower": fan_power,
        }

    return ventilator


def get_hrv(sys_data, vent_hours_per_day, is_whole_house, model_data):
    if sys_data == {}:
        return {}

    fan_power = h2k.get_number_field(sys_data, "ventilator_fan_power")
    flow_rate = h2k.get_number_field(sys_data, "ventilator_supply_flowrate")
    hrv_efficiency = h2k.get_number_field(sys_data, "hrv_efficiency")
    # Very unlikely an hrv will be a supplemental system but technically possible
    supplemental_vent_hours_per_day = h2k.get_number_field(
        sys_data, "supplemental_vent_schedule"
    )

    hrv = {
        "SystemIdentifier": {
            "@id": f"Hrv{'WholeHouse' if is_whole_house else 'Supplemental'}1"
        },
        "FanType": "heat recovery ventilator",
        "RatedFlowRate": flow_rate,
        "HoursInOperation": (
            vent_hours_per_day if is_whole_house else supplemental_vent_hours_per_day
        ),
        "UsedForWholeBuildingVentilation": is_whole_house,
        "SensibleRecoveryEfficiency": hrv_efficiency,
        "FanPower": fan_power,
    }

    return hrv
