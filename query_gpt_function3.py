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
def summarize_by_LLMs(desc,examples,model="gpt-4o-mini-2024-07-18"):
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
    - Analyze the function signature and state variables to identify their roles and contributions.
    - Identify isolation checks and constraints based on the Domain Models and User Stories:
        - Read/Write Isolation:
            · Use arguments/global variables (msg.sender, msg.value, this, etc.) to enforce per-user/contract access (e.g., msg.sender == _owner).
        - Cross-Contract Encapsulation:
            · Validate external contract interactions (e.g., _externalContract in whitelist).
        - Integrity via Hashing:
            · If a state variable is private, consider that it is necessary to using keccak256 or other hashing to ensure the integrity of seemingly private data (e.g., luckyNumber = keccak256(_luckyNumber)).
    3. Output Format
    You should ONLY output a JSON object in the following formate without any other text.
    - Keys: Arguments/global variables involved in isolation checks or encryption-focused checks.
    - Values: Descriptions of isolation or encryption-focused checks.
    For example, the output should be like this:
    {{  
        ["msg.sender", "_patient"]: "Verify msg.sender == _patient to enforce write access to _encryptedRecords.",  
        ["_encryptedData", "recordHash"]: "Ensure keccak256(_encryptedData) == recordHash to validate data integrity."  
    }}

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
    - [players]:
        · This array of Player structs is private, ensuring that only the contract can access the player addresses and their chosen numbers. This enforces isolation by preventing other players from viewing each other's information during the game.
    - [count]:
        · This variable tracks the number of players that have joined the game. It is not marked as private, but its usage is controlled within the contract logic to ensure that it only reflects the number of players currently participating, thus maintaining the integrity of the game state and ensuring that the game only proceeds when two players have joined.
    </Domain Models>
    """

    usr_content=f"""
    The function signature is:
    <function_signature>
        function play(uint number) public payable;
    </function_signature>
    The state variables are:
    <state_variables>
        struct Player {{
                address addr;
                uint number;
            }}

        Player[2] private players;
        uint count = 0;
    </state_variables>
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
                        )
    except Exception as e:
        print('Error in response')
        print(e)
        return None
    return response.choices[0].message.content

if __name__ == "__main__":
    res=summarize_by_LLMs("test","test")
    with open('/home/liuhan/utils_download/checks_test_gpt4omini2_new.txt','w') as f:
        f.write(res)