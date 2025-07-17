import math

from .windows import get_windows
from .doors import get_doors
from .rim_joists import get_rim_joists

from ..utils import obj, h2k


# Gets all crawlspace components and possible subcomponents (windows, doors, floor headers)
def get_crawlspaces(h2k_dict, model_data={}):
    components = obj.get_val(h2k_dict, "HouseFile,House,Components")

    if "Crawlspace" not in components.keys():
        h2k_crawlspaces = []
    else:
        h2k_crawlspaces = components["Crawlspace"]

    wall_absorptance = h2k.get_number_field(h2k_dict, "wall_absorptance")
    is_crawlspace_heated = h2k.get_selection_field(h2k_dict, "crawlspace_heated")

    # Always process as array
    h2k_crawlspaces = (
        h2k_crawlspaces if isinstance(h2k_crawlspaces, list) else [h2k_crawlspaces]
    )

    hpxml_foundations = []
    hpxml_foundation_walls = []
    hpxml_slabs = []
    hpxml_floors = []

    hpxml_doors = []
    hpxml_windows_doors = []
    hpxml_windows = []
    hpxml_rim_joists = []

    # Open crawlspace is essentially an exposed floor
    # Closed and vented are the same in h2k except for the assumed air change rates
    for crawlspace in h2k_crawlspaces:
        model_data.inc_foundation_count()
        model_data.inc_floor_count()

        crawlspace_label = crawlspace.get("Label", "No Label")
        crawlspace_venting = h2k.get_selection_field(crawlspace, "crawlspace_vented")
        is_open_crawlspace = crawlspace_venting == "outside"
        is_crawlspace_vented = crawlspace_venting == "crawlspace - vented"

        if not is_open_crawlspace:
            model_data.inc_foundation_wall_count()
            model_data.inc_slab_count()
        else:
            model_data.add_warning_message(
                {
                    "message": "The model contains an open crawlspace, which does not have a direct HPXML equivalent"
                }
            )

        foundation_id = f"Foundation{model_data.get_foundation_count()}"
        foundation_wall_id = f"FoundationWall{model_data.get_foundation_wall_count()}"
        slab_id = f"Slab{model_data.get_slab_count()}"
        floor_id = f"Floor{model_data.get_floor_count()}"

        # Using "crawlspace - conditioned" for vented and unvented matches h2k assumptions
        interior_adjacent = (
            "outside" if is_open_crawlspace else "crawlspace - conditioned"
        )

        model_data.set_building_details(
            {
                "crawlspace_location": interior_adjacent,
            }
        )

        # Get required details from h2k crawlspace
        is_crawlspace_rectangular = h2k.get_selection_field(
            crawlspace, "foundation_rectangular"
        )
        crawlspace_floor_area = h2k.get_number_field(
            crawlspace, "foundation_floor_area"
        )
        crawlspace_perimeter = h2k.get_number_field(crawlspace, "foundation_perimeter")
        crawlspace_exp_perimeter = h2k.get_number_field(
            crawlspace, "foundation_exp_perimeter"
        )
        crawlspace_width = h2k.get_number_field(crawlspace, "foundation_width")
        crawlspace_length = h2k.get_number_field(crawlspace, "foundation_length")
        crawlspace_height = h2k.get_number_field(crawlspace, "foundation_height")
        crawlspace_depth = h2k.get_number_field(crawlspace, "foundation_depth")

        foundation_tot_perimeter = (
            2 * (crawlspace_width + crawlspace_length)
            if is_crawlspace_rectangular
            else crawlspace_perimeter
        )

        foundation_tot_area = (
            crawlspace_width * crawlspace_length
            if is_crawlspace_rectangular
            else crawlspace_floor_area
        )

        foundation_wall_exp_area = crawlspace_exp_perimeter * crawlspace_height
        if crawlspace_exp_perimeter == 0:
            foundation_wall_exp_area = foundation_tot_perimeter * crawlspace_height

        model_data.add_foundation_detail(
            {
                "type": "crawlspace",
                "total_perimeter": foundation_tot_perimeter,
                "total_area": 0 if is_open_crawlspace else foundation_tot_area,
                "exposed_perimeter": crawlspace_exp_perimeter,
                "exposed_fraction": crawlspace_exp_perimeter / foundation_tot_perimeter,
            }
        )

        slab_config = obj.get_val(crawlspace, "Configuration,#text")
        wall_core = "C"  # This value is only used to prevent dvide by zero errors
        slab_ins = slab_config[2]  # "N" None, "A" Above, "B" Below

        wall_construction = obj.get_val(crawlspace, "Wall,Construction")

        if is_open_crawlspace:
            crwl_wall_rval = 0
        else:
            crwl_wall_composite = wall_construction["Type"]
            crwl_wall_rval = h2k.get_composite_rval(crwl_wall_composite, wall_core)

        floors_above_rval = h2k.get_number_field(
            crawlspace, "floors_above_foundation_rval"
        )

        slab_r_val = 0  # nominal R-value, so not including concrete
        insulation_spans_slab = True
        slab_ins_width = round(
            math.sqrt(foundation_tot_area) / 2, 2
        )  # default to "full"

        slab_skirt_ins_depth = 0
        slab_skirt_rval = 0

        if slab_ins != "N":
            # Dealing with either above or below slab insulation
            slab_r_val = h2k.get_number_field(crawlspace, "slab_r_value")
            # get perimeter if applicable
            perimeter_slab_ins = h2k.get_foundation_config("perimeter_slab_ins")
            if slab_config in perimeter_slab_ins.keys():
                insulation_spans_slab = False
                slab_ins_width = perimeter_slab_ins.get(slab_config, slab_ins_width)

            # check for skirt insulation
            slab_skirt_ins = h2k.get_foundation_config("slab_skirt_ins")
            if slab_config in slab_skirt_ins:
                slab_skirt_ins_depth = 1.9685  # always 60cm
                slab_skirt_rval = h2k.get_number_field(crawlspace, "slab_skirt_r_value")

        # files show attached to rim joist info, but might be able to exclude this (how to handle multiple floor headers?)
        new_foundation = {
            "SystemIdentifier": {"@id": foundation_id},
            "FoundationType": {
                "Crawlspace": {
                    "Vented": is_crawlspace_vented,
                    "Conditioned": is_crawlspace_heated,
                }
            },
            # "AttachedToRimJoist": {"@idref": "Temp"},
            **(
                {"AttachedToFoundationWall": {"@idref": foundation_wall_id}}
                if not is_open_crawlspace
                else {}
            ),
            "AttachedToFloor": {"@idref": floor_id},
            **(
                {"AttachedToSlab": {"@idref": slab_id}}
                if not is_open_crawlspace
                else {}
            ),
            "extension": {"H2kLabel": f"{crawlspace_label}"},
        }

        # Build hpxml foundation wall
        new_foundation_wall = (
            {
                "SystemIdentifier": {"@id": foundation_wall_id},
                "ExteriorAdjacentTo": "ground",  # only applicable option, even for mostly above grade walls
                "InteriorAdjacentTo": interior_adjacent,
                "Height": crawlspace_height,
                "Area": foundation_wall_exp_area,
                "Thickness": "8.0",  # default
                "DepthBelowGrade": crawlspace_depth,
                "InteriorFinish": {"Type": "gypsum board"},  # default
                "Insulation": {
                    "SystemIdentifier": {"@id": f"{foundation_wall_id}Insulation"},
                    "AssemblyEffectiveRValue": round(crwl_wall_rval, 2),
                    # "Layer": [
                    #     {
                    #         "InstallationType": "continuous - exterior",
                    #         "NominalRValue": "8.9",
                    #         "DistanceToTopOfInsulation": "0.0",
                    #         "DistanceToBottomOfInsulation": "8.0",
                    #     },
                    #     {
                    #         "InstallationType": "continuous - interior",
                    #         "NominalRValue": "0.0",
                    #     },
                    # ],
                },
                "extension": {"H2kLabel": f"{crawlspace_label}"},
            }
            if not is_open_crawlspace
            else {}
        )

        # Basement Slab
        new_slab = (
            {
                "SystemIdentifier": {"@id": slab_id},
                "InteriorAdjacentTo": interior_adjacent,
                "Area": foundation_tot_area,
                "Thickness": "4.0",  # Default
                "ExposedPerimeter": (
                    foundation_tot_perimeter
                    if crawlspace_exp_perimeter == 0
                    else crawlspace_exp_perimeter
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
                    "H2kLabel": f"{crawlspace_label}",
                },  # defaults to >0 if not provided
            }
            if not is_open_crawlspace
            else {}
        )

        # Floor above crawlspace
        new_floor = {
            "SystemIdentifier": {"@id": floor_id},
            "ExteriorAdjacentTo": interior_adjacent,  # interior relative to crawlspace walls
            "InteriorAdjacentTo": "conditioned space",  # the home
            "FloorOrCeiling": "floor",
            "FloorType": {"WoodFrame": None},  # for now, always WoodStud
            "Area": foundation_tot_area,  # [ft2]
            "InteriorFinish": {"Type": "none"},  # default for non-ceiling floors
            "Insulation": {
                "SystemIdentifier": {"@id": f"{floor_id}Insulation"},
                "AssemblyEffectiveRValue": round(floors_above_rval, 2),
            },
            "extension": {"H2kLabel": f"{crawlspace_label}"},
        }

        hpxml_floors = [*hpxml_floors, new_floor]
        if not is_open_crawlspace:
            hpxml_foundations = [*hpxml_foundations, new_foundation]
            hpxml_foundation_walls = [*hpxml_foundation_walls, new_foundation_wall]
            hpxml_slabs = [*hpxml_slabs, new_slab]

        # Handle subcomponents on wall (window, door, floor header/rim joists)
        # Subcomponents not nested with HPXML
        h2k_windows = crawlspace.get("Components", {}).get("Window", {})
        h2k_doors = crawlspace.get("Components", {}).get("Door", {})
        h2k_floor_headers = crawlspace.get("Components", {}).get("FloorHeader", {})

        # Doors
        door_output = get_doors(h2k_doors, "FoundationWall", model_data)
        hpxml_doors = [*hpxml_doors, *door_output["hpxml_doors"]]
        hpxml_windows_doors = [
            *hpxml_windows_doors,
            *door_output["hpxml_windows_doors"],
        ]

        # Windows
        window_output = get_windows(h2k_windows, "FoundationWall", model_data)
        hpxml_windows = [*hpxml_windows, *window_output["hpxml_windows"]]

        # Floor Headers / Rim Joists
        rim_joists_output = get_rim_joists(
            h2k_floor_headers, "FoundationWall", model_data
        )
        hpxml_rim_joists = [*hpxml_rim_joists, *rim_joists_output["hpxml_rim_joists"]]

    return {
        "windows": [*hpxml_windows, *hpxml_windows_doors],
        "doors": hpxml_doors,
        "rim_joists": hpxml_rim_joists,
        "foundations": hpxml_foundations,
        "foundation_walls": hpxml_foundation_walls,
        "slabs": hpxml_slabs,
        "floors": hpxml_floors,
    }
