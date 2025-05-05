import os
import re
import json
from openai import OpenAI
from tqdm import tqdm
import httpx
import faiss
import numpy as np
import tiktoken
from pymongo import MongoClient
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
    temp_cou=3
    client=MongoClient("mongodb://shuaicpu5.cse.ust.hk:27017/")
    collection_source=client['contracts']['top_contracts']
    docs=collection_source.find({'code':{'$exists':True}},{'code_hash':1,'embedding':1,'code':1})
    embeddings=[]
    all_hashs=set()
    codes=[]
    for doc in tqdm(docs):
        code=doc['code']
        code_hash=doc['code_hash']
        embedding=doc['embedding']
        if code_hash in all_hashs:
            continue
        all_hashs.add(code_hash)
        codes.append(code)
        embeddings.append(embedding)
    dimension = len(embeddings[0])
    index = faiss.IndexFlatL2(dimension)
    index.add(np.array(embeddings).astype('float32'))
    with open(f'/home/liuhan/utils_download/test_contract{temp_cou}.sol','r') as f:
        code=f.read()
    code=process_code(code)
    code, len_tokens=get_token_count(code)
    code_embedding=get_openai_embedding(code)
    code_embedding = np.array(code_embedding).astype('float32')
    code_embedding = np.reshape(code_embedding, (1, -1))
    k = 10
    D, I = index.search(code_embedding, k)
    codes = [codes[i] for i in I[0]]
    cou=0
    os.makedirs(f"/home/liuhan/utils_download/similar_code{temp_cou}", exist_ok=True)
    for code in codes:
        with open(f"/home/liuhan/utils_download/similar_code{temp_cou}/contract_{cou}.sol",'w') as f:
            f.write(code)
        cou+=1