from pymongo import MongoClient
import json
from tqdm import tqdm
import ast
import tiktoken
import hashlib
import os
from deepseek_v3_tokenizer.deepseek_tokenizer import token_number
prompt = """
Role: You are a smart contract Architect and Requirements Engineering Expert. You will be given a smart contracts, a state variable transition graph (STG) of the contract, and a set of function signature.  STG is a directed graph where each node represents a situation of all the state variables of the contract, and each edge represents a transition between two situations. The transition is triggered by a function call, and for each different condition of the function call, there is a different transition. 
    Now your task is to analyze a given smart contract and generate User Stories, Domain Models and checks of each given function focused on state isolation.

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
        · What is the contract doing and how it is used.
        · How state isolation is enforced across users and contracts.
    - Example: 
    For a voting system:
        This contract is a voting system where users can cast votes, and their preferences are stored securely.
        · As a user, I want my encrypted voting preferences isolated from others, even though the blockchain is public.
        · As a owner, I want to ensure that only authorized users can access sensitive data.
        This contract is a token minting system where users can mint tokens, and their balances are stored securely.
    For a token minting system:
        · As a whitelister, I want to mint tokens for myself or other users I wanted.
        · As a user, I want to ensure that my token balance is isolated from others, preventing unauthorized access.
        · As a contract owner, I want to restrict token minting to authorized users only.
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
    6. Specific Checks in Functions
    - For each given function in the contract, extract the specific checks that ensure state isolation:
    - Format:
        function <function_signature> returns (<return_type>):[
        {{
            "specific_checks": "<condition>",
            "involved_variables":  ["<variable1>", "<variable2>"],
            "descriptions": "<description of the check>",
            "references": ["<state_variable1>", "<state_variable2>"]
        }}
        ]
    - Example:
        function mint(address, uint256) returns (bool):[
        {{
            "specific_checks": "msg.sender == owner",
            "involved_variables":  ["msg.sender"],
            "descriptions": "Verify msg.sender == owner to enforce write access to _balances.",
            "references": ["_balances"]
        }}
        ]
    7. Output Format
    Structure your response as: 
    The general User Stories are:  
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

    The specific checks in functions are:
    <Specific Checks in Functions>
    <Function Signature 1>:[
    {{
            "specific_checks": "<condition>",
            "involved_variables":  ["<variable1>", "<variable2>"],
            "descriptions": "<description of the check>",
            "references": ["<state_variable1>", "<state_variable2>"]
    }},
    ...
    ]
    <Function Signature 2>:[specific_checks]
    ...
    </Specific Checks in Functions>"""
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
    # path='/home/liuhan/utils_download/most_unrelated'
    # all_tokens = 0
    # for file in tqdm(os.listdir(path)):
    #     if file.endswith('.sol'):
    #         file_path = os.path.join(path, file)
    #         with open(file_path, 'r') as f:
    #             code = f.read()
    #         config_path = os.path.join(path, file.replace('.sol', '.json'))
    #         with open(config_path, 'r') as f:
    #             config = json.load(f)
    #         # print(token_number(code))
    #         stg= config.get('stg', '')
    #         function_path = os.path.join(path, file.replace('.sol', '_public_functions.json'))
    #         with open(function_path, 'r') as f:
    #             func = json.load(f)
    #         func = [ f"function {func_sig}" for func_sig in func ]
    #         func_str = ' \n '.join(func)
    #         # print(token_number(stg))
    #         all= code + '\n\n' + stg + '\n\n'+ prompt + '\n\n' + func_str
    #         len_tokens = token_number(all)
    #         all_tokens += len_tokens
    #         if len_tokens > 63500:
    #             print(f"File {file} exceeds token limit: {len_tokens} tokens")
    # print(f"Total tokens across all files: {all_tokens}")
            # Uncomment the following lines if you want to save the truncated code
            # with open(file_path, 'w') as f:
            #     f.write(code)
    client = MongoClient("mongodb://shuaicpu5.cse.ust.hk:27017/")
    collection_source=client['contracts']['top_contracts']
    # 查询MongoDB集合中的所有文档
    documents = collection_source.find({'stg':{'$exists':True}},{'code':1,'stg':1})
    all_contracts = []
    cou=0
    cou2=0
    all_hashs=set()
    for doc in tqdm(documents):
        code=doc['code']
        stg=doc['stg']
        id=doc['_id']
        if code=='':
            continue
        code_hash=hashlib.sha256(code.encode()).hexdigest()
        if code_hash in all_hashs:
            continue
        all_hashs.add(code_hash)
        # collection_source.update_one({'_id': id}, {'$set': {'used': True}})
        all_contracts.append(code+'\n\n'+stg)
    print(len(all_contracts))
    for code in tqdm(all_contracts):
        _, len_tokens=truncate_token(code)
        cou+=len_tokens
    print((cou/1000000)*0.40)
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