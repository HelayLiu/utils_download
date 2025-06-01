from pymongo import MongoClient
import json
from tqdm import tqdm
import ast
import tiktoken
import hashlib
import os
def truncate_token(text: str, model: str = 'gpt-4o-mini', max_token=128000) -> int:
    try:
        encoding = tiktoken.encoding_for_model(model)
    except KeyError:
        encoding = tiktoken.get_encoding("cl100k_base")
    tokens = encoding.encode(text)
    tokens = tokens[-max_token:]
    len_tokens = len(tokens)
    truncated_code = encoding.decode(tokens)
    return truncated_code, len_tokens
    
if __name__ == "__main__":
    # client = MongoClient("mongodb://shuaicpu5.cse.ust.hk:27017/")
    # collection_source=client['contracts']['top_contracts']
    # # 查询MongoDB集合中的所有文档
    # documents = collection_source.find({'code':{'$exists':True}},{'code':1})
    # all_contracts = []
    # cou=0
    # cou2=0
    # all_hashs=set()
    # for doc in tqdm(documents):
    #     code=doc['code']
    #     if code=='':
    #         continue
    #     code_hash=hashlib.sha256(code.encode()).hexdigest()
    #     if code_hash in all_hashs:
    #         continue
    #     all_hashs.add(code_hash)
    #     all_contracts.append(code)
    # print(len(all_contracts))
    # for code in tqdm(all_contracts):
    #     _, len_tokens=truncate_token(code)
    #     cou+=len_tokens
    # print((cou/1000000)*0.15)
    cou2 = 0
    path="/home/liuhan/utils_download/most_unrelated"
    for file in tqdm(os.listdir(path)):
        file_path = os.path.join(path, file)
        with open(file_path, 'r') as f:
            code = f.read()
        code, len_tokens = truncate_token(code)
        cou2 += len_tokens
    print("Total tokens:", cou2)
    print("Total cost in USD:", (cou2 / 1000000) * 0.035)