import math


from ..utils import obj, h2k


def get_slabs(h2k_dict, model_data={}):
    components = obj.get_val(h2k_dict, "HouseFile,House,Components")

    if "Slab" not in components.keys():
        h2k_slabs = []
    else:
        h2k_slabs = components["Slab"]

    # Always process as array
    h2k_slabs = h2k_slabs if isinstance(h2k_slabs, list) else [h2k_slabs]

    hpxml_slabs = []
    hpxml_foundations = []

    for slab in h2k_slabs:
        model_data.inc_slab_count()
        model_data.inc_foundation_count()

        foundation_id = f"Foundation{model_data.get_foundation_count()}"
        slab_id = f"Slab{model_data.get_slab_count()}"
        slab_label = slab.get("Label", "No Label")

        # Get required details from h2k slab
        is_slab_rectangular = h2k.get_selection_field(slab, "foundation_rectangular")
        slab_floor_area = h2k.get_number_field(slab, "foundation_floor_area")
        slab_perimeter = h2k.get_number_field(slab, "foundation_perimeter")
        slab_exp_perimeter = h2k.get_number_field(slab, "foundation_exp_perimeter")
        slab_width = h2k.get_number_field(slab, "foundation_width")
        slab_length = h2k.get_number_field(slab, "foundation_length")

        foundation_tot_perimeter = (
            2 * (slab_width + slab_length) if is_slab_rectangular else slab_perimeter
        )

        foundation_tot_area = (
            slab_width * slab_length if is_slab_rectangular else slab_floor_area
        )

        model_data.add_foundation_detail(
            {
                "type": "slab",
                "total_perimeter": foundation_tot_perimeter,
                "total_area": foundation_tot_area,
                "exposed_perimeter": slab_exp_perimeter,
                "exposed_fraction": slab_exp_perimeter / foundation_tot_perimeter,
            }
        )

        slab_config = obj.get_val(slab, "Configuration,#text")
        slab_ins = slab_config[2]  # "N" None, "A" Above, "B" Below

        slab_r_val = 0  # nominal R-value, so not including concrete
        insulation_spans_slab = True
        slab_ins_width = round(
            math.sqrt(foundation_tot_area) / 2, 2
        )  # default to "full"

        slab_skirt_ins_depth = 0
        slab_skirt_rval = 0

        if slab_ins != "N":
            # Dealing with either above or below slab insulation
            slab_r_val = h2k.get_number_field(slab, "slab_r_value")
            # get perimeter if applicable
            perimeter_slab_ins = h2k.get_foundation_config("perimeter_slab_ins")
            if slab_config in perimeter_slab_ins.keys():
                insulation_spans_slab = False
                slab_ins_width = perimeter_slab_ins.get(slab_config, slab_ins_width)

            # check for skirt insulation
            slab_skirt_ins = h2k.get_foundation_config("slab_skirt_ins")
            if slab_config in slab_skirt_ins:
                slab_skirt_ins_depth = 1.9685  # always 60cm
                slab_skirt_rval = h2k.get_number_field(slab, "slab_skirt_r_value")

        # Foundation
        new_foundation = {
            "SystemIdentifier": {"@id": foundation_id},
            "FoundationType": {"SlabOnGrade": None},
            "AttachedToSlab": {"@idref": slab_id},
            "extension": {"H2kLabel": f"{slab_label}"},
        }

        # Slab
        new_slab = {
            "SystemIdentifier": {"@id": slab_id},
            "InteriorAdjacentTo": "conditioned space",
            "Area": foundation_tot_area,
            "Thickness": "4.0",  # Default
            "ExposedPerimeter": (
                foundation_tot_perimeter
                if slab_exp_perimeter == 0
                else slab_exp_perimeter
            ),
            "PerimeterInsulation": {
                "SystemIdentifier": {"@id": f"{slab_id}PerimeterInsulation"},
                "Layer": {
                    "NominalRValue": slab_skirt_rval,
                    "InsulationDepth": slab_skirt_ins_depth,
                },
            },
            "UnderSlabInsulation": {
                "SystemIdentifier": {"@id": f"{slab_id}UnderSlabInsulation"},
                "Layer": {
                    "NominalRValue": slab_r_val,
                    **(
                        {"InsulationWidth": slab_ins_width}
                        if not insulation_spans_slab
                        else {}
                    ),
                    "InsulationSpansEntireSlab": insulation_spans_slab,
                },
            },
            "extension": {
                "CarpetFraction": "0.0",
                "CarpetRValue": "0.0",
                "H2kLabel": f"{slab_label}",
            },  # defaults to >0 if not provided
        }

        hpxml_slabs = [*hpxml_slabs, new_slab]
        hpxml_foundations = [*hpxml_foundations, new_foundation]

    return {"slabs": hpxml_slabs, "foundations": hpxml_foundations}
