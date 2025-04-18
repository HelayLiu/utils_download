import requests
import json
import time
import csv
from config import API_KEY
# 替换为你的 Dune API Key

QUERY_ID = '4082551'  # 查询的唯一ID
CHAIN='fantom' # 链名称
RESULT_LIMIT = 10000000

# Dune API endpoint for querying results in CSV format
url = f"https://api.dune.com/api/v1/query/{QUERY_ID}/results/csv?limit={RESULT_LIMIT}"

# Headers with the API key for authentication
headers = {
    "x-dune-api-key": API_KEY
}

response = requests.get(url, headers=headers)

# Check if the request was successful
if response.status_code == 200:
    # Parse CSV data
    csv_data = response.text.splitlines()
    
    # Create a dictionary to hold the JSON data (address: balance)
    address_balance_dict = {}
    
    # Use the csv.DictReader to convert CSV rows into dictionaries
    csv_reader = csv.DictReader(csv_data)
    
    # Iterate over each row and add it to the dictionary
    for row in csv_reader:
        # Convert 'balance' to float and add it to the dictionary
        if not isinstance(row['contract_address'], str) or row['contract_address']=='' or row['contract_address']=='<nil>':
            continue
        try:
            address_balance_dict[row['contract_address']] = row['transaction_count']
        except ValueError:
            address_balance_dict[row['contract_address']] = 0
            print(f"Failed to convert balance to float: {row['transaction_count']}")
    print(len(address_balance_dict))
    # Save the dictionary to a JSON file
    json_file_path = f"top2000_trans_{CHAIN}.json"
    with open(json_file_path, "w") as json_file:
        json.dump(address_balance_dict, json_file, indent=4)
    
    print(f"Address:Balance JSON successfully saved to {json_file_path}")
else:
    print(f"Failed to fetch data: {response.status_code}")
    print(response.text)