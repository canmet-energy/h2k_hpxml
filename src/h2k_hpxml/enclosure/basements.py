import math

from .windows import get_windows
from .doors import get_doors
from .rim_joists import get_rim_joists

from ..utils import obj, h2k


# Gets all basement components and possible subcomponents (windows, doors, floor headers)
def get_basements(h2k_dict, model_data={}):
    components = obj.get_val(h2k_dict, "HouseFile,House,Components")

    if "Basement" not in components.keys():
        h2k_basements = []
    else:
        h2k_basements = components["Basement"]

    wall_absorptance = h2k.get_number_field(h2k_dict, "wall_absorptance")
    is_basement_heated = h2k.get_selection_field(h2k_dict, "basement_heated")

    # Always process as array
    h2k_basements = (
        h2k_basements if isinstance(h2k_basements, list) else [h2k_basements]
    )

    hpxml_foundations = []
    hpxml_foundation_walls = []
    hpxml_slabs = []
    hpxml_floors = []

    hpxml_pony_walls = []

    hpxml_doors = []
    hpxml_windows_doors = []
    hpxml_windows = []
    hpxml_rim_joists = []

    for basement in h2k_basements:
        model_data.inc_foundation_count()
        model_data.inc_foundation_wall_count()
        model_data.inc_slab_count()
        # model_data.inc_floor_count()

        basement_label = basement.get("Label", "No Label")

        foundation_id = f"Foundation{model_data.get_foundation_count()}"
        foundation_wall_id = f"FoundationWall{model_data.get_foundation_wall_count()}"
        slab_id = f"Slab{model_data.get_slab_count()}"
        # floor_id = f"Floor{model_data.get_floor_count()}"

        # Get required details from h2k basement
        is_basement_rectangular = h2k.get_selection_field(
            basement, "foundation_rectangular"
        )
        basement_floor_area = h2k.get_number_field(basement, "foundation_floor_area")
        basement_perimeter = h2k.get_number_field(basement, "foundation_perimeter")
        basement_exp_perimeter = h2k.get_number_field(
            basement, "foundation_exp_perimeter"
        )
        basement_width = h2k.get_number_field(basement, "foundation_width")
        basement_length = h2k.get_number_field(basement, "foundation_length")
        basement_height = h2k.get_number_field(basement, "foundation_height")
        basement_depth = h2k.get_number_field(basement, "foundation_depth")

        pony_wall_height = h2k.get_number_field(basement, "pony_wall_height")

        foundation_tot_perimeter = (
            2 * (basement_width + basement_length)
            if is_basement_rectangular
            else basement_perimeter
        )

        foundation_tot_area = (
            basement_width * basement_length
            if is_basement_rectangular
            else basement_floor_area
        )

        foundation_wall_exp_area = basement_exp_perimeter * basement_height
        if basement_exp_perimeter == 0:
            foundation_wall_exp_area = foundation_tot_perimeter * basement_height

        model_data.add_foundation_detail(
            {
                "type": "basement",
                "total_perimeter": foundation_tot_perimeter,
                "total_area": foundation_tot_area,
                "exposed_perimeter": basement_exp_perimeter,
                "exposed_fraction": basement_exp_perimeter / foundation_tot_perimeter,
            }
        )

        basement_config = obj.get_val(basement, "Configuration,#text")
        wall_core = basement_config[1]  # C (concrete), W (wood)
        slab_ins = basement_config[3]  # "N" None, "A" Above, "B" Below

        # Concrete or wood wall + interior air film
        basement_wall_rval = 0.116 * 5.678 if wall_core == "C" else 0.417 * 5.678
        # basement_wall_rval += 0.12 * 5.678 #Air film

        pony_wall_rval = 0  # (0.12 + 0.03) * 5.678 #Air films

        wall_construction = obj.get_val(basement, "Wall,Construction")
        has_pony_wall = obj.get_val(basement, "Wall,@hasPonyWall") == "true"

        if "InteriorAddedInsulation" in wall_construction.keys():
            int_wall_composite = wall_construction["InteriorAddedInsulation"]
            int_wall_rval = h2k.get_composite_rval(int_wall_composite, wall_core)
            basement_wall_rval += int_wall_rval

        if "ExteriorAddedInsulation" in wall_construction.keys():
            ext_wall_composite = wall_construction["ExteriorAddedInsulation"]
            ext_wall_rval = h2k.get_composite_rval(ext_wall_composite, wall_core)
            basement_wall_rval += ext_wall_rval

        if ("PonyWallType" in wall_construction.keys()) & (has_pony_wall):
            # Note we'll assume a wood core for pony walls
            pony_wall_composite = wall_construction["PonyWallType"]
            pony_wall_rval = h2k.get_composite_rval(pony_wall_composite, "W")

        floors_above_rval = h2k.get_number_field(
            basement, "floors_above_foundation_rval"
        )

        slab_r_val = 0  # nominal R-value, so not including concrete
        insulation_spans_slab = True
        slab_ins_width = round(math.sqrt(foundation_tot_area) / 2, 2)
        if slab_ins != "N":
            # Dealing with either above or below slab insulation
            slab_r_val = h2k.get_number_field(basement, "slab_r_value")
            # get perimeter if applicable
            perimeter_basement_ins = h2k.get_foundation_config("perimeter_basement_ins")
            if basement_config in perimeter_basement_ins.keys():
                insulation_spans_slab = False
                slab_ins_width = perimeter_basement_ins.get(
                    basement_config, slab_ins_width
                )

        # files show attached to rim joist info, but might be able to exclude this (how to handle multiple floor headers?)
        new_foundation = {
            "SystemIdentifier": {"@id": foundation_id},
            "FoundationType": {"Basement": {"Conditioned": is_basement_heated}},
            # "AttachedToRimJoist": {"@idref": "Temp"},
            "AttachedToFoundationWall": {"@idref": foundation_wall_id},
            "AttachedToSlab": {"@idref": slab_id},
            "extension": {"H2kLabel": f"{basement_label}"},
        }

        # Build hpxml foundation wall
        new_foundation_wall = {
            "SystemIdentifier": {"@id": foundation_wall_id},
            "ExteriorAdjacentTo": "ground",
            "InteriorAdjacentTo": "basement - conditioned",
            "Height": basement_height,
            "Area": foundation_wall_exp_area,
            "Thickness": "8.0",  # default
            "DepthBelowGrade": basement_depth,
            "InteriorFinish": {"Type": "gypsum board"},  # default
            "Insulation": {
                "SystemIdentifier": {"@id": f"{foundation_wall_id}Insulation"},
                "AssemblyEffectiveRValue": basement_wall_rval,
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
            "extension": {"H2kLabel": f"{basement_label}"},
        }

        # Pony Wall if present
        if has_pony_wall:
            model_data.inc_wall_count()
            pony_wall_id = f"Wall{model_data.get_wall_count()}"

            pony_wall_area = pony_wall_height * basement_exp_perimeter
            new_pony_wall = {
                "SystemIdentifier": {"@id": pony_wall_id},
                "ExteriorAdjacentTo": "outside",
                "InteriorAdjacentTo": "conditioned space",  # always
                "WallType": {"WoodStud": None},  # for now, always WoodStud
                "Area": pony_wall_area,  # [ft2]
                "Siding": "wood siding",  # for now, always wood siding
                "SolarAbsorptance": wall_absorptance,
                "Emittance": "0.9",  # Default
                "InteriorFinish": {
                    "Type": "gypsum board"
                },  # for now, always gypsum board, note default thickness is 0.5"
                "Insulation": {
                    "SystemIdentifier": {"@id": f"{pony_wall_id}Insulation"},
                    "AssemblyEffectiveRValue": pony_wall_rval,
                },
                "extension": {"H2kLabel": f"{basement_label}"},
            }

            hpxml_pony_walls = [*hpxml_pony_walls, new_pony_wall]

        # Basement Slab
        new_slab = {
            "SystemIdentifier": {"@id": slab_id},
            "InteriorAdjacentTo": "basement - conditioned",
            "Area": foundation_tot_area,
            "Thickness": "4.0",  # Default
            "ExposedPerimeter": (
                foundation_tot_perimeter
                if basement_exp_perimeter == 0
                else basement_exp_perimeter
            ),
            "PerimeterInsulation": {
                "SystemIdentifier": {"@id": f"{slab_id}PerimeterInsulation"},
                "Layer": {
                    "NominalRValue": "0.0",
                    "InsulationDepth": "0.0",
                },  # Basements never have this (skirt insulation) in h2k
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
                "H2kLabel": f"{basement_label}",
            },  # defaults to >0 if not provided
        }

        # Floor above basement
        # Removed because this can trigger a geometry error in the HPXML workflow (and is adiabatic anyway)
        # new_floor = {
        #     "SystemIdentifier": {"@id": floor_id},
        #     "ExteriorAdjacentTo": "basement - conditioned",
        #     "InteriorAdjacentTo": "conditioned space",  # the home
        #     "FloorType": {"WoodFrame": None},  # for now, always WoodStud
        #     # "FloorOrCeiling": "floor",
        #     "Area": foundation_tot_area,  # [ft2]
        #     "InteriorFinish": {"Type": "none"},  # default for non-ceiling floors
        #     "Insulation": {
        #         "SystemIdentifier": {"@id": f"{floor_id}Insulation"},
        #         "AssemblyEffectiveRValue": floors_above_rval,
        #     },
        # }

        hpxml_foundations = [*hpxml_foundations, new_foundation]
        hpxml_foundation_walls = [*hpxml_foundation_walls, new_foundation_wall]
        hpxml_slabs = [*hpxml_slabs, new_slab]
        # hpxml_floors = [*hpxml_floors, new_floor]

        # Handle subcomponents on wall (window, door, floor header/rim joists)
        # Subcomponents not nested with HPXML
        h2k_windows = basement.get("Components", {}).get("Window", {})
        h2k_doors = basement.get("Components", {}).get("Door", {})
        h2k_floor_headers = basement.get("Components", {}).get("FloorHeader", {})

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
        "pony_walls": hpxml_pony_walls,
        "floors": hpxml_floors,
    }
