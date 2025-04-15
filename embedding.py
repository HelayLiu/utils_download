
import json
import os

from tqdm import tqdm
from pymongo import MongoClient
import hashlib
from openai import OpenAI
import httpx
import tiktoken
from config import OPENAI_API_KEY
proxy_1 = "http://127.0.0.1:20171"
# 配置 HTTP 代理地址
proxies = {
    "http": "http://127.0.0.1:20171",
    "https": "http://127.0.0.1:20171",
}
def get_openai_embedding(text: str, model: str = "text-embedding-3-small") -> list:
    client= OpenAI(api_key=OPENAI_API_KEY,http_client=httpx.Client(proxy=proxy_1))
    response = client.embeddings.create(
        input=text,
        model=model
    )
    return response.data[0].embedding
def get_token_count(text: str, model: str = 'text-embedding-3-small', max_token=8000) -> int:
    try:
        encoding = tiktoken.encoding_for_model(model)
    except KeyError:
        encoding = tiktoken.get_encoding("cl100k_base")
    tokens = encoding.encode(text)
    tokens = tokens[-max_token:]
    len_tokens = len(tokens)
    truncated_code = encoding.decode(tokens)
    return truncated_code, len_tokens
def process_code(code):
    code = code.split('\n')
    new_code = []
    for code_line in code:
        code_line = code_line.strip()
        if code_line.startswith('//') or code_line.startswith('/*') or code_line.startswith('*'):
            continue
        if code_line.strip() == '':
            continue
        new_code.append(code_line)
    code = '\n'.join(new_code)
    return code

if __name__ == "__main__":
    client=MongoClient("mongodb://shuaicpu5.cse.ust.hk:27017/")
    collection_source=client['contracts']['top_contracts']
    docs=collection_source.find({'code':{'$exists':True}},{'_id':1,'code':1})
    codes={}
    code_hashs_id={}
    for doc in tqdm(docs):
        code=doc['code']
        code_hash=hashlib.sha256(code.encode()).hexdigest()
        id=doc['_id']
        if code_hash not in code_hashs_id:
            code_hashs_id[code_hash]=[id]
            codes[code_hash]=code
        else:
            code_hashs_id[code_hash].append(id)
    total_token_num=0
    for code_hash in tqdm(code_hashs_id):
        code=codes[code_hash]
        ids=code_hashs_id[code_hash]
        code=process_code(code)
        new_code,token_num=get_token_count(code)
        total_token_num+=token_num
        embedding=get_openai_embedding(new_code)
        for id in ids:
            collection_source.update_one({'_id': id}, {'$set': {'embedding': embedding}})
    print(f"Total token num: {total_token_num}")
    print(f"Total cost: {total_token_num/1000*0.00002}")