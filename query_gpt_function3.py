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
def summarize_by_LLMs(desc,examples,model="gpt-4.1-mini-2025-04-14"):
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
            · For each read state variable, ensure it should check the related Domain Models, i.e., if the variable should not be read by other users, it should be **encrypted or hashed**.
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
    - Reference: A list of all the state variables that lead to the checks, e.g., _balances, _encryptedData, recordHash, etc.
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
    As a player, I want to participate in the OddEven game by submitting my number and paying 1 ether, so that I can compete for the total balance.  
    As a player, I want to ensure that my address and chosen number are stored privately, so that other players cannot see my information during the game.  
    As a player, I want to receive my winnings automatically if I win, so that I do not have to manually claim my prize after the game ends.  
    As a player, I want to know that the game will only proceed when two players have joined, ensuring a fair competition.  
    As a player, I want to ensure that my funds are securely transferred to the winner without any risk of failure, so that I can trust the game's outcome.  
    As a player, I want to be assured that my participation in the game is isolated from other players, maintaining the integrity of my individual game experience.  
    </User Stories>

    The Domain Models are:
    <Domain Models>  
    - players: Player[2] private  
        · Write restricted to contract internal logic only (when players join the game).  
        · Read restricted to contract internal logic only (private storage to prevent other players from seeing addresses and chosen numbers).  
    - count: uint private  
        · Write restricted to contract internal logic only (incremented when players join).  
        · Read restricted to contract internal logic only (private to prevent external visibility).  
    </Domain Models>
    The function signature is:
    <functions>
        function play(uint number) public payable:{{
        "read_state_variables": ["count"],
        "write_state_variables": ["players", "count"],
        }}
    </functions>
    """
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
                        )
    except Exception as e:
        print('Error in response')
        print(e)
        return None
    return response.choices[0].message.content

if __name__ == "__main__":
    res=summarize_by_LLMs("test","test",model="ft:gpt-4.1-mini-2025-04-14:hkust-cybersecurity-lab::BieHcNJb")
    with open('/home/liuhan/utils_download/checks_test_finetune_2.txt','w') as f:
        f.write(res)