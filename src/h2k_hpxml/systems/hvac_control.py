import math

from ..utils import obj, h2k


# Returns the HVAC Control system dictionary
# Essentially contains the "Temperatures" section of h2k
def get_hvac_control(h2k_dict, model_data):

    setpoint_heating_day = h2k.get_number_field(h2k_dict, "setpoint_heating_day")
    setpoint_cooling_day = h2k.get_number_field(h2k_dict, "setpoint_cooling_day")
    setpoint_heating_night = h2k.get_number_field(h2k_dict, "setpoint_heating_night")
    setback_heating_duration = h2k.get_number_field(
        h2k_dict, "setback_heating_duration"
    )

    # Note
    # Setbacks are always present in h2k
    # setback start hours can be defined in extension/SetbackStartHourHeating, but the default is the same as h2k (11pm)
    # TODO: convert simple set back inputs to hourly arrays if h2k doesn't do setbacks on weekends
    hvac_control_dict = {
        "SystemIdentifier": {"@id": "HVACControl1"},
        "SetpointTempHeatingSeason": setpoint_heating_day,
        "SetbackTempHeatingSeason": setpoint_heating_night,
        "TotalSetbackHoursperWeekHeating": setback_heating_duration * 7,
        "SetpointTempCoolingSeason": setpoint_cooling_day,
    }

    return hvac_control_dict


# Element Order:
# SystemInfo
# ConnectedDevice
# AttachedToZone
# ControlType
# SetpointTempHeatingSeason
# SetbackTempHeatingSeason
# TotalSetbackHoursperWeekHeating
# SetupTempCoolingSeason
# SetpointTempCoolingSeason
# TotalSetupHoursperWeekCooling
# HotWaterResetControl
# HeatLowered
# ACAdjusted
# FractionThermostaticRadiatorValves
# FractionElectronicZoneValves
# HVACSystemsServed
# HeatingSeason
# CoolingSeason
