from ..utils import obj, h2k


# Gets all exposed floor components
def get_floors(h2k_dict, model_data={}):
    components = obj.get_val(h2k_dict, "HouseFile,House,Components")

    if "Floor" not in components.keys():
        h2k_exp_floors = []
    else:
        h2k_exp_floors = components["Floor"]

    # Always process as array
    h2k_exp_floors = (
        h2k_exp_floors if isinstance(h2k_exp_floors, list) else [h2k_exp_floors]
    )

    hpxml_floors = []
    for floor in h2k_exp_floors:
        model_data.inc_floor_count()
        # Get required details from h2k exposed floors
        floor_id = f"Floor{model_data.get_floor_count()}"
        floor_label = floor.get("Label", "No Label")

        floor_rval = h2k.get_number_field(floor, "exp_floor_r_value")
        floor_area = h2k.get_number_field(floor, "exp_floor_area")

        res_facility_type = model_data.get_building_detail("res_facility_type")
        attached_unit = (
            "attached" in res_facility_type or "apartment" in res_facility_type
        )

        buffered_attached_type = (
            "other non-freezing space" if attached_unit else "outside"
        )

        floor_exterior = (
            buffered_attached_type
            if floor["@adjacentEnclosedSpace"] == "true"
            else "outside"
        )

        # This is required here for floor area calculations later
        model_data.add_foundation_detail(
            {
                "type": "expFloor",
                "total_perimeter": 0,
                "total_area": floor_area,
                "exposed_perimeter": 0,
                "exposed_fraction": 0,
            }
        )

        # Build hpxml floor
        new_floor = {
            "SystemIdentifier": {"@id": floor_id},
            "ExteriorAdjacentTo": floor_exterior,
            "InteriorAdjacentTo": "conditioned space",  # always
            **(
                {"FloorOrCeiling": "floor"}
                if buffered_attached_type == "other non-freezing space"
                else {}
            ),
            "FloorType": {"WoodFrame": None},  # for now, always WoodStud
            # "FloorOrCeiling": "floor",
            "Area": floor_area,  # [ft2]
            "InteriorFinish": {"Type": "none"},  # default for non-ceiling floors
            "Insulation": {
                "SystemIdentifier": {"@id": f"{floor_id}Insulation"},
                "AssemblyEffectiveRValue": round(floor_rval, 2),
            },
            "extension": {"H2kLabel": f"{floor_label}"},
        }

        hpxml_floors = [*hpxml_floors, new_floor]

    return {
        "floors": hpxml_floors,
    }
