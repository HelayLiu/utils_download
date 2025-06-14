from pymongo import MongoClient
import json
from tqdm import tqdm
import shutil
import os
import subprocess
if __name__ == "__main__":
    client=MongoClient("mongodb://shuaicpu5.cse.ust.hk:27017/")
    collection_source=client['contracts']['top_contracts']
    docs=collection_source.find({'used':True},{'_id':1,'code':1})
    for doc in tqdm(docs):
        _id=doc['_id']
        code=doc['code']
        save_path=os.path.join('/home/liuhan/saved_contracts',f"{_id}.sol")
        if os.path.exists(save_path):
            continue
        with open(save_path,'w') as f:
            f.write(code)