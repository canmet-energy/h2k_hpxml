import math

from ..utils import obj, h2k

# Handled here, not in selection.json, because the format is slightly different
fireplace_stove_equip_map = {
    "advanced airtight wood stove": "stove",
    "1st option with catalytic converter": "stove",
    "conventional furnace": None,
    "conventional stove": "stove",
    "pellet stove": "stove",
    "masonry heater": None,
    "conventional fireplace": "fireplace",
    "fireplace insert": "fireplace",
}

# TODO: Flue diameter not handled


# Translates data from the "Type1" heating system section of h2k
def get_primary_heating_system(h2k_dict, model_data):

    type1_heating_system = obj.get_val(h2k_dict, "HouseFile,House,HeatingCooling,Type1")

    # h2k files cannot be built without a Type 1 heating system, so we don't need to check for the presence of one
    type1_type = [x for x in list(type1_heating_system.keys()) if x != "FansAndPump"][0]

    type1_data = type1_heating_system.get(type1_type, {})

    primary_heating_dict = {}
    if type1_type == "Baseboards":
        # TODO: Remove is_hvac_translated flag after testing
        model_data.set_is_hvac_translated(True)
        primary_heating_dict = get_electric_resistance(type1_data, model_data)

    elif type1_type == "Furnace":
        # TODO: Remove is_hvac_translated flag after testing
        model_data.set_is_hvac_translated(True)

        furnace_subtype = (
            str(obj.get_val(type1_data, "Equipment,EquipmentType,English"))
        ).lower()

        hpxml_heating_type = fireplace_stove_equip_map.get(furnace_subtype, None)

        if hpxml_heating_type == "stove":
            # ignores differences between furnaces and boilers because HPXML has an explicit stove component
            primary_heating_dict = get_stove(type1_data, model_data)
        elif hpxml_heating_type == "fireplace":
            # ignores differences between furnaces and boilers because HPXML has an explicit fireplace component
            primary_heating_dict = get_fireplace(type1_data, model_data)
        else:
            primary_heating_dict = get_furnace(type1_data, model_data)

    elif type1_type == "Boiler":
        # TODO: Remove is_hvac_translated flag after testing
        model_data.set_is_hvac_translated(True)

        # Wood boilers not broken down into stoves and fireplaces, only indoor/outdoor
        primary_heating_dict = get_boiler(type1_data, model_data)

    return primary_heating_dict


# Translates h2k's Baseboards Type1 system
def get_electric_resistance(type1_data, model_data):

    baseboard_capacity = h2k.get_number_field(type1_data, "baseboard_capacity")
    baseboard_efficiency = h2k.get_number_field(type1_data, "baseboard_efficiency")

    # By default we assume electric resistance, overwriting with radiant if present
    # “baseboard”, “radiant floor”, or “radiant ceiling”
    elec_resistance = {
        "SystemIdentifier": {"@id": model_data.get_system_id("primary_heating")},
        "HeatingSystemType": {
            "ElectricResistance": {"ElectricDistribution": "baseboard"}
        },
        "HeatingSystemFuel": "electricity",
        "HeatingCapacity": baseboard_capacity,
        "AnnualHeatingEfficiency": {
            "Units": "Percent",  # Only unit type allowed here. Note actual value must be a fraction
            "Value": baseboard_efficiency,
        },
        "FractionHeatLoadServed": 1,  # Hardcoded for now
    }

    # TODO: FractionHeatLoadServed is not allowed if this is a heat pump backup system
    # Also must sum to 1 across all heating systems

    return elec_resistance


def get_furnace(type1_data, model_data):
    # Currently, this portion of the HPXML doesn't have an analog for the "Equipment type" field

    furnace_capacity = h2k.get_number_field(type1_data, "furnace_capacity")

    furnace_efficiency = h2k.get_number_field(type1_data, "furnace_efficiency")

    # TODO: The documentation makes it look like the Units can be set to "Percent", but this throws an error when simulating
    # Currently hardcoded to AFUE
    is_steady_state = obj.get_val(type1_data, "Specifications,@isSteadyState")

    furnace_sizing_factor = h2k.get_number_field(type1_data, "furnace_sizing_factor")
    is_auto_sized = (
        "Calculated" == obj.get_val(type1_data, "Specifications,OutputCapacity,English")
        or furnace_capacity == 0
    )

    furnace_pilot_light = h2k.get_number_field(type1_data, "furnace_pilot_light")

    furnace_fuel_type = h2k.get_selection_field(type1_data, "furnace_fuel_type")

    # TODO: confirm desired behaviour around auto-sizing
    furnace_dict = {
        "SystemIdentifier": {"@id": model_data.get_system_id("primary_heating")},
        "DistributionSystem": {"@idref": model_data.get_system_id("hvac_distribution")},
        "HeatingSystemType": {
            "Furnace": None
        },  # potential to add pilot light info later
        "HeatingSystemFuel": furnace_fuel_type,
        **({} if is_auto_sized else {"HeatingCapacity": furnace_capacity}),
        "AnnualHeatingEfficiency": {
            "Units": (
                "AFUE"  # "Percent" if is_steady_state == "true" else "AFUE"
            ),  # "AFUE" / "Percent"
            "Value": furnace_efficiency,
        },
        "FractionHeatLoadServed": 1,
        **(
            {"extension": {"HeatingAutosizingFactor": furnace_sizing_factor}}
            if is_auto_sized
            else {}
        ),
    }

    # TODO: FractionHeatLoadServed is not allowed if this is a heat pump backup system
    # Also must sum to 1 across all heating systems

    # Add pilot light if present
    if furnace_pilot_light > 0:
        furnace_dict["HeatingSystemType"] = {
            "Furnace": {
                "PilotLight": "true",
                "extension": {"PilotLightBtuh": furnace_pilot_light},
            }
        }

    # No h2k representation for "gravity" distribution type
    # Might need to update this based on logic around system types
    model_data.set_hvac_distribution_type("air_regular velocity")

    return furnace_dict


def get_boiler(type1_data, model_data):
    # Currently, this portion of the HPXML doesn't have an analog for the "Equipment type" field

    boiler_capacity = h2k.get_number_field(type1_data, "furnace_capacity")

    boiler_efficiency = h2k.get_number_field(type1_data, "furnace_efficiency")

    # TODO: The documentation makes it look like the Units can be set to "Percent", but this throws an error when simulating
    # Currently hardcoded to AFUE
    is_steady_state = obj.get_val(type1_data, "Specifications,@isSteadyState")

    boiler_sizing_factor = h2k.get_number_field(type1_data, "furnace_sizing_factor")
    is_auto_sized = (
        "Calculated" == obj.get_val(type1_data, "Specifications,OutputCapacity,English")
        or boiler_capacity == 0
    )

    boiler_pilot_light = h2k.get_number_field(type1_data, "furnace_pilot_light")

    boiler_fuel_type = h2k.get_selection_field(type1_data, "furnace_fuel_type")

    # TODO: confirm desired behaviour around auto-sizing
    boiler_dict = {
        "SystemIdentifier": {"@id": model_data.get_system_id("primary_heating")},
        "DistributionSystem": {"@idref": model_data.get_system_id("hvac_distribution")},
        "HeatingSystemType": {
            "Boiler": None
        },  # potential to add pilot light info later
        "HeatingSystemFuel": boiler_fuel_type,
        **({} if is_auto_sized else {"HeatingCapacity": boiler_capacity}),
        "AnnualHeatingEfficiency": {
            "Units": (
                "AFUE"  # "Percent" if is_steady_state == "true" else "AFUE"
            ),  # "AFUE" / "Percent"
            "Value": boiler_efficiency,
        },
        "FractionHeatLoadServed": 1,
        "ElectricAuxiliaryEnergy": 0,  # Without this, HPXML assumes 330 kWh/y for oil and 170 kWh/y for gas boilers
        **(
            {"extension": {"HeatingAutosizingFactor": boiler_sizing_factor}}
            if is_auto_sized
            else {}
        ),
    }

    # TODO: FractionHeatLoadServed is not allowed if this is a heat pump backup system
    # Also must sum to 1 across all heating systems

    # Add pilot light if present
    if boiler_pilot_light > 0:
        boiler_dict["HeatingSystemType"] = {
            "Boiler": {
                "PilotLight": "true",
                "extension": {"PilotLightBtuh": boiler_pilot_light},
            }
        }

    # No h2k representation for "gravity" distribution type
    # Might need to update this based on logic around system types
    # TODO: change distribution type to "radiant floor" if in-floor is defined
    # Option to use air_fan coil if boiler has a shared water loop with a heat pump
    model_data.set_hvac_distribution_type("hydronic_radiator")

    return boiler_dict


def get_fireplace(type1_data, model_data):
    # Furnace field keys still work here because the structure is either a furnace or boiler
    fireplace_capacity = h2k.get_number_field(type1_data, "furnace_capacity")
    fireplace_efficiency = h2k.get_number_field(type1_data, "furnace_efficiency")

    # Fireplace accepts Percent, not AFUE
    is_steady_state = obj.get_val(type1_data, "Specifications,@isSteadyState")

    fireplace_sizing_factor = h2k.get_number_field(type1_data, "furnace_sizing_factor")
    is_auto_sized = (
        "Calculated" == obj.get_val(type1_data, "Specifications,OutputCapacity,English")
        or fireplace_capacity == 0
    )

    fireplace_fuel_type = h2k.get_selection_field(type1_data, "furnace_fuel_type")

    # TODO: confirm desired behaviour around auto-sizing
    fireplace_dict = {
        "SystemIdentifier": {"@id": model_data.get_system_id("primary_heating")},
        "HeatingSystemType": {
            "Fireplace": None
        },  # potential to add pilot light info later
        "HeatingSystemFuel": fireplace_fuel_type,
        **({} if is_auto_sized else {"HeatingCapacity": fireplace_capacity}),
        "AnnualHeatingEfficiency": {
            "Units": "Percent",  # "AFUE" / "Percent"
            "Value": fireplace_efficiency,
        },
        "FractionHeatLoadServed": 1,
        **(
            {"extension": {"HeatingAutosizingFactor": fireplace_sizing_factor}}
            if is_auto_sized
            else {}
        ),
    }

    # TODO: FractionHeatLoadServed is not allowed if this is a heat pump backup system
    # Also must sum to 1 across all heating systems

    return fireplace_dict


def get_stove(type1_data, model_data):
    # Furnace field keys still work here because the structure is either a furnace or boiler
    stove_capacity = h2k.get_number_field(type1_data, "furnace_capacity")
    stove_efficiency = h2k.get_number_field(type1_data, "furnace_efficiency")

    # Stove accepts Percent, not AFUE
    is_steady_state = obj.get_val(type1_data, "Specifications,@isSteadyState")

    stove_sizing_factor = h2k.get_number_field(type1_data, "furnace_sizing_factor")
    is_auto_sized = (
        "Calculated" == obj.get_val(type1_data, "Specifications,OutputCapacity,English")
        or stove_capacity == 0
    )

    stove_fuel_type = h2k.get_selection_field(type1_data, "furnace_fuel_type")

    # TODO: confirm desired behaviour around auto-sizing
    stove_dict = {
        "SystemIdentifier": {"@id": model_data.get_system_id("primary_heating")},
        "HeatingSystemType": {"Stove": None},  # potential to add pilot light info later
        "HeatingSystemFuel": stove_fuel_type,
        **({} if is_auto_sized else {"HeatingCapacity": stove_capacity}),
        "AnnualHeatingEfficiency": {
            "Units": "Percent",
            "Value": stove_efficiency,
        },
        "FractionHeatLoadServed": 1,
        **(
            {"extension": {"HeatingAutosizingFactor": stove_sizing_factor}}
            if is_auto_sized
            else {}
        ),
    }

    # TODO: FractionHeatLoadServed is not allowed if this is a heat pump backup system
    # Also must sum to 1 across all heating systems

    return stove_dict
