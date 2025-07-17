# High level HPXML structure :
#     "HVAC": {
#         "HVACPlant": {
#             "PrimarySystems": {
#                 "PrimaryHeatingSystem": {...},
#                 "PrimaryCoolingSystem": {...}
#             },
#             "HeatingSystem": [...],
#             "CoolingSystem": {...},
#         },
#         "HVACControl": {...},
#         "HVACDistribution": [...],
#     },
#     "WaterHeating": {
#         "WaterHeatingSystem": [...],
#         "HotWaterDistribution": [...],
#         "WaterFixture": [...],
#     }
# Certain sections must be conditionally present
# For example, with electric baseboards, no HVACDistribution section should be present

from .primary_heating import get_primary_heating_system
from .secondary_heating import get_secondary_heating_systems
from .additional_openings import get_additional_openings
from .hvac_control import get_hvac_control
from .hvac_distribution import get_hvac_distribution
from .heat_pumps import get_heat_pump
from .air_conditioning import get_air_conditioning

from .hot_water import get_hot_water_systems
from .hot_water_distribution import get_hot_water_distribution
from .water_fixtures import get_water_fixtures

from .ventilation import get_ventilation_systems

from .solar_generation import get_solar_generation


# This function compiles translations for all HVAC and DHW sections, as there are many dependencies between these sections
def get_systems(h2k_dict, model_data):

    # Only one primary heating system, define its id
    model_data.set_system_id({"primary_heating": "HeatingSystem1"})
    model_data.set_system_id({"air_conditioning": "CoolingSystem1"})
    model_data.set_system_id({"heat_pump": "HeatPump1"})
    model_data.set_system_id({"hvac_air_distribution": "HVACAirDistribution1"})
    model_data.set_system_id(
        {"hvac_hydronic_distribution": "HVACHydronicDistribution1"}
    )
    model_data.set_system_id({"primary_dhw": "WaterHeatingSystem1"})
    model_data.set_system_id({"secondary_dhw": "WaterHeatingSystem2"})
    model_data.set_system_id({"solar_dhw": "SolarThermalSystem1"})
    model_data.set_system_id({"dhw_distribution": "HotWaterDistribution1"})

    # Primary heating system as a component of the HVACPlant Section
    primary_heating_result = get_primary_heating_system(h2k_dict, model_data)

    secondary_heating_systems, remaining_fraction_floor_area = (
        get_secondary_heating_systems(h2k_dict, model_data)
    )

    if remaining_fraction_floor_area <= 0:
        model_data.add_warning_message(
            {
                "message": "The calculated area served by the active supplementary heating systems exceeds the total floor area of the home. The model will not be able to simulate in HPXML-OS."
            }
        )

    # note this doesn't build anything (no HPXML equivalent), just tracks whether there are flues/chimneys
    additional_openings_result = get_additional_openings(h2k_dict, model_data)

    # Primary cooling system as a component of the HVACPlant Section
    air_conditioning_result = get_air_conditioning(h2k_dict, model_data)

    # Heat Pumps handled here
    heat_pump_result = get_heat_pump(h2k_dict, model_data)
    # If backup type is integrated, get rid of the heating system

    # Always produces a complete dictionary, includes set point information.
    hvac_control_result = get_hvac_control(h2k_dict, model_data)

    # This may be an empty dictionary, e.g. for baseboards, in which case it must not be included in hvac_dict
    hvac_distribution_result = get_hvac_distribution(h2k_dict, model_data)

    primary_heating_id = model_data.get_system_id("primary_heating")
    primary_cooling_id = None
    heat_pump_backup_type = None
    if heat_pump_result != {}:
        primary_heating_id = model_data.get_system_id("heat_pump")
        primary_cooling_id = model_data.get_system_id("heat_pump")
        heat_pump_backup_type = model_data.get_building_detail("heat_pump_backup_type")

    elif air_conditioning_result != {}:
        primary_cooling_id = model_data.get_system_id("air_conditioning")

    # Rules for building the object below:
    # Only include a cooling system if an AC or Heat pump is present
    #   Note that it's impossible for both a heat pump and AC to be present because they're both type2 h2k systems
    # Only include a heating system if there is NOT a heat pump with an integrated back-up
    # Only include a HVAC distribution system if one has been built,
    #   Where the decision to build one is based on the heating/cooling system types present (based on heating_dist_type & ac_hp_dist_type)
    # TODO: FractionHeatingLoad must sum across all systems when dealing with multiple systems

    # Remove the "FractionHeatLoadServed" from the primary heating system if HeatPump[BackupType="separate"]
    # We don't really know we have to do this until everything is built
    if heat_pump_backup_type == "separate":
        primary_heating_result.pop("FractionHeatLoadServed", None)
        heat_pump_result["FractionHeatLoadServed"] = max(
            0, remaining_fraction_floor_area
        )
    elif heat_pump_backup_type == "integrated":
        heat_pump_result["FractionHeatLoadServed"] = max(
            0, remaining_fraction_floor_area
        )
    else:
        primary_heating_result["FractionHeatLoadServed"] = max(
            0, remaining_fraction_floor_area
        )

    hvac_dict = {
        "HVACPlant": {
            "PrimarySystems": {
                "PrimaryHeatingSystem": {"@idref": primary_heating_id},
                **(
                    {"PrimaryCoolingSystem": {"@idref": primary_cooling_id}}
                    if primary_cooling_id != None
                    else {}
                ),
            },
            **(
                {"HeatingSystem": secondary_heating_systems}
                if heat_pump_backup_type == "integrated"
                else {
                    "HeatingSystem": [
                        primary_heating_result,
                        *secondary_heating_systems,
                    ]
                }
            ),
            **({"HeatPump": heat_pump_result} if heat_pump_result != {} else {}),
            **(
                {"CoolingSystem": air_conditioning_result}
                if air_conditioning_result != {}
                else {}
            ),
        },
        "HVACControl": hvac_control_result,
        **(
            {"HVACDistribution": hvac_distribution_result}
            if hvac_distribution_result != {}
            else {}
        ),
    }

    hot_water_system_result, solar_dhw_system_result = get_hot_water_systems(
        h2k_dict, model_data
    )

    hot_water_distribution_result = get_hot_water_distribution(h2k_dict, model_data)
    water_fixtures_result = get_water_fixtures(h2k_dict, model_data)

    if hot_water_system_result[0] == {}:
        model_data.add_warning_message(
            {
                "message": "The h2k model does not have a DHW system defined, the HPXML simulation will not proceed."
            }
        )

    dhw_dict = {
        "WaterHeatingSystem": hot_water_system_result,
        "HotWaterDistribution": hot_water_distribution_result,
        "WaterFixture": water_fixtures_result,
    }

    solar_dhw_dict = (
        {"SolarThermalSystem": solar_dhw_system_result}
        if solar_dhw_system_result != {}
        else {}
    )

    # Ventilation Systems
    ventilation_results = get_ventilation_systems(h2k_dict, model_data)

    mech_vent_dict = (
        {"VentilationFans": {"VentilationFan": ventilation_results}}
        if ventilation_results != []
        else {}
    )

    # Generation (Photovoltaic) Systems
    generation_results = get_solar_generation(h2k_dict, model_data)

    return {
        "hvac_dict": hvac_dict,
        "dhw_dict": dhw_dict,
        "solar_dhw_dict": solar_dhw_dict,
        "mech_vent_dict": mech_vent_dict,
        "generation_dict": generation_results,
    }
