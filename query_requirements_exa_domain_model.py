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
    Role: You are a smart contract developer and requirements engineering expert. You will be given a smart contracts a state variable transition graph of the contract, which is a directed graph where each node represents a situation of all the state variables of the contract, and each edge represents a transition between two situations. The transition is triggered by a function call, and for each different condition of the function call, there is a different transition. 
    Now your task is to analyze a given smart contract and generate User Stories and Domain Models focused on state isolation across users and contracts.

    Instructions:
    1. Identify Actors
    - Identify the main actors in the contract (e.g., users, external contracts).
    - Determine the interactions between these actors and the contract.
    2. Code Analysis
    - Inline all inherited contracts to derive a complete codebase view.
    - Identify state variables, their visibility (public/private), and scopes:
        · User-specific: Variables tied to individual users (e.g., balances, permissions).
        · Contract-specific: Variables restricted to cross-contract interactions.
    - Flag variables where blockchain transparency conflicts with privacy needs (e.g., sensitive user data stored publicly).
    - Consider consulting the transition graph to refine your understanding of the contract.
    3. User Isolation
    - Analyze how state variables enforce isolation between users:
        · Use of private/internal visibility or access control.
        · Data partitioning (e.g., mapping(address => ...)).
        · Encryption/hashing techniques to protect sensitive data (e.g., encrypted balances).
    4. Contract Isolation
    - Analyze how state variables prevent unintended cross-contract interference:
        · Encapsulation of variables used for external calls (e.g., address private externalContract).
        · Validation of inputs/outputs in cross-contract interactions.
        · Use of cryptographic proofs (e.g., Merkle proofs) to ensure data integrity.
    5. User Stories
    - Summarize the contract’s purpose and use cases, emphasizing:
        · How user-specific state isolation is enforced (e.g., per-user balances stored in mapping).
        · How cross-contract interactions avoid unintended state leakage.
    - Example: "As a user, I want my encrypted voting preferences isolated from others, even though the blockchain is public."
        · "As a owner, I want to ensure that only authorized users can access sensitive data."
        · "As a whitelister, I want to mint tokens for myself or other users I wanted."
    6. Domain Models
    - Provide a state variable overview.
    - Design models strictly reflecting state isolation:
        - Write Isolation:
            · How variables restrict write access for different actors.
            · Example:
                _balances: mapping(address => uint256) private _balances;
                - This mapping ensures that each user's balance is isolated and can only be modified by the user themselves or the owner of the contract.
                Domain Models should be:
                _balances: mapping(address => uint256) private _balances;
                    · Write restricted to the user themselves or the owner of the contract.
        - Read Isolation:
            · How variables restrict read access for different actors.
            · Example:
                _luckyNumber: uint256 private _luckyNumber;
                - This variable is private, ensuring that only the contract owner can read the lucky number, preventing other users from accessing it. Additionally, to ensure data integrity, it is stored as a hash (e.g., luckyNumber = keccak256(_luckyNumber)).
                Domain Models should be:
                _luckyNumber: uint256 private _luckyNumber;
                    · Read restricted to the contract owner and stored as a hash for integrity.
    7. Output Format
    Structure your response as: 
    The general User Stories are:  
    <User Stories>  
    [Concise bullet points highlighting state isolation use cases]  
    </User Stories>  

    The Domain Models are:  
    <Domain Models>  
    - [State Variable 1]:
        · Read restricted to [Actor/Contract Type and stored as a hash for integrity] or Read restricted to [None].
        · Write restricted to [Actor/Contract Type] or Write restricted to [None].
    - [State Variable 2]:
        · Read restricted to [Actor/Contract Type and stored as a hash for integrity] or Read restricted to [None].
        · Write restricted to [Actor/Contract Type] or Write restricted to [None].
    ...
    </Domain Models>
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
            with open(os.path.join(root_path,f"{file}_gpt4omini_withgraph_new.txt"),'w') as f:
                f.write(requirement)