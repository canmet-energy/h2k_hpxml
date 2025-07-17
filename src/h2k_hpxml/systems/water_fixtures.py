import math

from ..utils import obj, h2k


# Water fixtures include "shower head" and "faucet"
# Low flow if rate is <= 2gpm
# H2k defines these in a fairly statis manner, all that's converted is the flowrates of the faucets
# Note that total amounts of daily/annual water consumption is handled in the base load translation
def get_water_fixtures(h2k_dict, model_data):

    shower_flow_rate = h2k.get_number_field(h2k_dict, "shower_head_flow_rate")
    faucet_flow_rate = h2k.get_number_field(h2k_dict, "water_faucet_flow_rate")

    hpxml_water_fixture = [
        {
            "SystemIdentifier": {
                "@id": "WaterFixture1",
            },
            "WaterFixtureType": "shower head",
            "FlowRate": shower_flow_rate,
        },
        {
            "SystemIdentifier": {
                "@id": "WaterFixture2",
            },
            "WaterFixtureType": "faucet",
            "FlowRate": faucet_flow_rate,
        },
    ]

    return hpxml_water_fixture
