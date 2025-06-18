from pymongo import MongoClient
import json
from tqdm import tqdm
import ast
import os

    
if __name__ == "__main__":
    client = MongoClient("mongodb://shuaicpu5.cse.ust.hk:27017/")
    collection_source=client['contracts']['top_contracts']
    # 查询MongoDB集合中的所有文档
    documents = collection_source.find({'all_state':{'$exists':True}},{})
    all_contracts = []
    cou=0
    for doc in tqdm(documents):
        id=doc['_id']
        all_state = doc['all_state']
        if all_state is None or all_state == '':
            continue
        cou += 1
        # address=doc['address']
        # chain_id=doc['chain_id']
        # source=doc['source']
        # if source.startswith('"') and source.endswith('"'):
        #     source=source[1:-1]
        collection_source.update_one({'_id': id}, {'$set': {'used_has_state': True}})
print(f"Processed {cou} contracts with state variables.")
