import requests
import re
import json
from openai import OpenAI
from tqdm import tqdm
import httpx
import os
import tiktoken
from config import *
import time
from datetime import datetime
proxy_1 = "http://127.0.0.1:20171"
# 配置 HTTP 代理地址
proxies = {
    "http": "http://127.0.0.1:20171",
    "https": "http://127.0.0.1:20171",
}
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


def summarize_by_LLMs(desc,graph,func,model="deepseek-reasoner"):
    role_content=f"""
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
    </Specific Checks in Functions>
    """

    usr_content=f"""
    The contract is <Contract>\n {desc} \n</Contract>
    The transition graph is <Transition Graph>\n {graph} \n</Transition Graph>
    The function signature is <Function Signature>\n {func} \n\</Function Signature>     
    """
    try:
        client= OpenAI(api_key=DEEPSEEK_API_KEY, base_url="https://api.deepseek.com")
        response = client.chat.completions.create(
                            model=model,
                            messages=[
                                {"role": "system", "content": role_content},
                                {"role": "user", "content": usr_content},
                            ],
                            stream=True,
                            max_tokens=64000
                        )
        total_tokens_in = 0
        total_tokens_out = 0
        reasoning_content = ""
        content = ""
        for chunk in response:
            if chunk.choices[0].delta.reasoning_content:
                reasoning_content += chunk.choices[0].delta.reasoning_content
            if chunk.choices[0].delta.content:
                content += chunk.choices[0].delta.content
            if chunk.usage:
                if chunk.usage.prompt_tokens:
                    total_tokens_in += chunk.usage.prompt_tokens
                if chunk.usage.completion_tokens:
                    total_tokens_out += chunk.usage.completion_tokens
        res = f"<THINKING_CONTENT>\n{reasoning_content}\n</THINKING_CONTENT>\n<RESPONSE>\n{content}\n</RESPONSE>"
        client.close()
    except Exception as e:
        print('Error in response')
        print(e)
        return None, None, None
    return res, total_tokens_in, total_tokens_out
def is_in_time_range(start_hour, start_minute, end_hour, end_minute):
    now = datetime.now()
    now_minutes = now.hour * 60 + now.minute
    start_minutes = start_hour * 60 + start_minute
    end_minutes = end_hour * 60 + end_minute
    return start_minutes <= now_minutes <= end_minutes
if __name__ == "__main__":
    root_path = f"/home/liuhan/utils_download/most_unrelated"
    for file in tqdm(os.listdir(root_path)):
        if file.endswith('.sol'):
            while True:
                if is_in_time_range(0, 30, 8, 20):
                    break
                print("Waiting for the time range to be valid...")
                time.sleep(60)
            output_file = file.replace('.sol', '_deepseek_res.txt')
            if os.path.exists(os.path.join(root_path, output_file)):
                continue
            with open(os.path.join(root_path,file),'r') as f:
                code=f.read()
            config_path = os.path.join(root_path, file.replace('.sol', '.json'))
            with open(config_path, 'r') as f:
                config = json.load(f)
            stg= config.get('stg', '')
            function_path = os.path.join(root_path, file.replace('.sol', '_public_functions.json'))
            with open(function_path, 'r') as f:
                func = json.load(f)
            func = [ f"function {func_sig}" for func_sig in func ]
            func_str = ' \n '.join(func)
            # if func_str == '' or stg == '' or code == '':
            #     print(f"Error in {file}, func_str or stg is empty")
            #     continue
            for i in range(5):
                res,token_in,token_out= summarize_by_LLMs(code,stg,func_str)
                if res is not None:
                    print(f"Success in {file}, token_in: {token_in}, token_out: {token_out}")
                    break
            
            with open(os.path.join(root_path,output_file),'w') as f:
                f.write(res)
