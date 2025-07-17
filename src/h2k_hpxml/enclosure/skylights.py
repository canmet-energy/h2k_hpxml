from ..utils import obj, h2k


def get_skylights(h2k_skylights, skylight_attachment, model_data):
    if skylight_attachment == {}:
        return {
            "hpxml_skylights": [],
            "total_skylight_area": 0,
        }

    # We get the parent ID at the level above because we need to know the type of ceiling/roof/attic we're dealing with
    # For ceilings with attics, we use the floor of the attic (representing a skylight with a shaft through the attic)
    # For flat/cathedral ceilings, we use the roof ID

    if not bool(h2k_skylights):
        return {"hpxml_skylights": [], "total_skylight_area": 0}

    # Always process as list
    h2k_skylights = (
        h2k_skylights if isinstance(h2k_skylights, list) else [h2k_skylights]
    )

    hpxml_skylights = []
    total_skylight_area = 0
    for window in h2k_skylights:
        new_skylights = []
        dup_window_count = h2k.get_number_field(window, "window_count")
        skylight_label = window.get("Label", "No Label")

        # Handling number of identical windows in h2k
        for i in range(dup_window_count):
            model_data.inc_window_count()
            window_id = f"Window{model_data.get_window_count()}"

            window_rval = h2k.get_number_field(window, "window_r_value")
            window_shgc = h2k.get_number_field(window, "window_shgc")
            window_height = h2k.get_number_field(window, "window_height")  # [ft]
            window_width = h2k.get_number_field(window, "window_width")  # [ft]
            window_header_height = h2k.get_number_field(
                window, "window_header_height"
            )  # [ft]
            window_overhang_width = h2k.get_number_field(
                window, "window_overhang_width"
            )  # [ft]
            window_area = round(window_height * window_width, 2)
            total_skylight_area += window_area

            if window_rval == 0:
                window_uval = 0
            else:
                window_uval = 1 / window_rval

            window_orientation = h2k.get_selection_field(window, "window_direction")

            has_overhang = window_header_height != 0 or window_overhang_width != 0
            distance_to_bottom = (
                window_header_height + window_height if has_overhang else 0
            )

            new_skylight = {
                "SystemIdentifier": {"@id": window_id},
                "Area": window_area,
                "Azimuth": window_orientation,
                "UFactor": window_uval,
                "SHGC": window_shgc,
                # "InteriorShading": {
                #     "SystemIdentifier": {"@id": f"{window_id}InteriorShading"},
                #     "SummerShadingCoefficient": "0.7",
                #     "WinterShadingCoefficient": "0.85",
                # },
                # "FractionOperable": "0.67",
                **(
                    {
                        "Overhangs": {
                            "Depth": window_overhang_width,
                            "DistanceToTopOfWindow": window_header_height,
                            "DistanceToBottomOfWindow": distance_to_bottom,
                        }
                    }
                    if has_overhang
                    else {}
                ),
                **skylight_attachment,
                "extension": {"H2kLabel": f"{skylight_label}"},
            }

            new_skylights = [*new_skylights, new_skylight]

        hpxml_skylights = [*hpxml_skylights, *new_skylights]

    return {
        "hpxml_skylights": hpxml_skylights,
        "total_skylight_area": total_skylight_area,
    }
