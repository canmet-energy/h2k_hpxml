from ..utils import obj, h2k


def get_appliances(h2k_dict, model_data={}):
    building_type = model_data.get_building_detail("building_type")
    num_occupants = model_data.get_building_detail("num_occupants")

    # Dryer to use 916 kWh/y with 4 occupants.
    # 687 kWh/y for a house (SOC)
    # 458 kWh/y for a murb (SOC)
    # TODO: find appropriate CombinedEnergyFactor to achieve above
    dryer_exhaust = h2k.get_number_field(h2k_dict, "dryer_exhaust_flowrate")

    # Range targets:
    # 565 kWh/y for a all (SOC)

    (
        cw_label_energy_rating,
        cw_label_cycles_year,
        cw_capacity,
        cw_ghwc,
        cw_elec_rate,
        cw_gas_rate,
        cw_imef,
    ) = calc_required_clothes_washer_specs(building_type, num_occupants)

    (
        dw_label_energy_rating,
        dw_label_cycles_year,
        dw_capacity,
        dw_ghwc,
    ) = calc_required_dishwasher_specs(building_type, num_occupants)

    dryer_combined_energy_factor = calc_required_dryer_specs(
        building_type,
        num_occupants,
        cw_label_energy_rating,
        cw_capacity,
        cw_imef,
    )

    range_usage_multiplier = calc_required_range_specs(building_type, num_occupants)

    # TODO: Other hot water consumption: 2.92 L/week
    # TODO: Shower/Bathroom faucet consumption

    hpxml_appliances = {
        "ClothesWasher": {
            "SystemIdentifier": {"@id": "ClothesWasher1"},
            "Location": "conditioned space",
            "IntegratedModifiedEnergyFactor": cw_imef,
            "RatedAnnualkWh": cw_label_energy_rating,
            "LabelElectricRate": cw_elec_rate,
            "LabelGasRate": cw_gas_rate,
            "LabelAnnualGasCost": cw_ghwc,
            "LabelUsage": cw_label_cycles_year / 52,
            "Capacity": cw_capacity,
        },
        "ClothesDryer": {
            "SystemIdentifier": {"@id": "ClothesDryer1"},
            "Location": "conditioned space",
            "FuelType": "electricity",
            "CombinedEnergyFactor": dryer_combined_energy_factor,
            "Vented": True,
            "VentedFlowRate": dryer_exhaust or 80.52,  # default
        },
        "Dishwasher": {
            "SystemIdentifier": {"@id": "Dishwasher1"},
            "Location": "conditioned space",
            "RatedAnnualkWh": dw_label_energy_rating,
            "PlaceSettingCapacity": dw_capacity,
            "LabelElectricRate": 0.12,  # Defaults used
            "LabelGasRate": 1.09,  # Defaults used
            "LabelAnnualGasCost": dw_ghwc,
            "LabelUsage": dw_label_cycles_year / 52,
        },
        "Refrigerator": {
            "SystemIdentifier": {"@id": "Refrigerator1"},
            "Location": "conditioned space",
            "RatedAnnualkWh": 639,
            "PrimaryIndicator": True,
        },
        "CookingRange": {
            "SystemIdentifier": {"@id": "CookingRange1"},
            "Location": "conditioned space",
            "FuelType": "electricity",
            "IsInduction": False,
            "extension": {"UsageMultiplier": range_usage_multiplier},
        },
        "Oven": {"SystemIdentifier": {"@id": "Oven1"}, "IsConvection": False},
    }

    return hpxml_appliances


# from HPXML-OS workflow
def get_adjusted_num_bedrooms(building_type, num_occupants):
    if building_type == "house":
        return -1.47 + 1.69 * num_occupants
    else:
        return -0.68 + 1.09 * num_occupants


def calc_required_clothes_washer_specs(building_type, num_occupants):
    # Calculates the required clothes washer specs based on the model used in the HPXML workflow
    # Goal is to have HPXML produce the same kWh/day and gal/day as H2k
    # model: https://www.resnet.us/wp-content/uploads/ANSI_RESNET_ICC-301-2019-Addendum-A-2019_7.16.20-1.pdf
    # The constants below have been tested with houses having 1-10 bedrooms, where the range of observed values are:
    # 350 < label_energy_rating < 472
    # 343 < label_cycles_year < 643

    adjusted_bedrooms = get_adjusted_num_bedrooms(building_type, num_occupants)

    volume_target = (
        (54 / 3.785411784) * 1.9 * num_occupants / 7
    )  # gal/day, SOC HARDCODED

    energy_target = 148 if building_type == "house" else 98.5

    # fixed parameters
    washer_capacity = 3  # [ft3], this number differs from defaults, but is used to match hpxml outputs to h2k inputs
    ghwc = 60  # label's $/y in gas cost to operate, must be 60 to allow 3 ft3 to work

    # constants and helper calcs from model
    elec_h2o = 0.0178
    gas_h2o = 0.3914
    cw_imef = 0.9  # needed for Dryer
    elec_rate = 0.3  # needed for Dryer
    gas_rate = 1.09  # Default
    cw_appl_denom = elec_rate * (gas_h2o / gas_rate) - elec_h2o
    gas_ratio = gas_h2o / gas_rate

    b1 = 364.095 * adjusted_bedrooms + 1284.12
    a1 = gas_ratio / cw_appl_denom
    a2 = elec_h2o / cw_appl_denom

    label_energy_rating = (
        volume_target * (365 / elec_h2o) * ((2.08 * washer_capacity + 1.59) / b1)
        + (a1 * ghwc)
    ) / (1 + a2)

    label_cycles_year = (
        b1
        * ((a1 * ghwc) - (a2 * label_energy_rating))
        / (energy_target * (2.08 * washer_capacity + 1.59))
    )

    return (
        label_energy_rating,
        label_cycles_year,
        washer_capacity,
        ghwc,
        elec_rate,
        gas_rate,
        cw_imef,
    )


def calc_required_dishwasher_specs(building_type, num_occupants):
    # Calculates the required diswasher specs based on the model used in the HPXML workflow
    # Goal is to have HPXML produce the same kWh/day and gal/day as H2k
    # model: https://www.resnet.us/wp-content/uploads/ANSI_RESNET_ICC-301-2019-Addendum-A-2019_7.16.20-1.pdf
    # The constants below have been tested with houses having 1-10 bedrooms, where the range of observed values are:
    # 272 < label_energy_rating < 319
    # 45 < label_cycles_year < 218

    adjusted_bedrooms = get_adjusted_num_bedrooms(building_type, num_occupants)

    volume_target = (
        (19 / 3.785411784) * 1.37 * num_occupants / 7
    )  # gal/day, SOC HARDCODED

    energy_target = 260 if building_type == "house" else 130

    # fixed parameters
    dishwasher_capacity = 12  # [place settings], represents a "Standard" dishwasher
    ghwc = 22.23  # label's $/y in gas cost to operate

    # constants from model
    actual_cycles_year = 88.4 + (34.9 * adjusted_bedrooms)
    a1 = 0.12 * (0.5497 / 1.09) - 0.02504
    a2 = a1 + 0.02504
    a3 = ghwc * 0.5497 / 1.09

    label_energy_rating = (
        volume_target * (365 / (0.02504 * actual_cycles_year)) * a1 + a3
    ) * (1 / a2)

    label_cycles_year = ((a3 - 0.02504 * label_energy_rating) / a1) * (
        actual_cycles_year / energy_target
    )

    return label_energy_rating, label_cycles_year, dishwasher_capacity, ghwc


def calc_required_dryer_specs(
    building_type,
    num_occupants,
    cw_label_energy_rating,
    cw_capacity,
    cw_imef,
):
    adjusted_bedrooms = get_adjusted_num_bedrooms(building_type, num_occupants)

    energy_target = 687 if building_type == "house" else 458

    rmc = (0.97 * (cw_capacity / cw_imef) - cw_label_energy_rating / 312.0) / (
        (2.0104 * cw_capacity + 1.4242) * 0.455
    ) + 0.04
    acy = (164.0 + 46.5 * adjusted_bedrooms) * (
        (3.0 * 2.08 + 1.59) / (cw_capacity * 2.08 + 1.59)
    )

    dryer_combined_energy_factor = (
        ((100 * (rmc - 0.04)) / 55.5) * (8.45 / energy_target) * acy
    )

    return dryer_combined_energy_factor


def calc_required_range_specs(building_type, num_occupants):
    adjusted_bedrooms = get_adjusted_num_bedrooms(building_type, num_occupants)

    target_energy = 565  # all housing types

    usage_multiplier = target_energy / (331 + 39.0 * adjusted_bedrooms)

    return usage_multiplier
