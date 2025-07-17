from ..utils import obj, h2k


def get_windows(h2k_windows, parent_type, model_data):
    parent_id = {
        "Wall": model_data.get_wall_count(),
        "FoundationWall": model_data.get_foundation_wall_count(),
    }[parent_type]

    if not bool(h2k_windows):
        return {"hpxml_windows": [], "total_window_area": 0}

    # Always process as list
    h2k_windows = h2k_windows if isinstance(h2k_windows, list) else [h2k_windows]

    hpxml_windows = []
    total_window_area = 0
    for window in h2k_windows:
        new_windows = []
        dup_window_count = h2k.get_number_field(window, "window_count")
        window_label = window.get("Label", "No Label")

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
            total_window_area += window_area

            if window_rval == 0:
                window_uval = 0
            else:
                window_uval = 1 / window_rval

            window_orientation = h2k.get_selection_field(window, "window_direction")

            has_overhang = window_header_height != 0 and window_overhang_width != 0

            if window_header_height < 0:
                model_data.add_warning_message(
                    {
                        "message": f"A negative window header height was specified for a window ({window_label}), which is not supported in HPXML. Its value has been overwritten with a length of 0 to allow the calculation to proceed."
                    }
                )
                window_header_height = 0

            distance_to_bottom = (
                window_header_height + window_height if has_overhang else 0
            )

            new_window = {
                "SystemIdentifier": {"@id": window_id},
                "Area": window_area,
                "Azimuth": window_orientation,
                "UFactor": round(window_uval, 4),
                "SHGC": round(window_shgc, 2),
                "InteriorShading": {
                    "SystemIdentifier": {"@id": f"{window_id}InteriorShading"},
                    "SummerShadingCoefficient": "1",
                    "WinterShadingCoefficient": "1",
                },
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
                "FractionOperable": "0",
                "AttachedToWall": {"@idref": f"{parent_type}{parent_id}"},
                "extension": {"H2kLabel": f"{window_label}"},
            }

            window_properties = False
            if window_properties:
                frame_type = "Wood"
                glass_layers = "single-pane"
                glass_type = "tinted"
                gas_fill = "air"
                thermal_break = False  # if aluminum frame we need this in the object

                new_window = {
                    "SystemIdentifier": {"@id": window_id},
                    "Area": window_area,
                    "Azimuth": window_orientation,
                    "FrameType": {[frame_type]: None},
                    "GlassLayers": glass_layers,
                    "GlassType": glass_type,
                    "GasFill": gas_fill,
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
                    "AttachedToWall": {"@idref": f"{parent_type}{parent_id}"},
                }

                if frame_type == "aluminum":
                    new_window["FrameType"][frame_type] = {
                        "ThermalBreak": thermal_break
                    }

            new_windows = [*new_windows, new_window]

        hpxml_windows = [*hpxml_windows, *new_windows]

    return {"hpxml_windows": hpxml_windows, "total_window_area": total_window_area}
