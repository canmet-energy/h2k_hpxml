import math

from ..utils import obj, h2k


# Here we always return an array of objects, because we could be dealing with a primary + secondary system configuration
def get_hot_water_systems(h2k_dict, model_data):

    hot_water_temperature = h2k.get_number_field(h2k_dict, "hot_water_temperature")
    hot_water_temperature_adv_uspec = h2k.get_number_field(
        h2k_dict, "hot_water_temperature_adv_uspec"
    )

    model_data.set_building_details(
        {
            "hot_water_temperature": (
                hot_water_temperature
                if hot_water_temperature > 0
                else hot_water_temperature_adv_uspec
            ),
        }
    )

    hpxml_dhw = []
    hpxml_solar_dhw = {}

    # TODO: Error handling when DHW is empty
    components = obj.get_val(h2k_dict, "HouseFile,House,Components")

    if "HotWater" not in components.keys():
        hot_water_dict = []

        return []
    else:
        hot_water_dict = components["HotWater"]

    primary_dhw_dict = hot_water_dict.get("Primary", {})
    secondary_dhw_dict = hot_water_dict.get("Secondary", {})

    # Note that we have a special case: Solar primary hot water with a back-up

    primary_dhw_type = obj.get_val(primary_dhw_dict, "EnergySource,English")

    if primary_dhw_type == "Solar":
        primary_dhw = get_single_dhw_system(
            secondary_dhw_dict, model_data.get_system_id("primary_dhw"), model_data
        )
        hpxml_dhw = [primary_dhw]

        hpxml_solar_dhw = get_solar_dhw_system(
            primary_dhw_dict, model_data.get_system_id("primary_dhw"), model_data
        )

    else:
        primary_dhw = get_single_dhw_system(
            primary_dhw_dict, model_data.get_system_id("primary_dhw"), model_data
        )
        hpxml_dhw = [primary_dhw]

        secondary_dhw = get_single_dhw_system(
            secondary_dhw_dict, model_data.get_system_id("secondary_dhw"), model_data
        )

        if secondary_dhw != {}:
            hpxml_dhw = [*hpxml_dhw, secondary_dhw]

    return hpxml_dhw, hpxml_solar_dhw


def get_single_dhw_system(system_dict, sys_id, model_data):
    if system_dict == {}:
        return {}

    # H2k does not allow a secondary DHW system when a combo is defined
    combi_related_hvac_id = model_data.get_system_id("combi_related_hvac_id")

    tank_type = h2k.get_selection_field(system_dict, "hot_water_tank_type")
    fuel_type = h2k.get_selection_field(system_dict, "hot_water_fuel_type")
    tank_location = h2k.get_selection_field(system_dict, "hot_water_tank_location")

    tank_volume = h2k.get_number_field(system_dict, "hot_water_tank_volume")
    load_fraction = h2k.get_number_field(system_dict, "hot_water_load_fraction")

    # Handles case when there's only one system so the field is empty
    # H2k doesn't allow you to have either fraction of tank = 0 when 2 DHW systems are defined
    if load_fraction == 0:
        load_fraction = 1

    heating_capacity = h2k.get_number_field(system_dict, "hot_water_heating_capacity")
    energy_factor = h2k.get_number_field(system_dict, "hot_water_energy_factor")
    heat_pump_cop = h2k.get_number_field(system_dict, "hot_water_heat_pump_cop")
    flue_diameter = h2k.get_number_field(system_dict, "hot_water_flue_diameter")
    hot_water_temperature = model_data.get_building_detail("hot_water_temperature")

    if flue_diameter > 0:
        model_data.set_flue_diameters(flue_diameter)

    # likely very rare, but if the tank is in a crawlspace we need to match the type used
    if tank_location == "CRAWLSPACE":
        crawlspace_location = model_data.get_building_detail("crawlspace_location")
        tank_location = crawlspace_location

    is_uef = obj.get_val(system_dict, "EnergyFactor,@isUniform")
    uef_draw_pattern = h2k.get_selection_field(
        system_dict, "hot_water_uef_draw_pattern"
    )

    energy_factor_obj = {}
    if is_uef == "true":
        energy_factor_obj = {
            "UniformEnergyFactor": energy_factor,
            "UsageBin": uef_draw_pattern,
        }
    else:
        energy_factor_obj = {
            "EnergyFactor": energy_factor,
        }

    hpxml_water_heating = {}

    if combi_related_hvac_id != None:
        # H2k does not allow a secondary DHW system when a combo is defined
        model_data.set_is_dhw_translated(True)
        # hpxml_water_heating = {
        #     "SystemIdentifier": {"@id": sys_id},
        #     "WaterHeaterType": (
        #         "space-heating boiler with tankless coil"
        #         if tank_volume == 0
        #         else "space-heating boiler with storage tank"
        #     ),
        #     "Location": tank_location,
        #     **({"TankVolume": tank_volume} if tank_volume != 0 else {}),
        #     "FractionDHWLoadServed": load_fraction,
        #     "HotWaterTemperature": hot_water_temperature,
        #     "RelatedHVACSystem": {"@idref": combi_related_hvac_id},
        # }

        combo_fuel_type = model_data.get_building_detail("combo_fuel_type")
        combo_energy_factor = model_data.get_building_detail("combo_energy_factor")
        combo_tank_volume = model_data.get_building_detail("combo_tank_volume")

        hpxml_water_heating = {
            "SystemIdentifier": {"@id": sys_id},
            "FuelType": combo_fuel_type,
            "WaterHeaterType": (
                "instantaneous water heater"
                if combo_tank_volume == 0
                else "storage water heater"
            ),
            "Location": tank_location,
            **({"TankVolume": combo_tank_volume} if combo_tank_volume != 0 else {}),
            "FractionDHWLoadServed": load_fraction,
            **({"HeatingCapacity": heating_capacity} if heating_capacity > 0 else {}),
            "EnergyFactor": combo_energy_factor,
            "HotWaterTemperature": hot_water_temperature,
            # "RelatedHVACSystem": {"@idref": combi_related_hvac_id}, #Disabling this as it appears combos aren't interpreted the same
        }

    elif tank_type == "storage water heater":
        model_data.set_is_dhw_translated(True)
        hpxml_water_heating = {
            "SystemIdentifier": {"@id": sys_id},
            "FuelType": fuel_type,
            "WaterHeaterType": tank_type,
            "Location": tank_location,
            "TankVolume": tank_volume,
            "FractionDHWLoadServed": load_fraction,
            **({"HeatingCapacity": heating_capacity} if heating_capacity > 0 else {}),
            **energy_factor_obj,
            # "RecoveryEfficiency": Defaults to 0.98 for electricity or regression analysis for other fuel types
            "HotWaterTemperature": hot_water_temperature,
        }

    elif tank_type == "instantaneous water heater":
        model_data.set_is_dhw_translated(True)
        hpxml_water_heating = {
            "SystemIdentifier": {"@id": sys_id},
            "FuelType": fuel_type,
            "WaterHeaterType": tank_type,
            "Location": tank_location,
            "FractionDHWLoadServed": load_fraction,
            **energy_factor_obj,
            # "RecoveryEfficiency": Defaults to 0.98 for electricity or regression analysis for other fuel types
            "HotWaterTemperature": hot_water_temperature,
        }

    elif tank_type == "heat pump water heater":
        model_data.set_is_dhw_translated(True)
        # Multiply input COP by 0.9 to reverse h2k input guidelines and get rated EF/UEF
        heat_pump_ef = 0.9 * heat_pump_cop

        if is_uef == "true":
            energy_factor_obj["UniformEnergyFactor"] = heat_pump_ef
        else:
            energy_factor_obj["EnergyFactor"] = heat_pump_ef

        hpxml_water_heating = {
            "SystemIdentifier": {"@id": sys_id},
            "FuelType": fuel_type,
            "WaterHeaterType": tank_type,
            "Location": tank_location,
            "TankVolume": tank_volume,
            "FractionDHWLoadServed": load_fraction,
            **({"HeatingCapacity": heating_capacity} if heating_capacity > 0 else {}),
            **energy_factor_obj,
            # "RecoveryEfficiency": Defaults to 0.98 for electricity or regression analysis for other fuel types
            "HotWaterTemperature": hot_water_temperature,
        }

        #   <WaterHeatingSystem>
        #     <SystemIdentifier id='WaterHeatingSystem1'/>
        #     <FuelType>electricity</FuelType>
        #     <WaterHeaterType>heat pump water heater</WaterHeaterType>
        #     <Location>conditioned space</Location>
        #     <TankVolume>50.0</TankVolume>
        #     <FractionDHWLoadServed>1.0</FractionDHWLoadServed>
        #     <UniformEnergyFactor>3.75</UniformEnergyFactor>
        #     <UsageBin>medium</UsageBin>
        #     <HotWaterTemperature>125.0</HotWaterTemperature>
        #   </WaterHeatingSystem>

        # <WaterHeatingSystem>
        #     <SystemIdentifier id='WaterHeatingSystem1'/>
        #     <FuelType>electricity</FuelType>
        #     <WaterHeaterType>heat pump water heater</WaterHeaterType>
        #     <Location>conditioned space</Location>
        #     <TankVolume>80.0</TankVolume>
        #     <FractionDHWLoadServed>1.0</FractionDHWLoadServed>
        #     <EnergyFactor>2.3</EnergyFactor>
        #     <HotWaterTemperature>125.0</HotWaterTemperature>
        #   </WaterHeatingSystem>

    # Save DWHR for later (hot_water_distribution.py), only for primary system, HPXML can't handle 2 DWHR systems
    if "1" in sys_id:
        # Looking for the "1" in the DHW system id to know we're dealing with the primary system
        model_data.set_building_details(
            {
                "dwhr_system_primary": system_dict.get("DrainWaterHeatRecovery", {}),
            }
        )

    return hpxml_water_heating


def get_solar_dhw_system(system_dict, sys_id, model_data):
    if system_dict == {}:
        return {}

    # Search file results to determine solar fraction of dhw heating
    # Models the system with a fraction of 0 if no results are in the file
    solar_dhw_fraction = 0.01
    results = model_data.get_results()

    if results != {}:
        solar_dhw_energy = float(obj.get_val(results, "Annual,HotWaterDemand,@primary"))
        secondary_dhw_energy = float(
            obj.get_val(results, "Annual,HotWaterDemand,@secondary")
        )
        solar_dhw_fraction = round(
            solar_dhw_energy / (solar_dhw_energy + secondary_dhw_energy), 2
        )

    else:
        model_data.add_warning_message(
            {
                "message": "A solar thermal water heating system was defined but the h2k file does not include results. This system cannot be accurately modelled in the resulting HPXML file, and has been given a placeholder solar fraction of 0.01."
            }
        )

    hpxml_solar_thermal = {
        "SystemIdentifier": {"@id": model_data.get_system_id("solar_dhw")},
        "SystemType": "hot water",
        "ConnectedTo": {"@idref": sys_id},
        "SolarFraction": solar_dhw_fraction,
    }

    return hpxml_solar_thermal
