import functools

from .windows import get_windows
from .doors import get_doors
from .rim_joists import get_rim_joists

from ..utils import obj, h2k


# Gets all wall components and possible subcomponents (windows, doors, floor headers)
def get_walls(h2k_dict, model_data={}):
    components = obj.get_val(h2k_dict, "HouseFile,House,Components")

    if "Wall" not in components.keys():
        h2k_walls = []
    else:
        h2k_walls = components["Wall"]

    wall_absorptance = h2k.get_number_field(h2k_dict, "wall_absorptance")

    # Always process as array
    h2k_walls = h2k_walls if isinstance(h2k_walls, list) else [h2k_walls]

    hpxml_walls = []
    hpxml_doors = []
    hpxml_windows_doors = []
    hpxml_windows = []
    hpxml_rim_joists = []

    for wall in h2k_walls:
        model_data.inc_wall_count()
        wall_id = f"Wall{model_data.get_wall_count()}"
        wall_label = wall.get("Label", "No Label")

        # Get required details from h2k wall
        wall_rval = h2k.get_number_field(wall, "wall_r_value")
        if wall_rval <= 0:
            model_data.add_warning_message(
                {
                    "message": f"The wall component {wall_label} has a zero (0) R-value. Please reopen the h2k file in HOT2000, navigate to the affected component, and ensure the correct value is shown before re-saving the file."
                }
            )

        wall_height = h2k.get_number_field(wall, "wall_height")
        wall_perimeter = h2k.get_number_field(wall, "wall_perimeter")
        wall_area = round(wall_height * wall_perimeter, 2)

        res_facility_type = model_data.get_building_detail("res_facility_type")
        attached_unit = (
            "attached" in res_facility_type or "apartment" in res_facility_type
        )

        buffered_attached_type = (
            "other non-freezing space" if attached_unit else "outside"
        )

        wall_exterior = (
            buffered_attached_type
            if wall["@adjacentEnclosedSpace"] == "true"
            else "outside"
        )

        # Build hpxml wall
        new_wall = {
            "SystemIdentifier": {"@id": wall_id},
            "ExteriorAdjacentTo": wall_exterior,
            "InteriorAdjacentTo": "conditioned space",  # always
            "WallType": {"WoodStud": None},  # for now, always WoodStud
            "Area": wall_area,  # [ft2]
            "Siding": "wood siding",  # for now, always wood siding
            "SolarAbsorptance": wall_absorptance,
            "Emittance": "0.9",  # Default
            "InteriorFinish": {
                "Type": "gypsum board"
            },  # for now, always gypsum board, note default thickness is 0.5"
            "Insulation": {
                "SystemIdentifier": {"@id": f"{wall_id}Insulation"},
                "AssemblyEffectiveRValue": round(wall_rval, 2),
            },
            "extension": {"H2kLabel": f"{wall_label}"},
        }

        if wall["@adjacentEnclosedSpace"] == "false":
            # track exposed walls
            model_data.add_wall_segment(
                {
                    "area": wall_area,
                    "height": wall_height,
                    "perimeter": wall_perimeter,
                    "rval": wall_rval,
                }
            )

        hpxml_walls = [*hpxml_walls, new_wall]

        # Handle subcomponents on wall (window, door, floor header/rim joists)
        # Subcomponents not nested with HPXML
        h2k_windows = wall.get("Components", {}).get("Window", {})
        h2k_doors = wall.get("Components", {}).get("Door", {})
        h2k_floor_headers = wall.get("Components", {}).get("FloorHeader", {})

        # Doors
        door_output = get_doors(h2k_doors, "Wall", model_data)
        hpxml_doors = [*hpxml_doors, *door_output["hpxml_doors"]]
        hpxml_windows_doors = [
            *hpxml_windows_doors,
            *door_output["hpxml_windows_doors"],
        ]

        # Windows
        window_output = get_windows(h2k_windows, "Wall", model_data)
        hpxml_windows = [*hpxml_windows, *window_output["hpxml_windows"]]

        # Floor Headers / Rim Joists
        rim_joists_output = get_rim_joists(h2k_floor_headers, "Wall", model_data)
        hpxml_rim_joists = [*hpxml_rim_joists, *rim_joists_output["hpxml_rim_joists"]]

    return {
        "walls": hpxml_walls,
        "windows": [*hpxml_windows, *hpxml_windows_doors],
        "doors": hpxml_doors,
        "rim_joists": hpxml_rim_joists,
    }


def get_attached_walls(h2k_dict, model_data={}, add_test_wall=False):
    foundation_perimeters = [
        fnd for fnd in model_data.get_foundation_details() if fnd["type"] != "expFloor"
    ]

    wall_absorptance = h2k.get_number_field(h2k_dict, "wall_absorptance")

    hpxml_walls = []

    res_facility_type = model_data.get_building_detail("res_facility_type")
    attached_unit = "attached" in res_facility_type or "apartment" in res_facility_type

    # To testing to impact of an adiabatic wall on heat loss
    if add_test_wall:
        attached_unit = True
        foundation_perimeters = [
            {
                "type": "basement",
                "total_perimeter": 100,
                "total_area": 625,
                "exposed_perimeter": 50,
                "exposed_fraction": 0.5,
            }
        ]

    if (len(foundation_perimeters) == 1) and attached_unit:
        foundation_perimeter_dict = foundation_perimeters[0]
        model_data.inc_wall_count()
        wall_id = f"Wall{model_data.get_wall_count()}"

        print("ADDING AN ATTACHED WALL only one foundation (simple approach)")
        wall_segments = model_data.get_wall_segments()

        tot_exp_wall_area = functools.reduce(
            lambda prev, curr: prev + curr["area"], wall_segments, 0
        )

        attached_wall_area = (
            tot_exp_wall_area
            * (1 - foundation_perimeter_dict["exposed_fraction"])
            / foundation_perimeter_dict["exposed_fraction"]
        )

        # weighted average wall height
        avg_wall_height = functools.reduce(
            lambda prev, curr: prev
            + curr["height"] * (curr["area"] / tot_exp_wall_area),
            wall_segments,
            0,
        )

        wall_area_list = [wall["area"] for wall in wall_segments]

        index_max = max(range(len(wall_area_list)), key=wall_area_list.__getitem__)

        wall_common_rval = wall_segments[index_max]["rval"]

        new_attached_wall = {
            "SystemIdentifier": {"@id": wall_id},
            "ExteriorAdjacentTo": "other housing unit",
            "InteriorAdjacentTo": "conditioned space",  # always
            "WallType": {"WoodStud": None},  # for now, always WoodStud
            "Area": attached_wall_area,  # [ft2]
            "Siding": "wood siding",  # for now, always wood siding
            "SolarAbsorptance": wall_absorptance,
            "Emittance": "0.9",  # Default
            "InteriorFinish": {
                "Type": "gypsum board"
            },  # for now, always gypsum board, note default thickness is 0.5"
            "Insulation": {
                "SystemIdentifier": {"@id": f"{wall_id}Insulation"},
                "AssemblyEffectiveRValue": round(wall_common_rval, 2),
            },
            "extension": {"H2kLabel": "No H2k Component - Attached Wall"},
        }

        hpxml_walls = [*hpxml_walls, new_attached_wall]

    elif (len(foundation_perimeters) >= 2) and attached_unit:
        model_data.add_warning_message(
            {
                "message": "The .h2k file indicates an attached home, but not enough information is provided to determine the attached perimeter. Attached wall lengths have been assumed based on typical characteristics of homes from the HTAP archetype database."
            }
        )

        tot_fnd_floor_area = functools.reduce(
            lambda prev, curr: prev + curr["total_area"], foundation_perimeters, 0
        )
        tot_exp_fnd_perimeter = functools.reduce(
            lambda prev, curr: prev + curr["exposed_perimeter"],
            foundation_perimeters,
            0,
        )

        # Need to make an assumption about the exterior perimeter of the foundation
        # The fraction 0.480839 comes from median foundation perimeter/area from the HTAP archetypes
        assumed_total_ext_perimeter = 0.480839 * tot_fnd_floor_area

        attached_perimeter = assumed_total_ext_perimeter - tot_exp_fnd_perimeter

        if attached_perimeter <= 0:
            # Assumption doesn't hold, exit
            print("ASSUMED ATTACHED PERIMETER FOR MULTI-FOUNDATION <= 0")
            return {
                "walls": hpxml_walls,
            }

        # Only here are we committed to creating a new wall component
        model_data.inc_wall_count()
        wall_id = f"Wall{model_data.get_wall_count()}"

        print(
            "ADDING AN ATTACHED WALL multi-foundation (geometry assumptions required)"
        )

        wall_segments = model_data.get_wall_segments()

        tot_exp_wall_area = functools.reduce(
            lambda prev, curr: prev + curr["area"], wall_segments, 0
        )

        exposed_fraction = tot_exp_fnd_perimeter / assumed_total_ext_perimeter

        attached_wall_area = (
            tot_exp_wall_area * (1 - exposed_fraction) / exposed_fraction
        )

        wall_area_list = [wall["area"] for wall in wall_segments]

        index_max = max(range(len(wall_area_list)), key=wall_area_list.__getitem__)

        wall_common_rval = wall_segments[index_max]["rval"]

        new_attached_wall = {
            "SystemIdentifier": {"@id": wall_id},
            "ExteriorAdjacentTo": "other housing unit",
            "InteriorAdjacentTo": "conditioned space",  # always
            "WallType": {"WoodStud": None},  # for now, always WoodStud
            "Area": attached_wall_area,  # [ft2]
            "Siding": "wood siding",  # for now, always wood siding
            "SolarAbsorptance": wall_absorptance,
            "Emittance": "0.9",  # Default
            "InteriorFinish": {
                "Type": "gypsum board"
            },  # for now, always gypsum board, note default thickness is 0.5"
            "Insulation": {
                "SystemIdentifier": {"@id": f"{wall_id}Insulation"},
                "AssemblyEffectiveRValue": round(wall_common_rval, 2),
            },
            "extension": {"H2kLabel": "No H2k Component - Attached Wall"},
        }

        hpxml_walls = [*hpxml_walls, new_attached_wall]

    return {
        "walls": hpxml_walls,
    }
