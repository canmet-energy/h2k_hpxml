from ..utils import h2k


def get_infiltration(h2k_dict, model_data={}):
    house_volume = h2k.get_number_field(h2k_dict, "house_volume")
    air_leakage_ach = h2k.get_number_field(h2k_dict, "air_leakage_ach")

    res_facility_type = model_data.get_building_detail("res_facility_type")
    attached_unit = "attached" in res_facility_type or "apartment" in res_facility_type

    infiltration = {
        "AirInfiltrationMeasurement": {
            "SystemIdentifier": {"@id": "AirInfiltrationMeasurement1"},
            **(
                {"TypeOfInfiltrationLeakage": "unit exterior only"}
                if attached_unit
                else {}
            ),
            "HousePressure": 50,  # always ACH50
            "BuildingAirLeakage": {
                "UnitofMeasure": "ACH",
                "AirLeakage": air_leakage_ach,
            },
            "InfiltrationVolume": house_volume,
        }
    }

    return infiltration
