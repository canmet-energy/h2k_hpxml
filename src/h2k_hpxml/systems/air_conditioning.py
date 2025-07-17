import math

from ..utils import obj, h2k


# Translates air conditioning data from the "Type2" heating system section of h2k
def get_air_conditioning(h2k_dict, model_data):

    type2_heating_system = obj.get_val(h2k_dict, "HouseFile,House,HeatingCooling,Type2")

    # h2k files cannot be built without a Type 1 heating system, so we don't need to check for the presence of one
    type2_type = [
        x for x in list(type2_heating_system.keys()) if x != "@shadingInF280Cooling"
    ]

    type2_type = "None" if len(type2_type) == 0 else type2_type[0]

    type2_data = type2_heating_system.get(type2_type, {})

    # Get common specs
    cooling_sensible_heat_fraction = h2k.get_number_field(
        type2_data, "cooling_sensible_heat_fraction"
    )
    ac_cooling_eff = h2k.get_number_field(type2_data, "ac_cooling_efficiency")
    ac_capacity = h2k.get_number_field(type2_data, "ac_capacity")
    is_auto_sized = (
        "Calculated" == obj.get_val(type2_data, "Specifications,RatedCapacity,English")
        or ac_capacity == 0
    )

    ac_sizing_factor = h2k.get_number_field(type2_data, "ac_sizing_factor")

    is_cooling_cop = (
        obj.get_val(type2_data, "Specifications,Efficiency,@isCop") == "true"
    )
    # H2k's conversions:
    # COP = seer * 0.115 + 1.428;

    # Need cooling efficiency in SEER

    if is_cooling_cop:
        # Cooling provided in COP=
        ac_cooling_seer = (ac_cooling_eff - 1.428) / 0.115
    else:
        # Cooling provided in SEER
        # TODO: in v11.13, we can use the raw value here because they moved from SEER to EER=
        ac_cooling_seer = ac_cooling_eff

    ac_dict = {}

    if type2_type == "AirConditioning":
        ac_dict = {
            "SystemIdentifier": {"@id": model_data.get_system_id("air_conditioning")},
            "DistributionSystem": {
                "@idref": model_data.get_system_id("hvac_air_distribution")
            },
            "CoolingSystemType": "central air conditioner",
            "CoolingSystemFuel": "electricity",
            **({} if is_auto_sized else {"CoolingCapacity": ac_capacity}),
            # "CompressorType": "single stage", #Using HPXML's built-in defaulting at the moment
            # defaults to “single stage” if SEER <= 15, else “two stage” if SEER <= 21, else “variable speed”.
            "FractionCoolLoadServed": 1,
            "AnnualCoolingEfficiency": {
                "Units": "SEER",  # only option
                "Value": round(ac_cooling_seer, 2),
            },
            "SensibleHeatFraction": cooling_sensible_heat_fraction,
            # extension
            **(
                {
                    "extension": {
                        "CoolingAutosizingFactor": ac_sizing_factor,
                    }
                }
                if is_auto_sized
                else {}
            ),
        }

        model_data.set_ac_hp_distribution_type("air_regular velocity")

    return ac_dict
