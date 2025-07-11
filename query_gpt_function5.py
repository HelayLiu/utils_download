import requests
import re
import json
from openai import OpenAI
from tqdm import tqdm
import httpx
import os
import tiktoken
from pydantic import BaseModel
from config import OPENAI_API_KEY
proxy_1 = "http://127.0.0.1:20171"
# 配置 HTTP 代理地址
proxies = {
    "http": "http://127.0.0.1:20171",
    "https": "http://127.0.0.1:20171",
}
class FunctionChecks(BaseModel):
    
    potential_checks: str
    involved_variables: list[str]
    descriptions: str
    reference: list[str]
class FunctionChecksList(BaseModel):
    function_signature: str
    checks: list[FunctionChecks]
class FunctionChecksListResponse(BaseModel):
    result: list[FunctionChecksList]

def truncate_token(text: str, model: str = 'gpt-4.1-mini', max_token=128000) -> int:
    try:
        encoding = tiktoken.encoding_for_model(model)
    except KeyError:
        encoding = tiktoken.get_encoding("cl100k_base")
    tokens = encoding.encode(text)
    tokens = tokens[-max_token:]
    len_tokens = len(tokens)
    truncated_code = encoding.decode(tokens)
    return truncated_code, len_tokens
def summarize_by_LLMs(funcs,examples,model="gpt-4.1-mini"):
    role_content=f"""
    Role: You are a smart contract security architect. Given User Stories and Domain Models, your task is to analyze function signatures and the state variables and derive checks/constraints that enforce state isolation and cryptographic integrity.
    Instructions:
    1. User Stories & Domain Models Learning
    - Review User Stories to identify:
        · Actors: User types (e.g., regular users, admins) and contracts.
        · Corresponding Domain Models with the given state variables.
        · Isolation Rules: Domain Models defining state variable isolation (e.g., private mapping(address => bytes)).
        · Encryption Needs: Variables requiring hashing (e.g., keccak256) per Domain Models.
    2. Function Analysis
    - Analyze the function signature and read/written state variables to identify their roles and contributions, you should understand what the function is doing.
    - Identify isolation checks and constraints based on the Domain Models and User Stories:
        - Read Isolation:
            · For each read state variable, ensure it should check the related Domain Models (e.g., hashing)
        - Write Isolation:
            · For each written state variable, ensure it should check the related Domain Models (e.g., checking ownership, access control).
    - NOTE THAT DO NOT CONTAIN ANY LOGIC OF THE FUNCTIONALITY, LIKE ASSIGNMENTS OR ADD OR SUBTRACTION, I.E., =, +=, -=, ETC.
      YOU JUST NEED TO FOCUS ON THE ISOLATION CHECKS AND ENCRYPTION-FOCUSED CHECKS.
        - For example, [the amount should add to the balance of the user, i.e., _balances[msg.sender] = _balances[msg.sender] + amount.] should not be included in the output.
    - TRY TO SPLIT THE CHECKS IF THE CHECKS USING AND, YOU CAN SPLIT THEM INTO TWO PARTS.
        - For example, 
            [
                {{
                    "involved_variables": ["msg.sender", "_patient", "msg.value"],
                    "potential_checks": "msg.sender == _patient && msg.value > 0",
                    "descriptions": "Verify msg.sender == _patient to enforce write access to _encryptedRecords and msg.value > 0 to ensure a valid transaction."
                    "reference": ["_balances"]
                }}
            ]
            you should split them into two parts:
            [
                {{
                    "involved_variables": ["msg.sender", "_patient"],
                    "potential_checks": "msg.sender == _patient",
                    "descriptions": "Verify msg.sender == _patient to enforce write access to _encryptedRecords.",
                    "reference": ["_balances"]
                }},
                {{
                    "involved_variables": ["msg.value"],
                    "potential_checks": "msg.value > 0",
                    "descriptions": "Ensure msg.value > 0 to validate the transaction amount.",
                    "reference": ["_balances"]
                }}
            ]            
        
    3. Union of checks:
        - If the checks are intended to achieve a similar goal, you should union them together.
           · For example, if two of the state variables are both need to check the ownership of the user, you can union them together.
              i.e., _balances[msg.sender] and _allowances[msg.sender][spender] should both check the authorization of the user, i.e., msg.sender == authorizedUser, you can union them together.

    4. Output Format
    You should ONLY output a JSON object in the following formate without any other text. 
    In your response, you should include three parts:
    - Involved variables: A list of all the involved variables of the checks in the function signature and global variables, e.g, msg.sender, _patient, _encryptedData, recordHash, etc. 
    - Potential checks: The specific constraints of the potential checks should be done in the function, e.g., A == B, C = keccak256(D), etc. 
    - Descriptions: A sentences of the description of the isolation checks and encryption-focused checks.
    Each part should be a dictionary, for example, the output should be like this:
    {{"function_signature": "function submitNumber(uint256 _number) public payable",
    "checks":
    [{{
        "potential_checks": "msg.sender == _patient",
        "involved_variables": ["msg.sender", "_patient"],
        "descriptions": "Verify msg.sender == _patient to enforce write access to _encryptedRecords."
        "reference": ["_balances"]
    }},
    {{
        "involved_variables": ["_encryptedData", "recordHash"],
        "potential_checks": "recordHash = keccak256(_encryptedData)",
        "descriptions": "Ensure keccak256(_encryptedData) to validate data integrity."
        "reference": ["recordHash"]
    }}]
    "function_signature": "..."
    "checks": [
        {{
            "potential_checks": "...",
            "involved_variables": [...],
            "descriptions": "...",
            "reference": [...]
        }},
        ...
    ]
    }}


    """

    usr_content=f"""
    The general User Stories are: 
    <User Stories> 
    - This contract serves as a wrapper for ERC20 tokens, allowing users to mint tokens based on their holdings of ERC721 and ERC1155 tokens. It ensures user-specific state isolation by maintaining individual balances in a mapping, preventing any unintended state leakage between users. The contract also implements reentrancy guards to protect against potential attacks during token transfers and minting operations.
    - As a user, I want my ERC20 token balance to be isolated from others, ensuring that my transactions do not affect other users' balances.
    - As a user, I want to mint ERC20 tokens by interacting with ERC721 and ERC1155 tokens, ensuring that my actions are secure and do not interfere with other users' transactions.
    - As a user, I want to unwrap my ERC20 tokens back into ERC1155 tokens, with the assurance that my balance is accurately calculated and that I receive the correct amount of tokens in return.
    - As a user, I want to ensure that my token transfers are protected against reentrancy attacks, so that my funds remain secure during transactions.
    - As a contract owner, I want to control the opening and closing of the minting process, ensuring that I can manage the supply of tokens effectively.
    </User Stories>
    

    The Domain Models are:
    <Domain Models>  
    - _opened: bool private _opened;  
        · Read restricted to Owner.  
        · Write restricted to Owner.  
    - _balances: mapping(address => uint256) private _balances;  
        · Read restricted to None.  
        · Write restricted to the user themselves or the contract (e.g., minting, burning) or the owner.  
    - _allowances: mapping(address => mapping(address => uint256)) private _allowances;  
        · Read restricted to None.  
        · Write restricted to the user themselves or the contract or the owner.  
    - _totalSupply: uint256 private _totalSupply;  
        · Read restricted to None.  
        · Write restricted to the owner or the contract (e.g., minting, burning).  
    - _name: string private _name;  
        · Read restricted to None.  
        · Write restricted to the owner.  
    - _symbol: string private _symbol;  
        · Read restricted to None.  
        · Write restricted to the owner.  
    - _owner: address private _owner;  
        · Read restricted to None.  
        · Write restricted to the contract owner.  
    </Domain Models>

    The functions are:
    <Functions>
    {funcs}
    </Functions>
    """
    #     This function doing the following functionality:
    # The function validates the token ID, potentially mints new tokens for the sender based on the received amount and a predefined ratio (ERC1155_RATIO), and always returns its function selector to acknowledge the receipt of ERC-1155 tokens.
    try:
        client= OpenAI(api_key=OPENAI_API_KEY,http_client=httpx.Client(proxy=proxy_1))
        response = client.chat.completions.create(
                            model=model,
                            messages=[
                                {"role": "system", "content": role_content},
                                {"role": "user", "content": usr_content},
                            ],
                            temperature = 0,
                            seed=0,
                            # top_p=0
                        )
    except Exception as e:
        print('Error in response')
        print(e)
        return None
    print(f"Prompt tokens: {response.usage.prompt_tokens}")
    print(f"Completion tokens: {response.usage.completion_tokens}")
    return response.choices[0].message.content

if __name__ == "__main__":
    with open('/home/liuhan/utils_download/test_contract3_function_wrv.json','r') as f:
        content = json.load(f)
    res=summarize_by_LLMs(content,"test",model="ft:gpt-4.1-mini-2025-04-14:hkust-cybersecurity-lab::BieHcNJb")
    with open('/home/liuhan/utils_download/checks_test_finetune.json','w') as f:
        json.dump(res,f,indent=4)