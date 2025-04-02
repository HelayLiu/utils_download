from pymongo import MongoClient
import json
from tqdm import tqdm
import ast
import os

    
if __name__ == "__main__":
    client = MongoClient("mongodb://shuaicpu5.cse.ust.hk:27017/")
    collection_source=client['contracts']['top_contracts']
    # 查询MongoDB集合中的所有文档
    documents = collection_source.find({'source':{'$ne':''}},{})
    all_contracts = []
    cou=0
    for doc in documents:
        id=doc['_id']
        address=doc['address']
        chain_id=doc['chain_id']
        source=doc['source']
        if source.startswith('"') and source.endswith('"'):
            source=source[1:-1]
        collection_source.update_one({'_id': id}, {'$set': {'source': source}})
