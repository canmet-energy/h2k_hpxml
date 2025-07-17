from ..utils import obj, h2k


def get_rim_joists(h2k_floor_headers, parent_type, model_data):
    parent_id = {
        "Wall": model_data.get_wall_count(),
        "FoundationWall": model_data.get_foundation_wall_count(),
    }[parent_type]

    if not bool(h2k_floor_headers):
        return {"hpxml_rim_joists": []}

    # Always process as list
    h2k_floor_headers = (
        h2k_floor_headers
        if isinstance(h2k_floor_headers, list)
        else [h2k_floor_headers]
    )

    hpxml_rim_joists = []
    for floor_header in h2k_floor_headers:
        model_data.inc_floor_header_count()
        rim_joist_id = f"RimJoist{model_data.get_floor_header_count()}"
        floor_header_label = floor_header.get("Label", "No Label")

        rim_joist_rval = h2k.get_number_field(floor_header, "floor_header_r_value")
        rim_joist_height = h2k.get_number_field(floor_header, "floor_header_height")
        rim_joist_perimeter = h2k.get_number_field(
            floor_header, "floor_header_perimeter"
        )
        rim_joist_area = round(rim_joist_height * rim_joist_perimeter, 2)

        res_facility_type = model_data.get_building_detail("res_facility_type")
        attached_unit = (
            "attached" in res_facility_type or "apartment" in res_facility_type
        )
        buffered_attached_type = (
            "other non-freezing space" if attached_unit else "outside"
        )

        rim_joist_exterior = (
            buffered_attached_type
            if floor_header["@adjacentEnclosedSpace"] == "true"
            else "outside"
        )

        new_rim_joists = {
            "SystemIdentifier": {"@id": rim_joist_id},
            "ExteriorAdjacentTo": rim_joist_exterior,
            "InteriorAdjacentTo": (
                "basement - conditioned"
                if parent_type == "Basement"
                else "conditioned space"
            ),
            "Area": rim_joist_area,
            "Insulation": {
                "SystemIdentifier": {"@id": f"{rim_joist_id}Insulation"},
                "AssemblyEffectiveRValue": round(rim_joist_rval, 2),
            },
            "extension": {"H2kLabel": f"{floor_header_label}"},
        }

        hpxml_rim_joists = [*hpxml_rim_joists, new_rim_joists]

    return {"hpxml_rim_joists": hpxml_rim_joists}
