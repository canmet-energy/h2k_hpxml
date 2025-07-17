import math

from .skylights import get_skylights

from ..utils import obj, h2k


# Gets all wall components and possible subcomponents (windows, doors, floor headers)
def get_ceilings(h2k_dict, model_data={}):
    components = obj.get_val(h2k_dict, "HouseFile,House,Components")

    roof_cavity_inputs = (
        h2k_dict.get("HouseFile", {})
        .get("House", {})
        .get("Specifications", {})
        .get("RoofCavity", {})
    )

    has_roof_cavity_inputs = roof_cavity_inputs != {}

    if "Ceiling" not in components.keys():
        h2k_ceilings = []
    else:
        h2k_ceilings = components["Ceiling"]

    roof_absorptance = h2k.get_number_field(h2k_dict, "roof_absorptance")
    wall_absorptance = h2k.get_number_field(h2k_dict, "wall_absorptance")
    roof_material = h2k.get_selection_field(h2k_dict, "roof_material")

    # Always process as array
    h2k_ceilings = h2k_ceilings if isinstance(h2k_ceilings, list) else [h2k_ceilings]

    hpxml_attics = []
    hpxml_roofs = []
    hpxml_walls = []
    hpxml_floors = []
    hpxml_skylights = []

    for ceiling in h2k_ceilings:
        construction_type = obj.get_val(ceiling, "Construction,Type,English")
        ceiling_label = ceiling.get("Label", "No Label")

        skylight_attachment = {}

        if construction_type.lower() == "attic/gable":
            # attic/gable => Floor (ceiling), 2x gable end walls, roof, attic (AtticType = Attic)
            model_data.inc_wall_count()
            model_data.inc_floor_count()
            model_data.inc_roof_count()
            model_data.inc_attic_count()

            wall_id = f"Wall{model_data.get_wall_count()}"
            floor_id = f"Floor{model_data.get_floor_count()}"
            roof_id = f"Roof{model_data.get_roof_count()}"
            attic_id = f"Attic{model_data.get_attic_count()}"

            # Geometry
            roof_pitch = h2k.get_selection_field(ceiling, "roof_pitch")
            if roof_pitch == None:
                roof_pitch = int(
                    round(12 * h2k.get_number_field(ceiling, "roof_pitch_value"))
                )

            ceiling_area = h2k.get_number_field(ceiling, "ceiling_area")
            ceiling_length = h2k.get_number_field(
                ceiling, "ceiling_length"
            )  # total compressed length, 2 sides for this ceiling type

            roof_angle = math.atan(roof_pitch / 12)
            roof_area = ceiling_area / math.cos(roof_angle)

            gable_wall_width = ceiling_area / (
                ceiling_length / 2
            )  # divide length by 2, since the input captures both compressed sides of home

            roof_height = (gable_wall_width / 2) * (
                roof_pitch / 12
            )  # half gable wall length is x, height is y in the pitch equation

            # For this ceiling type, we assume there are two gable ends without additional information
            tot_gable_wall_area = (
                2 * (1 / 2) * gable_wall_width * roof_height
            )  # 2x the triangle with base = gable_wall_width, height = roof_height

            # Rvalues
            ceiling_rval = h2k.get_number_field(ceiling, "ceiling_r_value")
            gable_wall_rval = 5.678 * (0.083 + 0.11)  # default in h2k
            roof_rval = 5.678 * (0.111 + 0.078)  # default in h2k
            if has_roof_cavity_inputs:
                sloped_roof_sheathing_r_value = h2k.get_number_field(
                    roof_cavity_inputs, "sloped_roof_sheathing_r_value"
                )
                sloped_roof_material_r_value = h2k.get_number_field(
                    roof_cavity_inputs, "sloped_roof_material_r_value"
                )
                gable_ends_sheathing_r_value = h2k.get_number_field(
                    roof_cavity_inputs, "gable_ends_sheathing_r_value"
                )
                gable_ends_exterior_r_value = h2k.get_number_field(
                    roof_cavity_inputs, "gable_ends_exterior_r_value"
                )

                gable_wall_rval = (
                    gable_ends_sheathing_r_value + gable_ends_exterior_r_value
                )
                roof_rval = sloped_roof_sheathing_r_value + sloped_roof_material_r_value

            # Horizontal ceiling surface, modelled as a Floor in HPXML
            new_floor = {
                "SystemIdentifier": {"@id": floor_id},
                "ExteriorAdjacentTo": "attic - vented",  # always for this type of floor as a ceiling
                "InteriorAdjacentTo": "conditioned space",  # always
                "FloorOrCeiling": "ceiling",
                "FloorType": {"WoodFrame": None},  # for now, always WoodFrame
                "Area": ceiling_area,  # [ft2]
                "InteriorFinish": {
                    "Type": "gypsum board"
                },  # default for ceiling floors
                "Insulation": {
                    "SystemIdentifier": {"@id": f"{floor_id}Insulation"},
                    "AssemblyEffectiveRValue": round(
                        ceiling_rval, 2
                    ),  # Ceiling r-value applied here
                },
                "extension": {"H2kLabel": f"{ceiling_label}"},
            }

            new_wall = {
                "SystemIdentifier": {"@id": wall_id},
                "ExteriorAdjacentTo": "outside",
                "InteriorAdjacentTo": "attic - vented",  # always
                "AtticWallType": "gable",
                "WallType": {"WoodStud": None},  # for now, always WoodStud
                "Area": tot_gable_wall_area,  # [ft2]
                "Siding": "wood siding",  # for now, always wood siding
                "SolarAbsorptance": wall_absorptance,
                "Emittance": "0.9",  # Default
                "Insulation": {
                    "SystemIdentifier": {"@id": f"{wall_id}Insulation"},
                    "AssemblyEffectiveRValue": round(gable_wall_rval, 2),
                },
                "extension": {"H2kLabel": f"{ceiling_label}"},
            }

            new_roof = {
                "SystemIdentifier": {"@id": roof_id},
                "InteriorAdjacentTo": "attic - vented",  # always
                "Area": roof_area,
                "RoofType": roof_material,
                "SolarAbsorptance": roof_absorptance,
                "Emittance": "0.9",  # Default in HPXML
                "Pitch": roof_pitch,
                "RadiantBarrier": "false",  # Default
                "Insulation": {
                    "SystemIdentifier": {"@id": f"{roof_id}Insulation"},
                    "AssemblyEffectiveRValue": round(roof_rval, 2),
                },
                "extension": {"H2kLabel": f"{ceiling_label}"},
            }

            new_attic = {
                "SystemIdentifier": {"@id": attic_id},
                "AtticType": {
                    "Attic": {"Vented": "true"},
                },
                # "WithinInfiltrationVolume": "false",
                "VentilationRate": {"UnitofMeasure": "ACHnatural", "Value": 2.4},
                "AttachedToRoof": {"@idref": roof_id},
                "AttachedToWall": {"@idref": wall_id},
                "AttachedToFloor": {"@idref": floor_id},
                "extension": {"H2kLabel": f"{ceiling_label}"},
            }

            skylight_attachment = {
                "AttachedToRoof": {"@idref": roof_id},
                "AttachedToFloor": {"@idref": floor_id},
            }

            hpxml_attics = [*hpxml_attics, new_attic]
            hpxml_roofs = [*hpxml_roofs, new_roof]
            hpxml_walls = [*hpxml_walls, new_wall]
            hpxml_floors = [*hpxml_floors, new_floor]

        elif construction_type.lower() == "attic/hip":
            # attic/hip => Floor (ceiling), roof, attic
            model_data.inc_floor_count()
            model_data.inc_roof_count()
            model_data.inc_attic_count()

            floor_id = f"Floor{model_data.get_floor_count()}"
            roof_id = f"Roof{model_data.get_roof_count()}"
            attic_id = f"Attic{model_data.get_attic_count()}"

            # Geometry
            roof_pitch = h2k.get_selection_field(ceiling, "roof_pitch")
            if roof_pitch == None:
                roof_pitch = int(
                    round(12 * h2k.get_number_field(ceiling, "roof_pitch_value"))
                )

            ceiling_area = h2k.get_number_field(ceiling, "ceiling_area")
            ceiling_length = h2k.get_number_field(
                ceiling, "ceiling_length"
            )  # total compressed length, assumed to be total perimeter for this ceiling type

            perimeter_min = 4 * math.sqrt(ceiling_area)

            length = 0
            width = 0

            if ceiling_length < perimeter_min:
                # Can't enclose ceiling area in given (assumed) perimeter, use length:width ratio from h2k defaults
                width = ceiling_area * (10 / (1.58**2))
                length = ceiling_area / width
            else:
                width = (
                    ceiling_length + math.sqrt(ceiling_length**2 - (8 * ceiling_area))
                ) / 4
                length = ceiling_area / width

            roof_width = min(width, length)
            roof_length = max(width, length)

            roof_angle = math.atan(roof_pitch / 12)

            roof_ridge_length = roof_length - roof_width
            roof_slope_length = (roof_width / 2) / math.cos(roof_angle)
            roof_height = (roof_pitch / 12) * roof_width / 2

            roof_area = (
                roof_slope_length * roof_width
                + (roof_length + roof_ridge_length) * roof_slope_length
            )

            # Rvalues
            ceiling_rval = h2k.get_number_field(ceiling, "ceiling_r_value")
            roof_rval = 5.678 * (0.111 + 0.078)  # default in h2k
            if has_roof_cavity_inputs:
                sloped_roof_sheathing_r_value = h2k.get_number_field(
                    roof_cavity_inputs, "sloped_roof_sheathing_r_value"
                )
                sloped_roof_material_r_value = h2k.get_number_field(
                    roof_cavity_inputs, "sloped_roof_material_r_value"
                )
                gable_ends_sheathing_r_value = h2k.get_number_field(
                    roof_cavity_inputs, "gable_ends_sheathing_r_value"
                )
                gable_ends_exterior_r_value = h2k.get_number_field(
                    roof_cavity_inputs, "gable_ends_exterior_r_value"
                )

                gable_wall_rval = (
                    gable_ends_sheathing_r_value + gable_ends_exterior_r_value
                )
                roof_rval = sloped_roof_sheathing_r_value + sloped_roof_material_r_value

            # Horizontal ceiling surface, modelled as a Floor in HPXML
            new_floor = {
                "SystemIdentifier": {"@id": floor_id},
                "ExteriorAdjacentTo": "attic - vented",  # always for this type of floor as a ceiling
                "InteriorAdjacentTo": "conditioned space",  # always
                "FloorOrCeiling": "ceiling",
                "FloorType": {"WoodFrame": None},  # for now, always WoodFrame
                "Area": ceiling_area,  # [ft2]
                "InteriorFinish": {
                    "Type": "gypsum board"
                },  # default for ceiling floors
                "Insulation": {
                    "SystemIdentifier": {"@id": f"{floor_id}Insulation"},
                    "AssemblyEffectiveRValue": round(
                        ceiling_rval, 2
                    ),  # Ceiling r-value applied here
                },
                "extension": {"H2kLabel": f"{ceiling_label}"},
            }

            new_roof = {
                "SystemIdentifier": {"@id": roof_id},
                "InteriorAdjacentTo": "attic - vented",  # always
                "Area": roof_area,
                "RoofType": roof_material,
                "SolarAbsorptance": roof_absorptance,
                "Emittance": "0.9",  # Default in HPXML
                "Pitch": roof_pitch,
                "RadiantBarrier": "false",  # Default
                "Insulation": {
                    "SystemIdentifier": {"@id": f"{roof_id}Insulation"},
                    "AssemblyEffectiveRValue": round(roof_rval, 2),
                },
                "extension": {"H2kLabel": f"{ceiling_label}"},
            }

            new_attic = {
                "SystemIdentifier": {"@id": attic_id},
                "AtticType": {
                    "Attic": {"Vented": "true"},
                },
                # "WithinInfiltrationVolume": "false",
                "VentilationRate": {"UnitofMeasure": "ACHnatural", "Value": 2.4},
                "AttachedToRoof": {"@idref": roof_id},
                "AttachedToFloor": {"@idref": floor_id},
                "extension": {"H2kLabel": f"{ceiling_label}"},
            }

            skylight_attachment = {
                "AttachedToRoof": {"@idref": roof_id},
                "AttachedToFloor": {"@idref": floor_id},
            }

            hpxml_attics = [*hpxml_attics, new_attic]
            hpxml_roofs = [*hpxml_roofs, new_roof]
            hpxml_floors = [*hpxml_floors, new_floor]
        elif construction_type.lower() == "cathedral":
            # cathedral => Attic (AtticType = Cathedral Ceiling), roof
            # R-values must be applied to roof
            model_data.inc_roof_count()
            model_data.inc_attic_count()

            roof_id = f"Roof{model_data.get_roof_count()}"
            attic_id = f"Attic{model_data.get_attic_count()}"

            # Geometry
            roof_pitch = h2k.get_selection_field(ceiling, "roof_pitch")
            if roof_pitch == None:
                roof_pitch = int(
                    round(12 * h2k.get_number_field(ceiling, "roof_pitch_value"))
                )

            ceiling_area = h2k.get_number_field(ceiling, "ceiling_area")

            # Rvalues
            ceiling_rval = h2k.get_number_field(ceiling, "ceiling_r_value")
            roof_rval = 5.678 * (0.111 + 0.078)  # default in h2k
            if has_roof_cavity_inputs:
                sloped_roof_sheathing_r_value = h2k.get_number_field(
                    roof_cavity_inputs, "sloped_roof_sheathing_r_value"
                )
                sloped_roof_material_r_value = h2k.get_number_field(
                    roof_cavity_inputs, "sloped_roof_material_r_value"
                )
                gable_ends_sheathing_r_value = h2k.get_number_field(
                    roof_cavity_inputs, "gable_ends_sheathing_r_value"
                )
                gable_ends_exterior_r_value = h2k.get_number_field(
                    roof_cavity_inputs, "gable_ends_exterior_r_value"
                )

                gable_wall_rval = (
                    gable_ends_sheathing_r_value + gable_ends_exterior_r_value
                )
                roof_rval = sloped_roof_sheathing_r_value + sloped_roof_material_r_value

            # Insulation here, because we have no "floor"
            new_roof = {
                "SystemIdentifier": {"@id": roof_id},
                "InteriorAdjacentTo": "conditioned space",  # always
                "Area": ceiling_area,
                "RoofType": roof_material,
                "SolarAbsorptance": roof_absorptance,
                "Emittance": "0.9",  # Default in HPXML
                "InteriorFinish": {"Type": "gypsum board"},
                "Pitch": roof_pitch,
                "RadiantBarrier": "false",  # Default
                "Insulation": {
                    "SystemIdentifier": {"@id": f"{roof_id}Insulation"},
                    "AssemblyEffectiveRValue": round(ceiling_rval + roof_rval, 2),
                },
                "extension": {"H2kLabel": f"{ceiling_label}"},
            }

            new_attic = {
                "SystemIdentifier": {"@id": attic_id},
                "AtticType": {
                    "CathedralCeiling": None,
                },
                "AttachedToRoof": {"@idref": roof_id},
                "extension": {"H2kLabel": f"{ceiling_label}"},
            }

            skylight_attachment = {
                "AttachedToRoof": {"@idref": roof_id},
            }

            hpxml_attics = [*hpxml_attics, new_attic]
            hpxml_roofs = [*hpxml_roofs, new_roof]

        elif construction_type.lower() == "flat":
            # flat => Attic (AtticType = FlatRoof), roof
            # R-values must be applied to roof
            model_data.inc_roof_count()
            model_data.inc_attic_count()

            roof_id = f"Roof{model_data.get_roof_count()}"
            attic_id = f"Attic{model_data.get_attic_count()}"

            # Geometry
            roof_pitch = 0

            ceiling_area = h2k.get_number_field(ceiling, "ceiling_area")

            # Rvalues
            ceiling_rval = h2k.get_number_field(ceiling, "ceiling_r_value")
            roof_rval = 5.678 * (0.111 + 0.078)  # default in h2k
            if has_roof_cavity_inputs:
                sloped_roof_sheathing_r_value = h2k.get_number_field(
                    roof_cavity_inputs, "sloped_roof_sheathing_r_value"
                )
                sloped_roof_material_r_value = h2k.get_number_field(
                    roof_cavity_inputs, "sloped_roof_material_r_value"
                )
                gable_ends_sheathing_r_value = h2k.get_number_field(
                    roof_cavity_inputs, "gable_ends_sheathing_r_value"
                )
                gable_ends_exterior_r_value = h2k.get_number_field(
                    roof_cavity_inputs, "gable_ends_exterior_r_value"
                )

                gable_wall_rval = (
                    gable_ends_sheathing_r_value + gable_ends_exterior_r_value
                )
                roof_rval = sloped_roof_sheathing_r_value + sloped_roof_material_r_value

            # Insulation here, because we have no "floor"
            new_roof = {
                "SystemIdentifier": {"@id": roof_id},
                "InteriorAdjacentTo": "conditioned space",  # always
                "Area": ceiling_area,
                "RoofType": roof_material,
                "SolarAbsorptance": roof_absorptance,
                "Emittance": "0.9",  # Default in HPXML
                "InteriorFinish": {"Type": "gypsum board"},
                "Pitch": roof_pitch,
                "RadiantBarrier": "false",  # Default
                "Insulation": {
                    "SystemIdentifier": {"@id": f"{roof_id}Insulation"},
                    "AssemblyEffectiveRValue": round(ceiling_rval + roof_rval, 2),
                },
                "extension": {"H2kLabel": f"{ceiling_label}"},
            }

            new_attic = {
                "SystemIdentifier": {"@id": attic_id},
                "AtticType": {
                    "FlatRoof": None,
                },
                "AttachedToRoof": {"@idref": roof_id},
                "extension": {"H2kLabel": f"{ceiling_label}"},
            }

            skylight_attachment = {
                "AttachedToRoof": {"@idref": roof_id},
            }

            hpxml_attics = [*hpxml_attics, new_attic]
            hpxml_roofs = [*hpxml_roofs, new_roof]

        elif construction_type.lower() == "scissor":
            # scissor => Floor (ceiling), 2x gable end walls for attic portion, roof, attic (AtticType = Attic) w/ area geometry calculations
            # ceiling pitch assumed to be half of roof pitch (provided)
            model_data.inc_wall_count()
            model_data.inc_floor_count()
            model_data.inc_roof_count()
            model_data.inc_attic_count()

            wall_id = f"Wall{model_data.get_wall_count()}"
            floor_id = f"Floor{model_data.get_floor_count()}"
            roof_id = f"Roof{model_data.get_roof_count()}"
            attic_id = f"Attic{model_data.get_attic_count()}"

            # Geometry
            roof_pitch = h2k.get_selection_field(ceiling, "roof_pitch")
            if roof_pitch == None:
                roof_pitch = int(
                    round(12 * h2k.get_number_field(ceiling, "roof_pitch_value"))
                )

            ceiling_pitch = roof_pitch / 2

            sloped_ceiling_area = h2k.get_number_field(ceiling, "ceiling_area")
            ceiling_length = h2k.get_number_field(
                ceiling, "ceiling_length"
            )  # total compressed length, 2 sides for this ceiling type

            roof_angle = math.atan(roof_pitch / 12)
            ceiling_angle = math.atan(ceiling_pitch / 12)

            # Projected ceiling area (i.e. ceiling area if it were a flat ceiling)
            proj_ceiling_area = sloped_ceiling_area * math.cos(ceiling_angle)

            roof_area = proj_ceiling_area / math.cos(roof_angle)

            gable_wall_width = proj_ceiling_area / (
                ceiling_length / 2
            )  # divide length by 2, since the input captures both compressed sides of home

            # roof_height relative to the projected ceiling
            roof_height = (gable_wall_width / 2) * (
                roof_pitch / 12
            )  # half gable wall length is x, height is y in the pitch equation

            ceiling_height = (gable_wall_width / 2) * (ceiling_pitch / 12)

            # For this ceiling type, we assume there are two gable ends
            # We also subtract the wall area contained in the heated volume
            # 2x the triangle with base = gable_wall_width, height = roof_height,
            # subtracting 2x the triangle whose base is the projected ceiling plane,
            # and whose height is the ceiling height above that plane
            tot_gable_wall_area = (2 * (1 / 2) * gable_wall_width * roof_height) - (
                2 * (1 / 2) * gable_wall_width * ceiling_height
            )

            # Rvalues
            ceiling_rval = h2k.get_number_field(ceiling, "ceiling_r_value")
            gable_wall_rval = 5.678 * (0.083 + 0.11)  # default in h2k
            roof_rval = 5.678 * (0.111 + 0.078)  # default in h2k
            if has_roof_cavity_inputs:
                sloped_roof_sheathing_r_value = h2k.get_number_field(
                    roof_cavity_inputs, "sloped_roof_sheathing_r_value"
                )
                sloped_roof_material_r_value = h2k.get_number_field(
                    roof_cavity_inputs, "sloped_roof_material_r_value"
                )
                gable_ends_sheathing_r_value = h2k.get_number_field(
                    roof_cavity_inputs, "gable_ends_sheathing_r_value"
                )
                gable_ends_exterior_r_value = h2k.get_number_field(
                    roof_cavity_inputs, "gable_ends_exterior_r_value"
                )

                gable_wall_rval = (
                    gable_ends_sheathing_r_value + gable_ends_exterior_r_value
                )
                roof_rval = sloped_roof_sheathing_r_value + sloped_roof_material_r_value

            # Horizontal ceiling surface, modelled as a Floor in HPXML
            new_floor = {
                "SystemIdentifier": {"@id": floor_id},
                "ExteriorAdjacentTo": "attic - vented",  # always for this type of floor as a ceiling
                "InteriorAdjacentTo": "conditioned space",  # always
                "FloorOrCeiling": "ceiling",
                "FloorType": {"WoodFrame": None},  # for now, always WoodFrame
                "Area": sloped_ceiling_area,  # [ft2]
                "InteriorFinish": {
                    "Type": "gypsum board"
                },  # default for ceiling floors
                "Insulation": {
                    "SystemIdentifier": {"@id": f"{floor_id}Insulation"},
                    "AssemblyEffectiveRValue": round(
                        ceiling_rval, 2
                    ),  # Ceiling r-value applied here
                },
                "extension": {"H2kLabel": f"{ceiling_label}"},
            }

            new_wall = {
                "SystemIdentifier": {"@id": wall_id},
                "ExteriorAdjacentTo": "outside",
                "InteriorAdjacentTo": "attic - vented",  # always
                "AtticWallType": "gable",
                "WallType": {"WoodStud": None},  # for now, always WoodStud
                "Area": tot_gable_wall_area,  # [ft2]
                "Siding": "wood siding",  # for now, always wood siding
                "SolarAbsorptance": wall_absorptance,
                "Emittance": "0.9",  # Default
                "Insulation": {
                    "SystemIdentifier": {"@id": f"{wall_id}Insulation"},
                    "AssemblyEffectiveRValue": round(gable_wall_rval, 2),
                },
                "extension": {"H2kLabel": f"{ceiling_label}"},
            }

            new_roof = {
                "SystemIdentifier": {"@id": roof_id},
                "InteriorAdjacentTo": "attic - vented",  # always
                "Area": roof_area,
                "RoofType": roof_material,
                "SolarAbsorptance": roof_absorptance,
                "Emittance": "0.9",  # Default in HPXML
                "Pitch": roof_pitch,
                "RadiantBarrier": "false",  # Default
                "Insulation": {
                    "SystemIdentifier": {"@id": f"{roof_id}Insulation"},
                    "AssemblyEffectiveRValue": round(roof_rval, 2),
                },
                "extension": {"H2kLabel": f"{ceiling_label}"},
            }

            new_attic = {
                "SystemIdentifier": {"@id": attic_id},
                "AtticType": {
                    "Attic": {"Vented": "true"},
                },
                # "WithinInfiltrationVolume": "false",
                "VentilationRate": {"UnitofMeasure": "ACHnatural", "Value": 2.4},
                "AttachedToRoof": {"@idref": roof_id},
                "AttachedToWall": {"@idref": wall_id},
                "AttachedToFloor": {"@idref": floor_id},
                "extension": {"H2kLabel": f"{ceiling_label}"},
            }

            skylight_attachment = {
                "AttachedToRoof": {"@idref": roof_id},
                "AttachedToFloor": {"@idref": floor_id},
            }

            hpxml_attics = [*hpxml_attics, new_attic]
            hpxml_roofs = [*hpxml_roofs, new_roof]
            hpxml_walls = [*hpxml_walls, new_wall]
            hpxml_floors = [*hpxml_floors, new_floor]
        else:
            # TODO: add error state here
            print("unknown ceiling type detected")

        # Handle subcomponents on ceilings (skylights)
        # Subcomponents not nested with HPXML
        h2k_windows = ceiling.get("Components", {}).get("Window", {})

        # Windows
        window_output = get_skylights(h2k_windows, skylight_attachment, model_data)
        hpxml_skylights = [*hpxml_skylights, *window_output["hpxml_skylights"]]

    return {
        "attics": hpxml_attics,
        "roofs": hpxml_roofs,
        "gable_walls": hpxml_walls,
        "skylights": hpxml_skylights,
        "ceiling_floors": hpxml_floors,
    }
