from pymongo import MongoClient
import json
from tqdm import tqdm
import ast
import tiktoken
import hashlib
import os
from deepseek_v3_tokenizer.deepseek_tokenizer import token_number
prompt = """
    Role: You are a smart contract Architect and Requirements Engineering Expert. You will be given a smart contracts, a user story, a set of state variables in the contract
    and a set of function with their checks. Your task is to analyze the contract and generate a domain model which describe the isolation of the state variables in the contract.

    Instructions:
    1. Identify Actors
    - Identify the main actors in the contract (e.g., users, external contracts).
    - Determine the interactions between these actors and the contract.
    2. Code Analysis
    - Inline all inherited contracts to derive a complete codebase view.
    - Identify read/write isolation needs according to the actors and their interactions.
        · Write Isolation: How variables restrict write access for different actors (i.e., Access Control).
        · Read Isolation: How variables restrict read access for different actors (i.e., Encrypted Data).
    - Review the checks in the functions provided in the Function Checks section to understand the conditions under which state variables can be modified or accessed.
    3. Domain Models
    For each state variable in the contract, extract the isolation requirements:
    - Focus on the state isolation of the contract (write/read isolation):
        - Write Isolation:
            · How variables restrict write access for different actors (i.e., Access Control).
        - Read Isolation:
            · How variables restrict read access for different actors (i.e., Encrypted Data).
    - Note that you should include all state variables provided in the state variable section.
    - When handling constants of address type (especially contract addresses), ensure that you have consider implementation accounts for the Write/Read isolation. 
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
    7. Output Format
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
    The contract is <Contract>\n  \n</Contract>
    The state variables are <State Variables>\n  \n</State Variables>
    The transition graph is <User Story>\n  \n</User Story>
    The function signature is <Function Checks>\n  \n\</Function Checks>  
    """
def truncate_token(text: str, model: str = 'o3', max_token=128000) -> int:
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
    root_path='/home/liuhan/utils_download/most_unrelated'
    all_tokens = 0
    for file in tqdm(os.listdir(root_path)):
        if file.endswith('.sol'):
            with open(os.path.join(root_path,file),'r') as f:
                code=f.read()
            usr_path = os.path.join(root_path, file.replace('.sol', '_1user.txt'))
            with open(usr_path, 'r') as f:
                usr = f.read()
            check_path = os.path.join(root_path, file.replace('.sol', '_4condition.json'))
            with open(check_path, 'r') as f:
                func = json.load(f)

            func = {k: v for k, v in func.items() if v not in (None, '', [], {})}
            func_str = str(func)
            state_path = os.path.join(root_path, file.replace('.sol', '_state.txt'))
            with open(state_path, 'r') as f:
                state = f.read()
            # print(token_number(stg))
            all= code + '\n\n' + usr + '\n\n'+ func_str + '\n\n' + state_path
            # len_tokens = token_number(all)
            code, len_tokens = truncate_token(all)
            all_tokens += len_tokens
            if len_tokens > 63500:
                print(f"File {file} exceeds token limit: {len_tokens} tokens")
    print(f"Total tokens across all files: {all_tokens}")
            # Uncomment the following lines if you want to save the truncated code
            # with open(file_path, 'w') as f:
            #     f.write(code)



    # client = MongoClient("mongodb://shuaicpu5.cse.ust.hk:27017/")
    # collection_source=client['contracts']['top_contracts']
    # # 查询MongoDB集合中的所有文档
    # documents = collection_source.find({'stg':{'$exists':True}},{'code':1,'stg':1})
    # all_contracts = []
    # cou=0
    # cou2=0
    # all_hashs=set()
    # for doc in tqdm(documents):
    #     code=doc['code']
    #     stg=doc['stg']
    #     id=doc['_id']
    #     if code=='':
    #         continue
    #     code_hash=hashlib.sha256(code.encode()).hexdigest()
    #     if code_hash in all_hashs:
    #         continue
    #     all_hashs.add(code_hash)
    #     # collection_source.update_one({'_id': id}, {'$set': {'used': True}})
    #     all_contracts.append(code+'\n\n'+stg)
    # print(len(all_contracts))
    # for code in tqdm(all_contracts):
    #     _, len_tokens=truncate_token(code)
    #     cou+=len_tokens
    # print((cou/1000000)*0.40)
    # cou2 = 0
    # path="/home/liuhan/utils_download/most_unrelated"
    # for file in tqdm(os.listdir(path)):
    #     file_path = os.path.join(path, file)
    #     with open(file_path, 'r') as f:
    #         code = f.read()
    #     code, len_tokens = truncate_token(code)
    #     cou2 += len_tokens
    # print("Total tokens:", cou2)
    # print("Total cost in USD:", (cou2 / 1000000) * 0.035)