import re
import pandas as pd
import os
import json
import difflib
from unidecode import unidecode

def get_numbers_and_provinces(file_path=None):
    if file_path is None:
        file_path = os.path.join(os.path.dirname(__file__), "..", "resources", "weather", "h2k_weather_names.txt")
    # Define a dictionary mapping province names to their codes
    prov_terr_codes = {
        "BRITISH COLUMBIA": "BC",
        "ALBERTA": "AB",
        "SASKATCHEWAN": "SK",
        "MANITOBA": "MB",
        "ONTARIO": "ON",
        "NEW BRUNSWICK": "NB",
        "NOVA SCOTIA": "NS",
        "QUEBEC": "QC",
        "PRINCE EDWARD ISLAND": "PE",
        "NEWFOUNDLAND AND LABRADOR": "NL",
        "YUKON": "YT",
        "NORTHWEST TERRITORIES": "NT",
        "NUNAVUT": "NU",
    }
    
    # Load the list of CWEC files from a JSON file. This is from the btap weather library
    # https://github.com/canmet-energy/btap_weather/blob/main/historic_weather_filenames.json
    weather_library = "historic"
    with open(
        os.path.join(
            os.path.dirname(__file__), "..", "resources", "weather", "historic.json"
        ),
        "r",
    ) as f:
        canadian_cwec_files = json.load(f)
    
    # Open and read the weather names file
    with open(file_path, 'r') as file:
        # Read the first line to get the number of cities and provinces
        first_line = file.readline().strip()
        numbers = first_line.split()
        number_of_cities = int(numbers[0])
        number_of_provinces = int(numbers[1])
        
        # Read the provinces in English
        provinces_english = []
        while len(provinces_english) < number_of_provinces:
            line = file.readline().strip()
            provinces = re.split(r'\s{2,}', line)
            provinces_english.extend(provinces)
            
        # Read the province-city mapping
        provinces_city_map = []
        while len(provinces_city_map) < number_of_cities:
            line = file.readline().strip()
            map = re.split(r'\s{2,}', line)
            provinces_city_map.extend(map)
            
        # Read the cities in English
        cities_english = []
        while len(cities_english) < number_of_cities:
            line = file.readline().strip()
            map = re.split(r'\s{3,}', line)
            cities_english.extend(map)
            
        # Read the provinces in French
        provinces_french = []
        while len(provinces_french) < number_of_provinces:
            line = file.readline().strip()
            provinces = re.split(r'\s{2,}', line)
            provinces_french.extend(provinces)
        
        # Read the cities in French
        cities_french = []
        while len(cities_french) < number_of_cities:
            line = file.readline().strip()
            map = re.split(r'\s{3,}', line)
            cities_french.extend(map)
            
    # Print the extracted data for verification
    print(f"Number of cities: {number_of_cities}")
    print(f"Number of french cities: {len(cities_french)}")
    print(f"Number of provinces: {number_of_provinces}")
    print(f"Number of french provinces: {len(provinces_french)}")
    print(f"Number of provinces city map: {len(provinces_city_map)}")
    print(f"Number of english cities: {len(cities_english)}")
    print(f"Number of english provinces: {len(provinces_english)}")
    
    # Create a DataFrame with the extracted data
    city_df = pd.DataFrame({
        'provinces_city_map': provinces_city_map,
        'cities_english': cities_english,
        'cities_french': cities_french
    })
    
    # Convert the provinces_city_map column to integers
    city_df['provinces_city_map'] = city_df['provinces_city_map'].astype(int)

    # Create a DataFrame for provinces
    province_df = pd.DataFrame({
        'provinces_english': provinces_english,
        'provinces_french': provinces_french
    })
    
    # Add an index column to the DataFrame
    province_df.index += 1
    city_df.index += 1
    
    # Merge the two DataFrames on the index column from province_df and the provinces_city_map column from city_df
    merged_df = city_df.merge(province_df, left_on='provinces_city_map', right_index=True, how='left')
    print(merged_df)
    
    # Apply unidecode to the provinces_english and cities_english columns. To remove accents from the strings
    merged_df['provinces_english'] = merged_df['provinces_english'].apply(unidecode)
    merged_df['cities_english'] = merged_df['cities_english'].apply(unidecode)
    
    # Define the types of historic weather files to look for. Only do this for CWEC2020.zip types for now.
    historic_types = [
        "CWEC2020.zip",
    ]

    # Create a new empty DataFrame to store the results
    new_df = pd.DataFrame()
    
    # Iterate over each province
    for province in prov_terr_codes:
        # Filter the merged DataFrame for the current province
        filtered_df = merged_df[merged_df['provinces_english'] == province]
        
        # Filter the list of CWEC files for the current province
        filtered_cwec_files_by_province = [file for file in canadian_cwec_files if f"CAN_{prov_terr_codes[province]}" in file]
        
        # Iterate over each historic type
        for historic_type in historic_types:
            # Filter the list of CWEC files for the current historic type
            filtered_cwec_files = [file for file in filtered_cwec_files_by_province if historic_type in file]
            print(historic_type)
            
            # Find the closest match for each city in the filtered DataFrame
            filtered_df[historic_type] = filtered_df.apply(
                lambda x: difflib.get_close_matches(
                    f"CAN_{prov_terr_codes[unidecode(x['provinces_english']).upper()]}_{unidecode(x['cities_english'])}_{historic_type}".lower(),
                    filtered_cwec_files, n=1, cutoff=0.1
                )[0], axis=1
            )
        
        # Concatenate the filtered DataFrame to the new DataFrame
        new_df = pd.concat([new_df, filtered_df], ignore_index=True)
    
    # Write the new DataFrame to a CSV file
    new_df.to_csv("h2k_weather_names.csv", index=False)
    
    return number_of_cities, number_of_provinces, provinces_english, provinces_city_map, cities_english, provinces_french, cities_french

# Main Code Call. I like making functions for everything by default in case it can be reused.
get_numbers_and_provinces()