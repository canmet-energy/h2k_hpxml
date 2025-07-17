import math

from ..utils import obj, h2k


# TODO: Flue diameter not handled


# Translates data from the supplementary heating systems section
# All FractionHeatLoadServed elements hardcoded at 0 until we figure out how to determine this
def get_secondary_heating_systems(h2k_dict, model_data):
    remaining_heating_fraction = 1
    # results = model_data.get_results("SOC")

    if (
        "SupplementaryHeatingSystems"
        not in obj.get_val(h2k_dict, "HouseFile,House,HeatingCooling").keys()
    ):
        return [], remaining_heating_fraction

    suppl_heating_systems = obj.get_val(
        h2k_dict, "HouseFile,House,HeatingCooling,SupplementaryHeatingSystems,System"
    )

    if suppl_heating_systems == {}:
        return [], remaining_heating_fraction

    # Always process as array
    suppl_heating_systems = (
        suppl_heating_systems
        if isinstance(suppl_heating_systems, list)
        else [suppl_heating_systems]
    )

    secondary_heating_results = []

    suppl_heating_distribution_types = []

    for system_data in suppl_heating_systems:
        # Determine fraction heating load, if any
        suppl_heating_usage = obj.get_val(system_data, "Specifications,Usage,English")
        suppl_heating_location = obj.get_val(
            system_data, "Specifications,LocationHeated,English"
        )

        suppl_heating_area_heated = h2k.get_number_field(
            system_data, "suppl_heating_area_heated"
        )

        fraction_floor_area = 0
        if (suppl_heating_usage == "Always") and (suppl_heating_location != "Exterior"):
            # Calculate fraction based on floor area served
            rank = obj.get_val(system_data, "@rank")
            ag_heated_floor_area = model_data.get_building_detail(
                "ag_heated_floor_area"
            )
            bg_heated_floor_area = model_data.get_building_detail(
                "bg_heated_floor_area"
            )
            fraction_floor_area = round(
                suppl_heating_area_heated
                / (ag_heated_floor_area + bg_heated_floor_area),
                2,
            )

            remaining_heating_fraction = round(
                remaining_heating_fraction - fraction_floor_area, 2
            )

        system_type = h2k.get_selection_field(system_data, "suppl_heating_equip_type")
        flue_diameter = h2k.get_number_field(system_data, "suppl_heating_flue_diameter")
        if flue_diameter > 0:
            model_data.set_flue_diameters(flue_diameter)

        # Determine what the primary (type1) heating system type is, if required
        type1_system_type = model_data.get_building_detail("primary_heating_equip_type")
        system_type = type1_system_type if system_type == "primary" else system_type

        new_system = {}
        if system_type == "baseboard":
            new_system = get_electric_resistance(
                system_data, system_type, fraction_floor_area, model_data
            )

        elif system_type == "stove":
            new_system = get_stove(system_data, fraction_floor_area, model_data)

        elif system_type == "fireplace":
            new_system = get_fireplace(system_data, fraction_floor_area, model_data)

        elif system_type == "furnace":
            new_system = get_furnace(system_data, fraction_floor_area, model_data)
            # Need this to be included here, so that the distribution system doesn't get missed
            suppl_heating_distribution_types = [
                *suppl_heating_distribution_types,
                "air_regular velocity",
            ]

        elif system_type == "space heater":
            new_system = get_space_heater(system_data, fraction_floor_area, model_data)

        elif system_type == "radiant floor":
            # Uses "Electric Resistance", always electric
            new_system = get_electric_resistance(
                system_data, system_type, fraction_floor_area, model_data
            )

        elif system_type == "radiant ceiling":
            # Uses "Electric Resistance", always electric
            new_system = get_electric_resistance(
                system_data, system_type, fraction_floor_area, model_data
            )

        elif system_type == "boiler":
            # The only way to get here is if the equipment type is set to "same as type 1"
            new_system = get_boiler(system_data, fraction_floor_area, model_data)
            suppl_heating_distribution_types = [
                *suppl_heating_distribution_types,
                "hydronic_radiator",
            ]

        secondary_heating_results = [*secondary_heating_results, new_system]

    secondary_heating_results = [x for x in secondary_heating_results if x != {}]

    model_data.set_suppl_heating_distribution_types(suppl_heating_distribution_types)

    return secondary_heating_results, remaining_heating_fraction


# Translates electric suppl heating systems that use the "baseboard", "radiant floor", or "radiant ceiling" ElectricDistribution types
def get_electric_resistance(system_data, system_type, fraction_floor_area, model_data):
    rank = obj.get_val(system_data, "@rank")

    suppl_heating_capacity = h2k.get_number_field(system_data, "suppl_heating_capacity")
    suppl_heating_efficiency = h2k.get_number_field(
        system_data, "suppl_heating_efficiency"
    )

    # By default we assume electric resistance, overwriting with radiant if present
    # “baseboard”, “radiant floor”, or “radiant ceiling”
    elec_resistance = {
        "SystemIdentifier": {"@id": f"SupplHeatingSystem{rank}"},
        "HeatingSystemType": {
            "ElectricResistance": {"ElectricDistribution": system_type}
        },
        "HeatingSystemFuel": "electricity",
        "HeatingCapacity": suppl_heating_capacity,
        "AnnualHeatingEfficiency": {
            "Units": "Percent",  # Only unit type allowed here. Note actual value must be a fraction
            "Value": suppl_heating_efficiency,
        },
        "FractionHeatLoadServed": fraction_floor_area,
    }

    return elec_resistance


def get_furnace(system_data, fraction_floor_area, model_data):
    rank = obj.get_val(system_data, "@rank")
    furnace_capacity = h2k.get_number_field(system_data, "suppl_heating_capacity")
    furnace_efficiency = h2k.get_number_field(system_data, "suppl_heating_efficiency")

    furnace_pilot_light = h2k.get_number_field(system_data, "suppl_heating_pilot_light")

    furnace_fuel_type = h2k.get_selection_field(system_data, "furnace_fuel_type")

    furnace_dict = {
        "SystemIdentifier": {"@id": f"SupplHeatingSystem{rank}"},
        "DistributionSystem": {
            "@idref": model_data.get_system_id("hvac_air_distribution")
        },
        "HeatingSystemType": {
            "Furnace": None
        },  # potential to add pilot light info later
        "HeatingSystemFuel": furnace_fuel_type,
        "HeatingCapacity": furnace_capacity,
        "AnnualHeatingEfficiency": {
            "Units": (
                "AFUE"  # "Percent" if is_steady_state == "true" else "AFUE"
            ),  # "AFUE" / "Percent"
            "Value": furnace_efficiency,
        },
        "FractionHeatLoadServed": fraction_floor_area,
    }

    # Add pilot light if present
    if furnace_pilot_light > 0:
        furnace_dict["HeatingSystemType"] = {
            "Furnace": {
                "PilotLight": "true",
                "extension": {"PilotLightBtuh": furnace_pilot_light},
            }
        }

    return furnace_dict


def get_boiler(system_data, fraction_floor_area, model_data):
    rank = obj.get_val(system_data, "@rank")
    boiler_capacity = h2k.get_number_field(system_data, "suppl_heating_capacity")
    boiler_efficiency = h2k.get_number_field(system_data, "suppl_heating_efficiency")
    boiler_pilot_light = h2k.get_number_field(system_data, "suppl_heating_pilot_light")

    boiler_fuel_type = h2k.get_selection_field(system_data, "furnace_fuel_type")

    boiler_dict = {
        "SystemIdentifier": {"@id": f"SupplHeatingSystem{rank}"},
        "DistributionSystem": {
            "@idref": model_data.get_system_id("hvac_hydronic_distribution")
        },
        "HeatingSystemType": {
            "Boiler": None
        },  # potential to add pilot light info later
        "HeatingSystemFuel": boiler_fuel_type,
        "HeatingCapacity": boiler_capacity,
        "AnnualHeatingEfficiency": {
            "Units": (
                "AFUE"  # "Percent" if is_steady_state == "true" else "AFUE"
            ),  # "AFUE" / "Percent"
            "Value": boiler_efficiency,
        },
        "FractionHeatLoadServed": fraction_floor_area,
        "ElectricAuxiliaryEnergy": 0,  # Without this, HPXML assumes 330 kWh/y for oil and 170 kWh/y for gas boilers
    }

    # Add pilot light if present
    if boiler_pilot_light > 0:
        boiler_dict["HeatingSystemType"] = {
            "Boiler": {
                "PilotLight": "true",
                "extension": {"PilotLightBtuh": boiler_pilot_light},
            }
        }

    return boiler_dict


def get_fireplace(system_data, fraction_floor_area, model_data):
    rank = obj.get_val(system_data, "@rank")
    fireplace_capacity = h2k.get_number_field(system_data, "suppl_heating_capacity")
    fireplace_efficiency = h2k.get_number_field(system_data, "suppl_heating_efficiency")

    # Same options as furnace
    fireplace_fuel_type = h2k.get_selection_field(system_data, "furnace_fuel_type")

    fireplace_dict = {
        "SystemIdentifier": {"@id": f"SupplHeatingSystem{rank}"},
        "HeatingSystemType": {
            "Fireplace": None
        },  # potential to add pilot light info later
        "HeatingSystemFuel": fireplace_fuel_type,
        "HeatingCapacity": fireplace_capacity,
        "AnnualHeatingEfficiency": {
            "Units": "Percent",  # "AFUE" / "Percent"
            "Value": fireplace_efficiency,
        },
        "FractionHeatLoadServed": fraction_floor_area,
    }

    return fireplace_dict


def get_stove(system_data, fraction_floor_area, model_data):
    rank = obj.get_val(system_data, "@rank")
    stove_capacity = h2k.get_number_field(system_data, "suppl_heating_capacity")
    stove_efficiency = h2k.get_number_field(system_data, "suppl_heating_efficiency")

    stove_fuel_type = h2k.get_selection_field(system_data, "furnace_fuel_type")

    stove_dict = {
        "SystemIdentifier": {"@id": f"SupplHeatingSystem{rank}"},
        "HeatingSystemType": {"Stove": None},
        "HeatingSystemFuel": stove_fuel_type,
        "HeatingCapacity": stove_capacity,
        "AnnualHeatingEfficiency": {
            "Units": "Percent",
            "Value": stove_efficiency,
        },
        "FractionHeatLoadServed": fraction_floor_area,
    }

    return stove_dict


def get_space_heater(system_data, fraction_floor_area, model_data):
    rank = obj.get_val(system_data, "@rank")

    suppl_heating_capacity = h2k.get_number_field(system_data, "suppl_heating_capacity")
    suppl_heating_efficiency = h2k.get_number_field(
        system_data, "suppl_heating_efficiency"
    )

    heater_fuel_type = h2k.get_selection_field(system_data, "furnace_fuel_type")

    # By default we assume electric resistance, overwriting with radiant if present
    # “baseboard”, “radiant floor”, or “radiant ceiling”
    space_heater = {
        "SystemIdentifier": {"@id": f"SupplHeatingSystem{rank}"},
        "HeatingSystemType": {"SpaceHeater": None},
        "HeatingSystemFuel": heater_fuel_type,
        "HeatingCapacity": suppl_heating_capacity,
        "AnnualHeatingEfficiency": {
            "Units": "Percent",  # Only unit type allowed here. Note actual value must be a fraction
            "Value": suppl_heating_efficiency,
        },
        "FractionHeatLoadServed": fraction_floor_area,
    }

    return space_heater
