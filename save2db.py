import os
from pymongo import MongoClient
import json
from tqdm import tqdm
client = MongoClient("mongodb://shuaicpu5.cse.ust.hk:27017/")
collection_source=client['contracts']['top_contracts']
chains = ['eth','bsc','arbi','avax','base','opt','poly','fantom']
for chain in chains:
    file_path=f'/home/liuhan/utils_download/top2000_trans_{chain}.json'
    if chain=='eth':
        chain_id='1'
    elif chain=='bsc':
        chain_id='56'
    elif chain=='arbi':
        chain_id='42161'
    elif chain=='avax':
        chain_id='43114'
    elif chain=='base':
        chain_id='8453'
    elif chain=='opt':
        chain_id='10'
    elif chain=='poly':
        chain_id='137'
    elif chain=='fantom':
        chain_id='250'
    else:
        chain_id='0'
    with open(file_path, 'r') as f:
        data = json.load(f)
    for address, trans in tqdm(data.items()):
        # Create a new document for each address
        doc = {
            'address': address,
            'trans_num': trans,
            'chain_id': chain_id,
            'chain': chain,
        }
        # Insert the document into the MongoDB collection
        collection_source.insert_one(doc)