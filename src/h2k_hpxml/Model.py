class ModelData:
    def __init__(self):
        # Model details
        self.building_details = {"building_type": "house", "murb_units": 0}

        # Tracker for foundation exposed perimeters and areas
        self.foundation_details = []
        self.wall_segments = []

        # Counters
        self.window_count = 0
        self.door_count = 0
        self.floor_header_count = 0
        self.wall_count = 0
        self.floor_count = 0
        self.ceiling_count = 0
        self.attic_count = 0
        self.roof_count = 0
        self.foundation_count = 0
        self.foundation_wall_count = 0
        self.crawlspace_count = 0
        self.slab_count = 0

        # Tracking info for Systems
        self.is_hvac_translated = False
        self.is_dhw_translated = False
        self.heating_distribution_type = None
        self.ac_hp_distribution_type = None
        self.suppl_heating_distribution_types = []
        self.system_ids = {"primary_heating": "HeatingSystem1"}

        self.flue_diameters = []

        # Results
        self.results = {
            "General": {},
            "SOC": {},
            "Reference": {},
        }

        # Tracking errors
        self.error_list = []

        self.warnings_list = []

    def __getitem__(self, key):
        return self.building_details.get(key, key)

    def __setitem__(self, key, newvalue):
        self.building_details[key] = newvalue

    # tracking model details
    def set_building_details(self, obj):
        for key in obj.keys():
            self.__setitem__(key, obj[key])

    def get_building_detail(self, key, default=None):
        value = self.__getitem__(key)

        if value == key:
            return default
        else:
            return value

    # foundation detail trackers
    def add_foundation_detail(self, fnd_perim):
        self.foundation_details = [*self.foundation_details, fnd_perim]

    def get_foundation_details(self):
        return self.foundation_details

    # wall trackers
    def add_wall_segment(self, wall_sgmt):
        self.wall_segments = [*self.wall_segments, wall_sgmt]

    def get_wall_segments(self):
        return self.wall_segments

    # warning list
    def add_warning_message(self, message):
        self.warnings_list = [*self.warnings_list, message]

    def get_warning_messages(self):
        return self

    # Increment counters
    def inc_window_count(self):
        self.window_count += 1

    def inc_door_count(self):
        self.door_count += 1

    def inc_floor_header_count(self):
        self.floor_header_count += 1

    def inc_wall_count(self):
        self.wall_count += 1

    def inc_floor_count(self):
        self.floor_count += 1

    def inc_ceiling_count(self):
        self.ceiling_count += 1

    def inc_attic_count(self):
        self.attic_count += 1

    def inc_roof_count(self):
        self.roof_count += 1

    def inc_foundation_wall_count(self):
        self.foundation_wall_count += 1

    def inc_foundation_count(self):
        self.foundation_count += 1

    def inc_crawlspace_count(self):
        self.crawlspace_count += 1

    def inc_slab_count(self):
        self.slab_count += 1

    # get counters
    def get_window_count(self):
        return self.window_count

    def get_door_count(self):
        return self.door_count

    def get_floor_header_count(self):
        return self.floor_header_count

    def get_wall_count(self):
        return self.wall_count

    def get_floor_count(self):
        return self.floor_count

    def get_ceiling_count(self):
        return self.ceiling_count

    def get_attic_count(self):
        return self.attic_count

    def get_roof_count(self):
        return self.roof_count

    def get_foundation_wall_count(self):
        return self.foundation_wall_count

    def get_foundation_count(self):
        return self.foundation_count

    def get_crawlspace_count(self):
        return self.crawlspace_count

    def get_slab_count(self):
        return self.slab_count

    def set_is_hvac_translated(self, val):
        # Set to True if we've translated the entire HVAC system into a valid object
        self.is_hvac_translated = val

    def set_is_dhw_translated(self, val):
        # Set to True if we've translated the entire DHW system into a valid object
        self.is_dhw_translated = val

    def get_is_hvac_translated(self):
        return self.is_hvac_translated

    def get_is_dhw_translated(self):
        return self.is_dhw_translated

    def set_heating_distribution_type(self, val):
        self.heating_distribution_type = val

    def get_heating_distribution_type(self):
        return self.heating_distribution_type

    def set_ac_hp_distribution_type(self, val):
        self.ac_hp_distribution_type = val

    def get_ac_hp_distribution_type(self):
        return self.ac_hp_distribution_type

    def set_suppl_heating_distribution_types(self, val):
        # Note that val gets passed here as a list already
        self.suppl_heating_distribution_types = val

    def get_suppl_heating_distribution_types(self):
        return self.suppl_heating_distribution_types

    def set_flue_diameters(self, val):
        self.flue_diameters = [*self.flue_diameters, val]

    def get_flue_diameters(self):
        return self.flue_diameters

    # tracking hvac system ids

    def __getid__(self, key):
        return self.system_ids.get(key, key)

    def __setid__(self, key, newvalue):
        self.system_ids[key] = newvalue

    def set_system_id(self, obj):
        for key in obj.keys():
            self.__setid__(key, obj[key])

    def get_system_id(self, key, default=None):
        value = self.__getid__(key)

        if value == key:
            return default
        else:
            return value

    def set_results(self, h2k_dict={}):
        file_results = (
            h2k_dict.get("HouseFile", {}).get("AllResults", {}).get("Results", [])
        )

        if isinstance(file_results, list):
            for res in file_results:
                house_code = res.get("@houseCode", "")
                upgrade_case = "@type" in res.keys()

                if (
                    house_code == "UserHouse" or "@houseCode" not in res.keys()
                ) and not (upgrade_case):
                    self.results = {
                        **self.results,
                        "General": res,
                    }

                elif house_code == "SOC" and not (upgrade_case):
                    self.results = {
                        **self.results,
                        "SOC": res,
                    }

                elif house_code == "Reference" and not (upgrade_case):
                    self.results = {
                        **self.results,
                        "Reference": res,
                    }

        return

    def get_results(self, res_type=""):
        results = {}
        if res_type == "":
            # when results type isn't specified, we assume we're looking for the base results
            # Attempt to return SOC results, and if they're not present return general mode.
            results = self.results.get("SOC", self.results.get("General", {}))

        else:
            results = self.results.get(res_type, {})

        return results
