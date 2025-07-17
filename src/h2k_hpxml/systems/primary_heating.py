import math

from ..utils import obj, h2k, units


# TODO: Flue diameter not handled


# Translates data from the "Type1" heating system section of h2k
def get_primary_heating_system(h2k_dict, model_data):

    type1_heating_system = obj.get_val(h2k_dict, "HouseFile,House,HeatingCooling,Type1")

    # h2k files cannot be built without a Type 1 heating system, so we don't need to check for the presence of one
    type1_type = [x for x in list(type1_heating_system.keys()) if x != "FansAndPump"][0]

    type1_data = type1_heating_system.get(type1_type, {})

    primary_heating_dict = {}

    # defaulting this to 0
    model_data.set_building_details({"primary_pilot_light_GJpery": 0})

    if type1_type == "Baseboards":
        # TODO: Remove is_hvac_translated flag after testing
        model_data.set_is_hvac_translated(True)
        # Needed for "Same as type 1 system" option in supplementary systems
        model_data.set_building_details(
            {
                "primary_heating_equip_type": "baseboard",
            }
        )
        primary_heating_dict = get_electric_resistance(type1_data, model_data)

    elif type1_type == "Furnace":
        # TODO: Remove is_hvac_translated flag after testing
        model_data.set_is_hvac_translated(True)
        # Needed for "Same as type 1 system" option in supplementary systems

        # A slightly unique selection field, used to determine whether to build a furnace (default), stove, or fireplace
        hpxml_heating_type = h2k.get_selection_field(type1_data, "furnace_equip_type")

        if hpxml_heating_type == "stove":
            # ignores differences between furnaces and boilers because HPXML has an explicit stove component
            # Needed for "Same as type 1 system" option in supplementary systems
            model_data.set_building_details(
                {
                    "primary_heating_equip_type": "stove",
                }
            )
            primary_heating_dict = get_stove(type1_data, model_data)
        elif hpxml_heating_type == "fireplace":
            # ignores differences between furnaces and boilers because HPXML has an explicit fireplace component
            # Needed for "Same as type 1 system" option in supplementary systems
            model_data.set_building_details(
                {
                    "primary_heating_equip_type": "fireplace",
                }
            )
            primary_heating_dict = get_fireplace(type1_data, model_data)
        else:
            # Default, builds furnace
            # Needed for "Same as type 1 system" option in supplementary systems
            model_data.set_building_details(
                {
                    "primary_heating_equip_type": "furnace",
                }
            )
            primary_heating_dict = get_furnace(type1_data, model_data)

    elif type1_type == "Boiler":
        # TODO: Remove is_hvac_translated flag after testing
        model_data.set_is_hvac_translated(True)

        # Needed for "Same as type 1 system" option in supplementary systems
        model_data.set_building_details(
            {
                "primary_heating_equip_type": "boiler",
            }
        )

        # Wood boilers not broken down into stoves and fireplaces, only indoor/outdoor
        primary_heating_dict = get_boiler(type1_data, model_data)

    elif type1_type == "ComboHeatDhw":
        # TODO: Remove is_hvac_translated flag after testing
        model_data.set_is_hvac_translated(True)

        # Needed for "Same as type 1 system" option in supplementary systems
        model_data.set_building_details(
            {
                "primary_heating_equip_type": "boiler",
            }
        )

        # A normal boiler is defined, we always use hydronic_radiator distribution in the get_boiler function
        primary_heating_dict = get_boiler(type1_data, model_data)

        # Note that with this type of combo system, we still have a HotWater object with all the info we need
        # However, we need to explicitly tell the system that it's a combo so it builds the HPXML combi directly
        model_data.set_system_id(
            {"combi_related_hvac_id": model_data.get_system_id("primary_heating")}
        )

    elif type1_type == "P9":
        # TODO: Remove is_hvac_translated flag after testing
        model_data.set_is_hvac_translated(True)

        # Needed for "Same as type 1 system" option in supplementary systems
        model_data.set_building_details(
            {
                "primary_heating_equip_type": "boiler",
            }
        )

        # Need a custom function here because the structure of the P9 object is very different
        primary_heating_dict = get_p9_heating_system(type1_data, model_data)

        model_data.set_system_id(
            {"combi_related_hvac_id": model_data.get_system_id("primary_heating")}
        )

    return primary_heating_dict


# Translates h2k's Baseboards Type1 system
def get_electric_resistance(type1_data, model_data):

    baseboard_capacity = h2k.get_number_field(type1_data, "baseboard_capacity")
    baseboard_efficiency = h2k.get_number_field(type1_data, "baseboard_efficiency")

    baseboard_sizing_factor = h2k.get_number_field(
        type1_data, "baseboard_sizing_factor"
    )
    is_auto_sized = (
        "Calculated" == obj.get_val(type1_data, "Specifications,OutputCapacity,English")
        or baseboard_capacity == 0
    )

    model_data.set_building_details(
        {
            "heat_pump_backup_type": "separate",
            "heat_pump_backup_system": "baseboards",
            "heat_pump_backup_fuel": "electricity",
            "heat_pump_backup_efficiency": baseboard_efficiency,
            "heat_pump_backup_eff_unit": "Percent",
            "heat_pump_backup_autosized": is_auto_sized,
            "heat_pump_backup_capacity": baseboard_capacity,
            "heat_pump_backup_system_id": model_data.get_system_id("primary_heating"),
        }
    )

    # By default we assume electric resistance, overwriting with radiant if present
    # “baseboard”, “radiant floor”, or “radiant ceiling”
    elec_resistance = {
        "SystemIdentifier": {"@id": model_data.get_system_id("primary_heating")},
        "HeatingSystemType": {
            "ElectricResistance": {"ElectricDistribution": "baseboard"}
        },
        "HeatingSystemFuel": "electricity",
        **({} if is_auto_sized else {"HeatingCapacity": baseboard_capacity}),
        "AnnualHeatingEfficiency": {
            "Units": "Percent",  # Only unit type allowed here. Note actual value must be a fraction
            "Value": baseboard_efficiency,
        },
        "FractionHeatLoadServed": 1,  # Hardcoded for now
        **(
            {"extension": {"HeatingAutosizingFactor": baseboard_sizing_factor}}
            if is_auto_sized
            else {}
        ),
    }

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
    furnace_flue_diameter = h2k.get_number_field(type1_data, "furnace_flue_diameter")

    furnace_fuel_type = h2k.get_selection_field(type1_data, "furnace_fuel_type")

    model_data.set_building_details(
        {
            "heat_pump_backup_type": "integrated",
            "heat_pump_backup_system": "furnace",
            "heat_pump_backup_fuel": furnace_fuel_type,
            "heat_pump_backup_efficiency": furnace_efficiency,
            "heat_pump_backup_eff_unit": "Percent" if is_steady_state else "AFUE",
            "heat_pump_backup_autosized": is_auto_sized,
            "heat_pump_backup_capacity": furnace_capacity,
            "heat_pump_backup_system_id": model_data.get_system_id("primary_heating"),
        }
    )

    if furnace_flue_diameter > 0:
        model_data.set_flue_diameters(furnace_flue_diameter)

    # TODO: confirm desired behaviour around auto-sizing
    furnace_dict = {
        "SystemIdentifier": {"@id": model_data.get_system_id("primary_heating")},
        "DistributionSystem": {
            "@idref": model_data.get_system_id("hvac_air_distribution")
        },
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

    # Add pilot light if present
    if furnace_pilot_light > 0:
        furnace_dict["HeatingSystemType"] = {
            "Furnace": {
                "PilotLight": "true",
                "extension": {"PilotLightBtuh": furnace_pilot_light},
            }
        }

        model_data.set_building_details(
            {
                "primary_pilot_light_GJpery": units.convert_unit(
                    furnace_pilot_light, "daily_energy", "BTU/h", "MJ/day"
                )
                * 365
                / 1000
            }
        )

    # No h2k representation for "gravity" distribution type
    # Might need to update this based on logic around system types
    model_data.set_heating_distribution_type("air_regular velocity")

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
    boiler_flue_diameter = h2k.get_number_field(type1_data, "furnace_flue_diameter")

    boiler_fuel_type = h2k.get_selection_field(type1_data, "furnace_fuel_type")

    combo_tank_volume = 0
    combo_energy_factor = boiler_efficiency  # Fallback, already a fraction
    if "ComboTankAndPump" in type1_data.keys():
        combo_tank_volume = h2k.get_number_field(type1_data, "combo_tank_volume")

        combo_default_ef = (
            type1_data.get("ComboTankAndPump", {})
            .get("EnergyFactor", {})
            .get("@useDefaults", "true")
            == "true"
        )
        if combo_default_ef:
            # warning, the default isn't actually written to the file
            model_data.add_warning_message(
                {
                    "message": "A default combo EF was specified, but HOT2000 does not write this value to the file. A user specified value should be used for better alignment between HOT2000 and HPXML."
                }
            )
        else:
            combo_energy_factor = float(
                type1_data.get("ComboTankAndPump", {})
                .get("EnergyFactor", {})
                .get("@value", "0")
            )

    model_data.set_building_details(
        {
            "heat_pump_backup_type": "separate",
            "heat_pump_backup_system": "boiler",
            "heat_pump_backup_fuel": boiler_fuel_type,
            "heat_pump_backup_efficiency": boiler_efficiency,
            "heat_pump_backup_eff_unit": "Percent" if is_steady_state else "AFUE",
            "heat_pump_backup_autosized": is_auto_sized,
            "heat_pump_backup_capacity": boiler_capacity,
            "heat_pump_backup_system_id": model_data.get_system_id("primary_heating"),
            "combo_fuel_type": boiler_fuel_type,
            "combo_energy_factor": combo_energy_factor,
            "combo_tank_volume": combo_tank_volume,
        }
    )

    if boiler_flue_diameter > 0:
        model_data.set_flue_diameters(boiler_flue_diameter)

    # Determine the ElectricAuxiliaryEnergy [kWh/y] from the results of the h2k file
    # TODO: figure out how this works for supplementary heating systems
    results = model_data.get_results()
    electric_aux_energy = 0
    if results != {}:
        tot_elec_heating_GJ = float(
            obj.get_val(results, "Annual,Consumption,Electrical,@spaceHeating")
        )
        heat_pump_elec_heating_GJ = float(
            obj.get_val(results, "Annual,Consumption,Electrical,@heatPump")
        )

        primary_elec_heating_GJ = (
            float(obj.get_val(results, "Annual,Consumption,SpaceHeating,@primary"))
            if boiler_fuel_type == "electricity"
            else 0
        )

        if boiler_fuel_type != "electricity" and heat_pump_elec_heating_GJ > 0:
            # When there's a non-electric boiler and a heat pump, we can subtract the heat pump consumption from the total electric space heating consumption
            electric_aux_energy = max(
                0, tot_elec_heating_GJ - heat_pump_elec_heating_GJ
            ) * (1 / 0.0036)
        elif boiler_fuel_type == "electricity" and heat_pump_elec_heating_GJ > 0:
            # We cannot disaggregate the results to determine this
            electric_aux_energy = 0
        else:
            electric_aux_energy = max(
                0, tot_elec_heating_GJ - primary_elec_heating_GJ
            ) * (1 / 0.0036)

    # TODO: confirm desired behaviour around auto-sizing
    boiler_dict = {
        "SystemIdentifier": {"@id": model_data.get_system_id("primary_heating")},
        "DistributionSystem": {
            "@idref": model_data.get_system_id("hvac_hydronic_distribution")
        },
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
        "ElectricAuxiliaryEnergy": round(
            electric_aux_energy, 1
        ),  # Without this, HPXML assumes 330 kWh/y for oil and 170 kWh/y for gas boilers
        **(
            {"extension": {"HeatingAutosizingFactor": boiler_sizing_factor}}
            if is_auto_sized
            else {}
        ),
    }

    # Add pilot light if present
    if boiler_pilot_light > 0:
        boiler_dict["HeatingSystemType"] = {
            "Boiler": {
                "PilotLight": "true",
                "extension": {"PilotLightBtuh": boiler_pilot_light},
            }
        }

        model_data.set_building_details(
            {
                "primary_pilot_light_GJpery": units.convert_unit(
                    boiler_pilot_light, "daily_energy", "BTU/h", "MJ/day"
                )
                * 365
                / 1000
            }
        )

    # No h2k representation for "gravity" distribution type
    # Might need to update this based on logic around system types
    # TODO: change distribution type to "radiant floor" if in-floor is defined
    # Option to use air_fan coil if boiler has a shared water loop with a heat pump
    model_data.set_heating_distribution_type("hydronic_radiator")
    # model_data.set_heating_distribution_type("air_regular velocity")

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

    fireplace_flue_diameter = h2k.get_number_field(type1_data, "furnace_flue_diameter")

    fireplace_fuel_type = h2k.get_selection_field(type1_data, "furnace_fuel_type")

    model_data.set_building_details(
        {
            "heat_pump_backup_type": "separate",
            "heat_pump_backup_system": "fireplace",
            "heat_pump_backup_fuel": fireplace_fuel_type,
            "heat_pump_backup_efficiency": fireplace_efficiency,
            "heat_pump_backup_eff_unit": "Percent" if is_steady_state else "AFUE",
            "heat_pump_backup_autosized": is_auto_sized,
            "heat_pump_backup_capacity": fireplace_capacity,
            "heat_pump_backup_system_id": model_data.get_system_id("primary_heating"),
        }
    )

    if fireplace_flue_diameter > 0:
        model_data.set_flue_diameters(fireplace_flue_diameter)

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

    stove_flue_diameter = h2k.get_number_field(type1_data, "furnace_flue_diameter")

    stove_fuel_type = h2k.get_selection_field(type1_data, "furnace_fuel_type")

    model_data.set_building_details(
        {
            "heat_pump_backup_type": "separate",
            "heat_pump_backup_system": "stove",
            "heat_pump_backup_fuel": stove_fuel_type,
            "heat_pump_backup_efficiency": stove_efficiency,
            "heat_pump_backup_eff_unit": "Percent" if is_steady_state else "AFUE",
            "heat_pump_backup_autosized": is_auto_sized,
            "heat_pump_backup_capacity": stove_capacity,
            "heat_pump_backup_system_id": model_data.get_system_id("primary_heating"),
        }
    )

    if stove_flue_diameter > 0:
        model_data.set_flue_diameters(stove_flue_diameter)

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

    return stove_dict


def get_p9_heating_system(type1_data, model_data):

    # Capacity never calculated for P9
    p9_capacity = h2k.get_number_field(type1_data, "p9_heating_capacity")

    # Because the hot water section for HPXML combos doesn't accept an efficiency, assuming we have to use the TPF here to capture the overall performance
    # Using the composite space heating efficiency rather than the TPF because we're decoupling hot water and heating
    # p9_tpf = h2k.get_number_field(type1_data, "p9_tpf")
    p9_composite_heating_eff = h2k.get_number_field(
        type1_data, "p9_composite_heating_eff"
    )
    p9_water_heating_performance_factor = h2k.get_number_field(
        type1_data, "p9_water_heating_performance_factor"
    )

    p9_fuel_type = h2k.get_selection_field(type1_data, "p9_fuel_type")

    model_data.set_building_details(
        {
            "heat_pump_backup_type": "separate",
            "heat_pump_backup_system": "boiler",
            "heat_pump_backup_fuel": p9_fuel_type,
            "heat_pump_backup_efficiency": p9_composite_heating_eff,
            "heat_pump_backup_eff_unit": "AFUE",
            "heat_pump_backup_autosized": False,
            "heat_pump_backup_capacity": p9_capacity,
            "heat_pump_backup_system_id": model_data.get_system_id("primary_heating"),
            "combo_fuel_type": p9_fuel_type,
            "combo_energy_factor": p9_water_heating_performance_factor,
            "combo_tank_volume": 0,
        }
    )

    # Determine the ElectricAuxiliaryEnergy [kWh/y] from the results of the h2k file
    results = model_data.get_results()
    electric_aux_energy = 0
    if results != {}:
        tot_elec_heating_GJ = float(
            obj.get_val(results, "Annual,Consumption,Electrical,@spaceHeating")
        )

        primary_elec_heating_GJ = (
            float(obj.get_val(results, "Annual,Consumption,SpaceHeating,@primary"))
            if p9_fuel_type == "electricity"
            else 0
        )

        electric_aux_energy = max(0, tot_elec_heating_GJ - primary_elec_heating_GJ) * (
            1 / 0.0036
        )

    # TODO: confirm desired behaviour around auto-sizing
    p9_dict = {
        "SystemIdentifier": {"@id": model_data.get_system_id("primary_heating")},
        "DistributionSystem": {
            "@idref": model_data.get_system_id(
                "hvac_hydronic_distribution"
            )  # Boilers must have a hydronic system
        },
        "HeatingSystemType": {"Boiler": None},
        "HeatingSystemFuel": p9_fuel_type,
        "HeatingCapacity": p9_capacity,
        "AnnualHeatingEfficiency": {
            "Units": (
                "AFUE"  # "Percent" if is_steady_state == "true" else "AFUE"
            ),  # "AFUE" / "Percent"
            "Value": p9_composite_heating_eff,
        },
        "FractionHeatLoadServed": 1,
        "ElectricAuxiliaryEnergy": round(
            electric_aux_energy, 1
        ),  # Without this, HPXML assumes 330 kWh/y for oil and 170 kWh/y for gas boilers
    }

    # No pilot light info for P9s

    # No h2k representation for "gravity" distribution type
    # Might need to update this based on logic around system types
    # TODO: change distribution type to "radiant floor" if in-floor is defined
    # Option to use air_fan coil if boiler has a shared water loop with a heat pump
    model_data.set_heating_distribution_type("hydronic_radiator")
    # model_data.set_heating_distribution_type("air_regular velocity")

    return p9_dict
