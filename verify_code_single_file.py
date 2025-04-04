from pymongo import MongoClient
import json
from tqdm import tqdm
import shutil
import os
import subprocess
if __name__ == "__main__":
    client = MongoClient("mongodb://shuaicpu5.cse.ust.hk:27017/")
    collection_source=client['contracts']['top_contracts']
    # 查询MongoDB集合中的所有文档
    documents = collection_source.find({'source':{'$ne':''}},{})
    all_contracts = []
    cou=0
    for doc in documents:
        id=doc['_id']
        source=doc['source']
        if source.startswith('{'):
            continue
        all_contracts.append({
                '_id': id,
                'code': source,
            })
    # with open('all_contracts.json', 'w') as f:
    #     json.dump(all_contracts, f, indent=4)
    for arg in tqdm(all_contracts):
        collection_source.update_one({'_id': arg['_id']}, {'$set': {'code': arg['code']}})
        # process_multifile(arg)
    # print(cou)
    # path,contract_path,flatten_path=export_multifile(all_contracts[0],'/home/liuhan/utils_download/solc_source_code')
    # forge_init(path,contract_path, flatten_path, viair=True)
