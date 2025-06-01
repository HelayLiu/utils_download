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

def summarize_by_LLMs(desc,examples,model="gpt-4.1-mini"):
    role_content=f"""
    You are a smart contract developer expert. Given User Stories, your task is to derive Domain Models that strictly enforce isolation of read/write operations on state variables across users and contracts, with cryptographic integrity guarantees. You will be provided with several examples of Domain Models and their corresponding User Stories. These examples have the same scenario as the one you are given. 

    Instructions:
    1. User Stories Learning
    - Analyze provided User Stories to identify:
        · Actors: User types (e.g., regular users, admins) and contract types (e.g., parent/external contracts).
        · Isolation Needs: Variables requiring read/write isolation (e.g., user-specific balances, contract-specific settings).
        · Encryption Triggers: Data where blockchain transparency conflicts with privacy (e.g., sensitive user details).
    2. Design Domain Models
    Derive models exclusively addressing:
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
        
    3. Output Format
    You should only output the Domain Models of the contract.
    The Domain Models are:  
    <Domain Models>  
    - [State Variable 1]:
        · Read restricted to [Actor/Contract Type and stored as a hash for integrity] or Read restricted to [None].
        · Write restricted to [Actor/Contract Type] or Write restricted to [None].
    - [State Variable 2]:
        · Read restricted to [Actor/Contract Type and stored as a hash for integrity] or Read restricted to [None].
        · Write restricted to [Actor/Contract Type] or Write restricted to [None].
    </Domain Models>

    The EXAMPLES are:
    {examples}

    """


    try:
        client= OpenAI(api_key=OPENAI_API_KEY,http_client=httpx.Client(proxy=proxy_1))
        response = client.chat.completions.create(
                            model=model,
                            messages=[
                                {"role": "system", "content": role_content},
                                {"role": "user", "content": f'''The user stories are <User Stories> {desc} </User Stories>.
                                        The state variables are 
                                        <State Variables>
                                        bool private _opened;
                                        mapping(address account => uint256) private _balances;
                                        mapping(address account => mapping(address spender => uint256)) private _allowances;
                                        uint256 private _totalSupply;
                                        string private _name;
                                        string private _symbol;
                                        address private _owner;
                                        </State Variables>
                                        '''},
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
    example_str=""
    cou=0
    for file in tqdm(os.listdir(root_path)):
        if file.endswith('_gpt4omini_withgraph_new.txt'):
            cou+=1
            with open(os.path.join(root_path,file),'r') as f:
                example_str+=f"EXAMPLE {cou} \n"
                example_str+=f"{f.read()}\n"
                example_str+="\n"
    with open(f"/home/liuhan/utils_download/summary_test{temp_cou}.txt",'r') as f:
        scenario=f.read()
    res=summarize_by_LLMs(scenario,example_str)
    with open(f'/home/liuhan/utils_download/requirement_test_gpt4omini{temp_cou}.txt','w') as f:
        f.write(res)