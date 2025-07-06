import requests
import re
import json
from openai import OpenAI
from tqdm import tqdm
import httpx
import os
import tiktoken
from config import OPENAI_API_KEY
proxy_1 = "http://127.0.0.1:20171"
# 配置 HTTP 代理地址
proxies = {
    "http": "http://127.0.0.1:20171",
    "https": "http://127.0.0.1:20171",
}
from pymongo import MongoClient
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


def summarize_by_LLMs(desc,state,graph,model="gpt-4.1-mini"):
    role_content=f"""
    Role: You are a Smart Contract Architect and an expert in Requirements Engineering. You will be provided with a smart contract, its associated state variables, and a corresponding state variable transition graph. This graph is a directed structure in which each node represents a distinct configuration of all the contract’s state variables, effectively reflecting a particular state of the contract. Transitions between these configurations are represented by edges, each of which is triggered by a function call. Depending on the specific conditions or parameters of the function call, different transitions may occur, resulting in changes to the contract's state. 
    Now your task is to analyze a given smart contract and generate User Stories and Domain Models focused on state isolation across users and contracts, i.e., how state variables are isolated for different actors (users, external contracts) in read and write operations.

    Instructions:
    1. Identify Actors
    - Identify the main actors in the contract (e.g., users, external contracts).
    - Determine the interactions between these actors and the contract.
    2. Code Analysis
    - Inline all inherited contracts to derive a complete codebase view.
    - Identify state variables, their visibility (public/private), and scopes:
        · User-specific: Variables tied to individual users.
        · Contract-specific: Variables restricted to cross-contract interactions.
    - Identify read/write isolation needs:
        · Write Isolation: How variables restrict write access for different actors (i.e., Access Control).
        · Read Isolation: How variables restrict read access for different actors (i.e., Encrypted Data).
    3. User Stories Summarize
    - Summarize the contract's purpose and use cases, emphasizing:
        · What is the contract doing and how is it being used.
        · How is state isolation enforced across users and contracts.
    - Example: 
    For a voting system:
        · This contract is a voting system where users can cast votes, and their preferences are stored securely.
        · As a user, I want my encrypted voting preferences isolated from others, even though the blockchain is public.
        · As an owner, I want to ensure that only authorized users can access to sensitive data.
    For a token minting system:
        · This contract is a token minting system where users can mint tokens, and their balances are stored securely.
        · As a whitelisted, I want to mint tokens for myself or other users I want.
        · As a user, I want to ensure that my token balance is isolated from others, to prevent unauthorized access.
        · As the contract owner, I want to restrict token minting to authorized users only.
    5. Domain Models
    - Provide a state variable overview.
    - Focus on the state isolation of the contract (write/read isolation):
        - Write Isolation:
            · How variables restrict write access for different actors (i.e., Access Control).
        - Read Isolation:
            · How variables restrict read access for different actors (i.e., Access Control).
    - Example:
    For a token minting system:
        _balances: mapping(address => uint256) private _balances;
            · Write restricted to the user themselves or the owner of the contract.
            · Read restriction to None.
        allowedMinter: mapping(address => bool) private _allowedMinters;
            · Write restricted to the contract owner.
            · Read restriction to None.
        allowance: mapping(address => mapping(address => uint256)) private _allowance;
            · Write restricted to the user themselves or the owner of the contract.
            · Read restriction to None.
    For a lucky number contract:
        _luckyNumber: uint256 private _luckyNumber;
            · Write restricted to the contract owner.
            · Read restricted to the contract owner and stored as a hash for integrity.
        _userPreferences: mapping(address => bytes32) private _userPreferences;
            · Write restricted to the user themselves or the contract owner.
            · Read restricted to the user themselves and stored as a hash for integrity.
    6. Output Format
    - Structure your response as: 
        The User Stories are:  
        <User Stories>  
        [Concise bullet points highlighting state isolation use cases]  
        </User Stories>  

        The Domain Models are:  
        <Domain Models>  
        - [State Variable 1]:
            · Write restricted to [Actor/Contract Type] or Write restricted to [None].
            · Read restricted to [Actor/Contract Type and stored as a hash for integrity] or Read restricted to [None].
            
        - [State Variable 2]:
            · Write restricted to [Actor/Contract Type] or Write restricted to [None].
            · Read restricted to [Actor/Contract Type and stored as a hash for integrity] or Read restricted to [None].
        ...
        </Domain Models>
    - Do not include any other information or explanations, just the User Stories and Domain Models.
    """


    try:
        client= OpenAI(api_key=OPENAI_API_KEY,http_client=httpx.Client(proxy=proxy_1))
        response = client.chat.completions.create(
                            model=model,
                            messages=[
                                {"role": "system", "content": role_content},
                                {"role": "user", "content": f'''The contract is <Contract> {desc} </Contract>\n
                                        The state variables are <State Variables> {state} </State Variables>\n
                                        The transition graph is <Transition Graph> {graph} </Transition Graph>'''},
                            ],
                            temperature = 0
                        )
    except Exception as e:
        print('Error in response')
        print(e)
        return None, 0 ,0
    return response.choices[0].message.content, response.usage.prompt_tokens, response.usage.completion_tokens

if __name__ == "__main__":
    # temp_cou=2
    # root_path = f"/home/liuhan/utils_download/similar_code{temp_cou}"
    # os.makedirs(root_path, exist_ok=True)
    # cou=0
    # for file in tqdm(os.listdir(root_path)):
    #     if file.endswith('.sol'):
    #         cou+=1
    #         with open(os.path.join(root_path,file),'r') as f:
    #             code=f.read()
    #         code, len_tokens=truncate_token(code,max_token=100000)
    #         file_name = file.split('.')[0]
    #         graph_path = os.path.join(root_path, f"{file_name}_setting.json")
    #         with open(graph_path, 'r') as f:
    #             settings = json.load(f)
    #         graph = settings.get('stg', '')
    #         re_try=0
    #         while True:

    #             requirement=summarize_by_LLMs(code,graph)
    #             if requirement is None:
    #                 re_try+=1
    #                 if re_try>10:
    #                     print("Error in response")
    #                     break
    #                 continue
    #             else:
    #                 break
    #         with open(os.path.join(root_path,f"{file}_gpt41mini0.txt"),'w') as f:
    #             f.write(requirement)
    
    client = MongoClient("mongodb://shuaicpu5.cse.ust.hk:27017/")
    collection_source=client['contracts']['top_contracts']
    # 查询MongoDB集合中的所有文档
    documents = collection_source.find({'used_has_state':{'$exists':True}},{'code':1,'stg':1,"all_state":1,"_id":1,'models':1})
    all_contracts = []
    documents_list = list(documents)
    all_in_tokens = 0
    all_out_tokens = 0
    for doc in tqdm(documents_list):
        if 'models' in doc and doc['models'] is not None and doc['models'] != '':
            continue

        code = doc.get('code', '')
        graph = doc.get('stg', '')
        state = doc.get('all_state', '')
        if not code:
            continue
        code, len_tokens = truncate_token(code, max_token=100000)
        re_try = 0
        while True:
            res,in_tokens,out_tokens = summarize_by_LLMs(code, state, graph)
            all_in_tokens += in_tokens
            all_out_tokens += out_tokens
            if res is None:
                re_try += 1
                if re_try > 50:
                    print("Error in response")
                    break
                continue
            else:
                break
        if res:
            collection_source.update_one(
                {'_id': doc['_id']},
                {'$set': {'models': res}}
            )
        total_cost = (in_tokens/1000000) * 0.4 + (out_tokens/1000000) * 1.6
        if total_cost > 100:
            print(f"Total cost exceeds $100 for contract {doc['_id']}: {total_cost}")
            break
    print(f"Total input tokens: {all_in_tokens}")
    print(f"Total output tokens: {all_out_tokens}")
    print(f"Total cost in USD: {(all_in_tokens / 1000000) * 0.4 + (all_out_tokens / 1000000) * 1.6}")