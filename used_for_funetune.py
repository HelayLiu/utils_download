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


def summarize_by_LLMs(desc,graph,model="gpt-4o-mini-2024-07-18"):
    role_content=f"""
    Role: You are a smart contract Architect and Requirements Engineering Expert. You will be given a smart contracts a state variable transition graph of the contract, which is a directed graph where each node represents a situation of all the state variables of the contract, and each edge represents a transition between two situations. The transition is triggered by a function call, and for each different condition of the function call, there is a different transition. 
    Now your task is to analyze a given smart contract and generate User Stories and Domain Models focused on state isolation across users and contracts.

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
    - For each public function in the contract, extract the specific checks that ensure state isolation:
    - Example:
        function mint(address, uint256) returns (bool):[
        {{
            "potential_checks": "msg.sender == owner",
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
    <Function Signature 1>:[specific_checks]
    <Function Signature 2>:[specific_checks]
    ...
    </Specific Checks in Functions>
    """


    try:
        client= OpenAI(api_key=OPENAI_API_KEY,http_client=httpx.Client(proxy=proxy_1))
        response = client.chat.completions.create(
                            model=model,
                            messages=[
                                {"role": "system", "content": role_content},
                                {"role": "user", "content": f'''The contract is <Contract> {desc} </Contract>\n\n
                                        The transition graph is <Transition Graph> {graph} </Transition Graph>'''},
                            ],
                            temperature = 0,
                        )
    except Exception as e:
        print('Error in response')
        print(e)
        return None
    return response.choices[0].message.content

if __name__ == "__main__":
    temp_cou=3
    root_path = f"/home/liuhan/utils_download/similar_code{temp_cou}"
    os.makedirs(root_path, exist_ok=True)
    cou=0
    for file in tqdm(os.listdir(root_path)):
        if file.endswith('.sol'):
            cou+=1
            with open(os.path.join(root_path,file),'r') as f:
                code=f.read()
            code, len_tokens=truncate_token(code,max_token=100000)
            file_name = file.split('.')[0]
            graph_path = os.path.join(root_path, f"{file_name}_graph.txt")
            with open(graph_path, 'r') as f:
                graph = f.read()
            re_try=0
            while True:

                requirement=summarize_by_LLMs(code,graph)
                if requirement is None:
                    re_try+=1
                    if re_try>10:
                        print("Error in response")
                        break
                    continue
                else:
                    break
            with open(os.path.join(root_path,f"{file}_gpt4omini_withgraph_new1.txt"),'w') as f:
                f.write(requirement)
            break