import math

from ..utils import obj, h2k


def get_additional_openings(h2k_dict, model_data):

    if (
        "AdditionalOpenings"
        not in obj.get_val(h2k_dict, "HouseFile,House,HeatingCooling").keys()
    ):
        return {}

    additional_openings = obj.get_val(
        h2k_dict, "HouseFile,House,HeatingCooling,AdditionalOpenings,Opening"
    )

    additional_openings = (
        additional_openings
        if isinstance(additional_openings, list)
        else [additional_openings]
    )

    for opening in additional_openings:
        flue_diameter = h2k.get_number_field(
            opening, "additional_opening_flue_diameter"
        )

        if flue_diameter > 0:
            model_data.set_flue_diameters(flue_diameter)

    return {}
