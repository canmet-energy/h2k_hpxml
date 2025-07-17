import math

from ..utils import obj, h2k
from operator import itemgetter


# Applies ASHRAE 140 assumptions to file
def apply_ashrae_140(hpxml_dict, h2k_dict, model_data):
    print("APPLYING ASHRAE 140")

    # Applies ASHRAE 140 assumptions in HPXML-OS process
    # Sets infiltration as a constant
    # Changes air films
    # Other details specified by standard
    hpxml_dict["HPXML"]["SoftwareInfo"] = {
        "extension": {"ApplyASHRAE140Assumptions": "true"}
    }

    # Apply site info
    hpxml_dict["HPXML"]["Building"]["BuildingDetails"]["BuildingSummary"]["Site"] = {
        "Surroundings": "stand-alone",
        "VerticalSurroundings": "no units above or below",
    }

    # Set occupancy to 0
    hpxml_dict["HPXML"]["Building"]["BuildingDetails"]["BuildingSummary"][
        "BuildingOccupancy"
    ]["NumberofResidents"] = 0

    # Drop bathrooms
    hpxml_dict["HPXML"]["Building"]["BuildingDetails"]["BuildingSummary"][
        "BuildingConstruction"
    ].pop("NumberofBathrooms", None)

    # Drop BuildingSummary extensions
    hpxml_dict["HPXML"]["Building"]["BuildingDetails"]["BuildingSummary"].pop(
        "extension", None
    )

    # Delete all systems, overwrite HVAC Control with specified set points
    hpxml_dict["HPXML"]["Building"]["BuildingDetails"]["Systems"] = {
        "HVAC": {
            "HVACControl": {
                "SystemIdentifier": {"@id": "HVACControl1"},
                "SetpointTempHeatingSeason": 68,
                "SetpointTempCoolingSeason": 78,
            }
        }
    }

    # ASHRAE 140 assumed to get ACH natural value from ventilation requirements section
    ventilation_requirement_achnat = h2k.get_number_field(
        h2k_dict, "ventilation_requirement_achnat"
    )
    hpxml_dict["HPXML"]["Building"]["BuildingDetails"]["Enclosure"][
        "AirInfiltration"
    ].pop("extension", None)
    hpxml_dict["HPXML"]["Building"]["BuildingDetails"]["Enclosure"]["AirInfiltration"][
        "AirInfiltrationMeasurement"
    ].pop("HousePressure", None)
    hpxml_dict["HPXML"]["Building"]["BuildingDetails"]["Enclosure"]["AirInfiltration"][
        "AirInfiltrationMeasurement"
    ]["BuildingAirLeakage"] = {
        "UnitofMeasure": "ACHnatural",
        "AirLeakage": ventilation_requirement_achnat,
    }

    # Delete Appliances and Lighting Sections
    hpxml_dict["HPXML"]["Building"]["BuildingDetails"].pop("Appliances", None)
    hpxml_dict["HPXML"]["Building"]["BuildingDetails"].pop("Lighting", None)

    # Overwrite MiscLoads with specified values to achieve desired internal gains
    # Special Cases L170 get no loads
    baseloads_summary = (
        h2k_dict.get("HouseFile", {})
        .get("House", {})
        .get("BaseLoads", {})
        .get("Summary", {})
    )

    appliances, lighting, other_elec, exterior_use = itemgetter(
        "@electricalAppliances", "@lighting", "@otherElectric", "@exteriorUse"
    )(baseloads_summary)

    if all(x == "0" for x in [appliances, lighting, other_elec, exterior_use]):
        hpxml_dict["HPXML"]["Building"]["BuildingDetails"]["MiscLoads"] = {
            "PlugLoad": {
                "SystemIdentifier": {"@id": "PlugLoad1"},
                "PlugLoadType": "other",
                "Load": {
                    "Units": "kWh/year",
                    "Value": 0,
                },
            }
        }
    else:
        total_load = 7302.2
        sensible_fraction = 0.822
        latent_fraction = 0.178
        day_schedule_fractions = "0.0203, 0.0203, 0.0203, 0.0203, 0.0203, 0.0339, 0.0426, 0.0852, 0.0497, 0.0304, 0.0304, 0.0406, 0.0304, 0.0254, 0.0264, 0.0264, 0.0386, 0.0416, 0.0447, 0.0700, 0.0700, 0.0731, 0.0731, 0.0660"
        month_schedule_fractions = (
            "1.0, 1.0, 1.0, 1.0, 1.0, 1.0, 1.0, 1.0, 1.0, 1.0, 1.0, 1.0"
        )
        hpxml_dict["HPXML"]["Building"]["BuildingDetails"]["MiscLoads"] = {
            "PlugLoad": {
                "SystemIdentifier": {"@id": "PlugLoad1"},
                "PlugLoadType": "other",
                "Load": {
                    "Units": "kWh/year",
                    "Value": total_load,
                },
                "extension": {
                    "FracSensible": sensible_fraction,
                    "FracLatent": latent_fraction,
                    "WeekdayScheduleFractions": day_schedule_fractions,
                    "WeekendScheduleFractions": day_schedule_fractions,
                    "MonthlyScheduleMultipliers": month_schedule_fractions,
                },
            }
        }

    return hpxml_dict
