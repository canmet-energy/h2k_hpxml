# Utility functions that calculate expected hot water usage in HPXML
import json
import os
import sys
from operator import itemgetter

from . import obj
from . import units
from . import h2k


def get_fixtures_multiplier(h2k_dict, model_data):

    target_daily_hot_water_usgpd = h2k.get_number_field(
        h2k_dict, "total_daily_hot_water"
    )

    clothes_washer_usgpd = model_data.get_building_detail("clothes_washer_usgpd")
    dishwasher_usgpd = model_data.get_building_detail("dishwasher_usgpd")

    target_fixture_waste_usgpd = target_daily_hot_water_usgpd - (
        clothes_washer_usgpd + dishwasher_usgpd
    )

    if target_fixture_waste_usgpd <= 0:
        model_data.add_warning_message(
            {
                "message": "The calculated fixture hot water usage requirement was below zero. Default values will be used, which will result in a discrepancy in hot water usage between HOT2000 and HPXML."
            }
        )
        return 1

    num_occupants = model_data.get_building_detail("num_occupants")

    frac_low_flow_fixtures = 0  # SOC Hardcoded

    fixture_usgpd = calc_fixture_hot_water(num_occupants, frac_low_flow_fixtures)
    waste_usgpd = calc_distribution_waste(num_occupants, frac_low_flow_fixtures)
    # print("fixture_usgpd", fixture_usgpd)
    # print("waste_usgpd", waste_usgpd)

    # Multiplying the gpd values by a calibration equation
    # Even though our fixture and waste gpd values match those calculated in the HPXML-OS workflow, these values appear to be "design" values, and aren't necessarily what the simulation experiences
    # The calibration equation assumes that the default fixture schedule is used. Any changes to the schedule should be reflected here and considered when re-evaluating the equation below
    factor = (
        0.00495951595602586 * (target_daily_hot_water_usgpd**2)
        - 0.469835725564538 * target_daily_hot_water_usgpd
        + 11.6641677398892
    )

    calculated_fixture_waste_usgpd = factor * (fixture_usgpd + waste_usgpd)

    fixtures_multiplier = target_fixture_waste_usgpd / calculated_fixture_waste_usgpd

    return fixtures_multiplier


# returns hot water fixture usage in US Gal/day
def calc_fixture_hot_water(num_occupants, frac_low_flow_fixtures):
    # Based on Operational calculation in HotWaterAppliances.get_fixtures_gpd

    ref_f_gpd = max(-4.84 + 18.6 * num_occupants, 0)

    f_eff = 1.0 - (0.05 * frac_low_flow_fixtures)

    return f_eff * ref_f_gpd


# returns hot water distribution waste usage in US Gal/day
# All Calculations use asset method for Standard hot water distribution system type
def calc_distribution_waste(
    num_occupants,
    frac_low_flow_fixtures,
):

    sys_factor = 1.0  # Always standard distribution system and pipe r value < 3

    ref_w_gpd = 7.16 * (num_occupants**0.7)

    o_frac = 0.25
    o_cd_eff = 0.0

    # ref_pipe_l = get_std_pipe_length(
    #     has_uncond_bsmnt, has_cond_bsmnt, conditioned_floor_area, num_storeys
    # )
    p_ratio = 1  # hot_water_distribution.standard_piping_length / ref_pipe_l

    o_w_gpd = ref_w_gpd * o_frac * (1.0 - o_cd_eff)  # Eq. 4.2-12
    s_w_gpd = (ref_w_gpd - ref_w_gpd * o_frac) * p_ratio * sys_factor  # Eq. 4.2-13

    wd_eff = 1.0

    f_eff = 1.0 - (0.05 * frac_low_flow_fixtures)

    mw_gpd = f_eff * (o_w_gpd + s_w_gpd * wd_eff)

    return mw_gpd


# not used because we're always using the standard pipe length so the ratio is 1
def get_std_pipe_length(
    has_uncond_bsmnt, has_cond_bsmnt, conditioned_floor_area, num_storeys
):
    bsmnt = 0
    if has_uncond_bsmnt & (not has_cond_bsmnt):
        bsmnt = 1

    return (
        2.0 * (conditioned_floor_area / num_storeys) ** 0.5
        + 10.0 * num_storeys
        + 5.0 * bsmnt
    )  # PipeL in ANSI 301
