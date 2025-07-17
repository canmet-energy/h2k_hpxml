from .windows import get_windows

from ..utils import obj, h2k


def get_doors(h2k_doors, parent_type, model_data):
    parent_id = {
        "Wall": model_data.get_wall_count(),
        "FoundationWall": model_data.get_foundation_wall_count(),
    }[parent_type]

    if not bool(h2k_doors):
        return {"hpxml_doors": [], "hpxml_windows_doors": []}

    # Always process as list
    h2k_doors = h2k_doors if isinstance(h2k_doors, list) else [h2k_doors]

    hpxml_doors = []
    hpxml_windows_doors = []
    for door in h2k_doors:
        model_data.inc_door_count()
        door_id = f"Door{model_data.get_door_count()}"
        door_label = door.get("Label", "No Label")

        door_rval = h2k.get_number_field(door, "door_r_value")
        door_height = h2k.get_number_field(door, "door_height")
        door_width = h2k.get_number_field(door, "door_width")
        door_area = round(door_height * door_width, 2)

        new_door = {
            "SystemIdentifier": {"@id": door_id},
            "AttachedToWall": {"@idref": f"{parent_type}{parent_id}"},
            "Area": door_area,
            # "Azimuth": "180",
            "RValue": door_rval,
            "extension": {"H2kLabel": f"{door_label}"},
        }

        # Handle subcomponents on door (windows)
        # Subcomponents not nested with HPXML
        h2k_windows = door.get("Components", {}).get("Window", {})
        window_output = get_windows(h2k_windows, "Wall", model_data)

        hpxml_windows_doors = [*hpxml_windows_doors, *window_output["hpxml_windows"]]
        total_window_area = window_output["total_window_area"]

        # Because we can't attach windows to doors in HPXML,
        # we need to subtract any area from the door
        if total_window_area > 0:
            new_door["Area"] = new_door["Area"] - total_window_area

        hpxml_doors = [*hpxml_doors, new_door]

    return {"hpxml_doors": hpxml_doors, "hpxml_windows_doors": hpxml_windows_doors}
