"""
Main module that handles the conversion of an h2k file to hpxml

Inputs: h2k string in xml format, config class instance to handle config params

Outputs: hpxml string
"""

import xmltodict
import os

from .utils import h2k, obj, weather, hot_water_usage

from .enclosure.walls import get_walls, get_attached_walls
from .enclosure.floors import get_floors
from .enclosure.ceilings import get_ceilings
from .enclosure.basements import get_basements
from .enclosure.crawlspaces import get_crawlspaces
from .enclosure.slabs import get_slabs
from .enclosure.infiltration import get_infiltration
from .baseloads.appliances import get_appliances
from .baseloads.lighting import get_lighting
from .baseloads.miscloads import get_plug_loads
from .systems.systems import get_systems
from .program_mode.ashrae140 import apply_ashrae_140

from . import Model


def h2ktohpxml(h2k_string="", config={}):

    # ================ 0. Get Config parameters  ================
    add_test_wall = config.get(
        "add_test_wall", False
    )  # To add a test adiabatic wall to check impact on loads

    translation_mode = config.get("translation_mode", "SOC")
    print("Translation Mode: \t\t", translation_mode)
    # ================ 1. Load template HPXML file ================
    base_hpxml_path = os.path.join(os.path.dirname(__file__), "templates", "base.xml")
    with open(base_hpxml_path, "r", encoding="utf-8") as f:
        base_hpxml = f.read()

    # ================ 1.a Parse xml ================
    h2k_dict = xmltodict.parse(h2k_string)
    # print(h2k_dict["HouseFile"].keys())

    hpxml_dict = xmltodict.parse(base_hpxml)
    # print(hpxml_dict["HPXML"].keys())

    model_data = Model.ModelData()

    model_data.set_results(h2k_dict)

    results = model_data.get_results("")

    # ================ 2. HPXML Section: Software Info ================

    # ================ 3. HPXML Section: Building ================
    # No changes required, but set up model details here
    # This information may be used elsewhere in calculations, so we append it to model_data for easy access
    model_data.set_building_details(
        {
            "building_type": h2k.get_selection_field(h2k_dict, "building_type"),
            "ag_heated_floor_area": h2k.get_number_field(
                h2k_dict, "ag_heated_floor_area"
            ),
            "bg_heated_floor_area": h2k.get_number_field(
                h2k_dict, "bg_heated_floor_area"
            ),
        }
    )

    if model_data.get_building_detail("building_type") != "house":
        # get murb details
        murb_unit_counts = obj.get_val(
            h2k_dict, "HouseFile,House,Specifications,NumberOf"
        )

        model_data.set_building_details(
            {
                "storeys_in_building": murb_unit_counts.get("@storeysInBuilding", 0),
                "res_units": murb_unit_counts.get("@dwellingUnits", 0),
                "non_res_units": murb_unit_counts.get("@nonResUnits", 0),
                "units_visited": murb_unit_counts.get("@unitsVisited", 0),
                "common_space_area": h2k.get_number_field(
                    h2k_dict, "common_space_area"
                ),
                "non_res_unit_area": h2k.get_number_field(
                    h2k_dict, "non_res_unit_area"
                ),
            }
        )

    # ================ 4. HPXML Section: Building Site ================
    # Handled in template

    # ================ 5. HPXML Section: Building Summary ================
    # Note there is a Buiilding/Site section and a BuildingSummary/Site section
    # /HPXML/Building/BuildingDetails/BuildingSummary/Site
    building_sum_site_dict = hpxml_dict["HPXML"]["Building"]["BuildingDetails"][
        "BuildingSummary"
    ]["Site"]

    # Front-facing direction
    building_sum_site_dict["AzimuthOfFrontOfHome"] = h2k.get_selection_field(
        h2k_dict, "azimuth_of_home"
    )

    # Shielding of home
    building_sum_site_dict["ShieldingofHome"] = h2k.get_selection_field(
        h2k_dict, "shielding_of_home"
    )

    # Ground Conductivity
    building_sum_site_dict["Soil"]["Conductivity"] = h2k.get_selection_field(
        h2k_dict, "ground_conductivity"
    )

    # /HPXML/Building/BuildingDetails/BuildingSummary/BuildingOccupancy
    # HPXML's default occupant schedules are not altered at this stage
    # num_occupants = (
    #     int(
    #         obj.get_val(
    #             h2k_dict, "HouseFile,House,BaseLoads,Occupancy,Adults,@occupants"
    #         )
    #     )
    #     + int(
    #         obj.get_val(
    #             h2k_dict, "HouseFile,House,BaseLoads,Occupancy,Children,@occupants"
    #         )
    #     )
    #     + int(
    #         obj.get_val(
    #             h2k_dict, "HouseFile,House,BaseLoads,Occupancy,Infants,@occupants"
    #         )
    #     )
    # )

    num_occupants = 3  # SOC Hardcoded

    hpxml_dict["HPXML"]["Building"]["BuildingDetails"]["BuildingSummary"][
        "BuildingOccupancy"
    ] = {"NumberofResidents": num_occupants}

    model_data.set_building_details(
        {
            "num_occupants": num_occupants,
        }
    )

    # /HPXML/Building/BuildingDetails/BuildingSummary/BuildingConstruction
    building_const_dict = hpxml_dict["HPXML"]["Building"]["BuildingDetails"][
        "BuildingSummary"
    ]["BuildingConstruction"]

    # ResidentialFacilityType
    res_facility_type = h2k.get_selection_field(h2k_dict, "res_facility_type")
    print("Residential Facility Type: \t", res_facility_type)
    model_data.set_building_details({"res_facility_type": res_facility_type})
    building_const_dict["ResidentialFacilityType"] = res_facility_type

    # NumberofConditionedFloorsAboveGrade
    num_ag_storeys = h2k.get_selection_field(h2k_dict, "num_ag_storeys")
    building_const_dict["NumberofConditionedFloorsAboveGrade"] = num_ag_storeys

    # NumberofConditionedFloors
    # Need to check for a basement, this field always excludes a conditioned crawlspace
    basement_dict = obj.get_val(h2k_dict, "HouseFile,House,Components,Basement")
    basement_dict = (
        basement_dict if isinstance(basement_dict, list) else [basement_dict]
    )[
        0
    ]  # Handles case where we have more than one basement components
    num_bg_storeys = 1 if "@exposedSurfacePerimeter" in basement_dict.keys() else 0

    num_tot_storeys = num_ag_storeys + num_bg_storeys

    building_const_dict["NumberofConditionedFloors"] = num_tot_storeys

    # NumberofBedrooms
    num_bedrooms = h2k.get_number_field(h2k_dict, "num_bedrooms")
    building_const_dict["NumberofBedrooms"] = num_bedrooms
    model_data.set_building_details(
        {
            "num_bedrooms": num_bedrooms,
        }
    )

    # NumberofBathrooms
    num_bathrooms = h2k.get_number_field(h2k_dict, "num_bathrooms")
    if num_bathrooms < 1:
        model_data.add_warning_message(
            {
                "message": "The h2k model does not have any bathrooms specified. One bathroom has been added to the HPXML model to prevent calculation errors."
            }
        )

    building_const_dict["NumberofBathrooms"] = max(num_bathrooms, 1)

    # ConditionedFloorArea (AFTER COMPONENTS)

    # ConditionedBuildingVolume
    house_volume = h2k.get_number_field(h2k_dict, "house_volume")
    building_const_dict["ConditionedBuildingVolume"] = house_volume

    # Natural Ventilation
    # Handled in template (0 days/week)

    # ================ 6. HPXML Section: Climate Zones ================
    # /HPXML/Building/BuildingDetails/ClimateandRiskZones/WeatherStation
    weather_dict = hpxml_dict["HPXML"]["Building"]["BuildingDetails"][
        "ClimateandRiskZones"
    ]["WeatherStation"]

    # Get the weather file
    if translation_mode == "ASHRAE140":
        # Selects one of the two ashrae140 weather files:
        # USA_CO_Colorado.Springs-Peterson.Field.724660_TMY3
        # USA_NV_Las.Vegas-McCarran.Intl.AP.723860_TMY3
        weather_location = obj.get_val(
            h2k_dict, "HouseFile,ProgramInformation,Weather,Location,English"
        )

        if weather_location == "Lasvega":
            weather_file = "USA_NV_Las.Vegas-McCarran.Intl.AP.723860_TMY3"
        else:
            weather_file = "USA_CO_Colorado.Springs-Peterson.Field.724660_TMY3"

    else:
        # Grabs the CWEC weather file
        weather_file = weather.get_cwec_file(
            obj.get_val(
                h2k_dict, "HouseFile,ProgramInformation,Weather,Region,English"
            ),
            obj.get_val(
                h2k_dict, "HouseFile,ProgramInformation,Weather,Location,English"
            ),
        )

    print(
        "HOT2000 Weather Location: \t",
        obj.get_val(h2k_dict, "HouseFile,ProgramInformation,Weather,Location,English"),
    )

    # print(weather_file)

    weather_dict["Name"] = weather_file
    weather_dict["extension"]["EPWFilePath"] = f"{weather_file}.epw"

    # ================ 7. HPXML Section: Enclosure ================
    walls = []
    floors = []
    attics = []
    roofs = []
    windows = []
    skylights = []
    doors = []
    rim_joists = []
    foundations = []
    foundation_walls = []
    slabs = []
    # Subcomponents (windows, doors, rim joists) all collected through parents

    # Walls
    wall_results = get_walls(h2k_dict, model_data)
    walls = [*walls, *wall_results["walls"]]
    windows = [*windows, *wall_results["windows"]]
    doors = [*doors, *wall_results["doors"]]
    rim_joists = [*rim_joists, *wall_results["rim_joists"]]

    # Exposed Floors
    floor_results = get_floors(h2k_dict, model_data)
    floors = [*floors, *floor_results["floors"]]

    # Ceilings
    ceiling_results = get_ceilings(h2k_dict, model_data)
    attics = [*attics, *ceiling_results["attics"]]
    roofs = [*roofs, *ceiling_results["roofs"]]
    walls = [*walls, *ceiling_results["gable_walls"]]
    skylights = [*skylights, *ceiling_results["skylights"]]
    floors = [*floors, *ceiling_results["ceiling_floors"]]

    # Basements
    basement_results = get_basements(h2k_dict, model_data)
    windows = [*windows, *basement_results["windows"]]
    doors = [*doors, *basement_results["doors"]]
    rim_joists = [*rim_joists, *basement_results["rim_joists"]]
    foundations = [*foundations, *basement_results["foundations"]]
    foundation_walls = [*foundation_walls, *basement_results["foundation_walls"]]
    slabs = [*slabs, *basement_results["slabs"]]
    walls = [*walls, *basement_results["pony_walls"]]
    floors = [*floors, *basement_results["floors"]]

    # Crawlspaces
    crawlspace_results = get_crawlspaces(h2k_dict, model_data)
    windows = [*windows, *crawlspace_results["windows"]]
    doors = [*doors, *crawlspace_results["doors"]]
    rim_joists = [*rim_joists, *crawlspace_results["rim_joists"]]
    foundations = [*foundations, *crawlspace_results["foundations"]]
    foundation_walls = [*foundation_walls, *crawlspace_results["foundation_walls"]]
    slabs = [*slabs, *crawlspace_results["slabs"]]
    floors = [*floors, *crawlspace_results["floors"]]

    # Slab-on-grades
    slab_results = get_slabs(h2k_dict, model_data)
    slabs = [*slabs, *slab_results["slabs"]]

    # Airtightness
    infiltration = get_infiltration(h2k_dict, model_data)

    # Handle attached walls for attached homes
    attached_wall_results = get_attached_walls(h2k_dict, model_data, add_test_wall)
    walls = [*walls, *attached_wall_results["walls"]]

    # xmltodict unparse handles empty dicts/lists
    # Garages between Foundations and Roofs if they are modelled
    hpxml_dict["HPXML"]["Building"]["BuildingDetails"]["Enclosure"] = {
        "AirInfiltration": infiltration,
        **({"Attics": {"Attic": attics}} if attics != [] else {}),
        **({"Foundations": {"Foundation": foundations}} if foundations != [] else {}),
        **({"Roofs": {"Roof": roofs}} if roofs != [] else {}),
        **({"RimJoists": {"RimJoist": rim_joists}} if rim_joists != [] else {}),
        **({"Walls": {"Wall": walls}} if walls != [] else {}),
        **(
            {"FoundationWalls": {"FoundationWall": foundation_walls}}
            if foundation_walls != []
            else {}
        ),
        **({"Floors": {"Floor": floors}} if floors != [] else {}),
        **({"Slabs": {"Slab": slabs}} if slabs != [] else {}),
        **({"Windows": {"Window": windows}} if windows != [] else {}),
        **({"Skylights": {"Skylight": skylights}} if skylights != [] else {}),
        **({"Doors": {"Door": doors}} if doors != [] else {}),
    }

    # ConditionedFloorArea after components to ensure it aligns with areas provided in components
    foundation_details = model_data.get_foundation_details()
    # total_foundation_area = sum([fnd["total_area"] for fnd in foundation_details if "expFloor" != fnd["type"]])
    total_foundation_area = sum([fnd["total_area"] for fnd in foundation_details])

    ag_heated_floor_area = model_data.get_building_detail("ag_heated_floor_area")
    bg_heated_floor_area = model_data.get_building_detail("bg_heated_floor_area")

    # Check here to ensure no errors in HPXML, since bg_heated_floor_area is an input in h2k that is separate from the actual component areas
    if total_foundation_area > bg_heated_floor_area:
        bg_heated_floor_area = total_foundation_area

    building_const_dict["ConditionedFloorArea"] = (
        ag_heated_floor_area + bg_heated_floor_area
    )

    print("Heated Floor Area (ft2): \t", building_const_dict["ConditionedFloorArea"])

    # ================ 8. HPXML Section: Systems ================
    # Run appliances first so we know hot water consumption
    appliance_result = get_appliances(h2k_dict, model_data)

    systems_results = get_systems(h2k_dict, model_data)
    hvac_dict = systems_results["hvac_dict"]
    dhw_dict = systems_results["dhw_dict"]
    mech_vent_dict = systems_results["mech_vent_dict"]
    solar_dhw_dict = systems_results["solar_dhw_dict"]
    generation_dict = systems_results["generation_dict"]

    # Calculate hot water fixture multiplier
    fixtures_multiplier = hot_water_usage.get_fixtures_multiplier(h2k_dict, model_data)

    hpxml_dict["HPXML"]["Building"]["BuildingDetails"]["Systems"] = {
        **({"HVAC": hvac_dict} if model_data.get_is_hvac_translated() else {}),
        **({"MechanicalVentilation": mech_vent_dict} if mech_vent_dict != {} else {}),
        **(
            {
                "WaterHeating": {
                    **dhw_dict,
                    "extension": {"WaterFixturesUsageMultiplier": fixtures_multiplier},
                }
            }
            if dhw_dict != {}
            else {}
        ),
        **({"SolarThermal": solar_dhw_dict} if solar_dhw_dict != {} else {}),
        **({"Photovoltaics": generation_dict} if generation_dict != {} else {}),
    }

    # Specify presence of flues if any have been detected while processing systems
    hpxml_dict["HPXML"]["Building"]["BuildingDetails"]["Enclosure"][
        "AirInfiltration"
    ] = {
        **hpxml_dict["HPXML"]["Building"]["BuildingDetails"]["Enclosure"][
            "AirInfiltration"
        ],
        "extension": {
            "HasFlueOrChimneyInConditionedSpace": len(model_data.get_flue_diameters())
            > 0
        },
    }

    # ================ 9. HPXML Section: Appliances ================
    hpxml_dict["HPXML"]["Building"]["BuildingDetails"]["Appliances"] = appliance_result

    # ================ 10. HPXML Section: Lighting & Ceiling Fans ================

    hpxml_dict["HPXML"]["Building"]["BuildingDetails"]["Lighting"] = get_lighting(
        h2k_dict, model_data
    )

    # ================ 11. HPXML Section: Pools & Permanent Spas ================
    # Not considered under SOC, possibly under atypical loads

    # ================ 12. HPXML Section: Misc Loads ================
    hpxml_dict["HPXML"]["Building"]["BuildingDetails"]["MiscLoads"] = get_plug_loads(
        h2k_dict, model_data
    )

    # ================ Apply overall translation mode specifications ================
    if translation_mode == "ASHRAE140":
        hpxml_dict = apply_ashrae_140(hpxml_dict, h2k_dict, model_data)

    # Done!
    return xmltodict.unparse(
        hpxml_dict, encoding="utf-8", pretty=True, short_empty_elements=True
    )
