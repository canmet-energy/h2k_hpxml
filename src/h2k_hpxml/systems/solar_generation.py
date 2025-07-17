import math

from ..utils import obj, h2k


def get_solar_generation(h2k_dict, model_data):

    h2k_solar_pv_systems = (
        obj.get_val(h2k_dict, "HouseFile,House,Generation")
        .get("PhotovoltaicSystems", {})
        .get("System", {})
    )

    if h2k_solar_pv_systems == {}:
        return {}

    h2k_solar_pv_systems = (
        h2k_solar_pv_systems
        if isinstance(h2k_solar_pv_systems, list)
        else [h2k_solar_pv_systems]
    )

    pv_system_list = []
    pv_array_capacities = []
    inverter_list = []
    inverter_efficiencies = []
    i = 0
    for pv_system in h2k_solar_pv_systems:
        new_pv, new_inverter = get_solar_pv_system(pv_system, i, model_data)

        pv_system_list = [*pv_system_list, new_pv]
        pv_array_capacities = [*pv_array_capacities, new_pv["MaxPowerOutput"]]

        inverter_list = [*inverter_list, new_inverter]
        inverter_efficiencies = [
            *inverter_efficiencies,
            new_inverter["InverterEfficiency"],
        ]
        i += 1

    # If there are multiple inverters, their efficiencies must all be equal
    # When consolidating efficiencies, take weighted average based on attached array size
    if len(set(inverter_efficiencies)) > 1:
        new_inverter_efficiency = sum(
            [
                a * (b / sum(pv_array_capacities))
                for a, b in zip(inverter_efficiencies, pv_array_capacities)
            ]
        )

        for inverter in inverter_list:
            inverter["InverterEfficiency"] = round(new_inverter_efficiency, 3)

    solar_generation_dict = {"PVSystem": pv_system_list, "Inverter": inverter_list}

    return solar_generation_dict


def get_solar_pv_system(sys_data, ind, model_data):

    pv_module_type = h2k.get_selection_field(sys_data, "pv_module_type")

    pv_array_tilt = h2k.get_number_field(sys_data, "pv_array_tilt")
    h2k_array_azimuth = h2k.get_number_field(sys_data, "pv_array_azimuth")
    pv_array_area = h2k.get_number_field(sys_data, "pv_array_area")
    pv_module_efficiency = h2k.get_number_field(sys_data, "pv_module_efficiency")
    pv_array_misc_losses = h2k.get_number_field(sys_data, "pv_array_misc_losses")
    pv_array_other_losses = h2k.get_number_field(sys_data, "pv_array_other_losses")
    inverter_efficiency = h2k.get_number_field(sys_data, "pv_inverter_efficiency")

    # HPXML Azimuth has 0 @ north, increments clockwise
    # H2k Azimuth has 0 S, -90 W, 90 E, 180/-180 N
    hpxml_array_azimuth = 180 - h2k_array_azimuth

    # Calculate max power output based on array area and efficiency @ STC (1000W/m2)
    pv_array_stc_power = (
        pv_array_area * 1000 * pv_module_efficiency
    )  # [m2] * [1000 W/m2] * [Wp/W] = Wp

    # Calculated according to documentation (product, not sum)
    system_losses_fraction = 1 - (
        1 * (1 - pv_array_misc_losses) * (1 - pv_array_other_losses)
    )

    pv = {
        "SystemIdentifier": {"@id": f"PVSystem{ind}"},
        "Location": "roof",
        "ModuleType": pv_module_type,
        "Tracking": "fixed",
        "ArrayAzimuth": int(round(hpxml_array_azimuth, 0)),
        "ArrayTilt": pv_array_tilt,
        "MaxPowerOutput": round(pv_array_stc_power, 2),
        "SystemLossesFraction": round(system_losses_fraction, 2),
        "AttachedToInverter": {"@idref": f"Inverter{ind}"},
    }

    inverter = {
        "SystemIdentifier": {"@id": f"Inverter{ind}"},
        "InverterEfficiency": round(inverter_efficiency, 2),
    }

    return pv, inverter
