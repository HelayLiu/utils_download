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
    You are now acting as a smart contract developer expert. You are given a scenario and a few requirements of smart contracts, and your task is to analyze and summarize the potential checks and constraint based on the given function signature.
    Instructions:
    1. Scenario and Requirements Learning
    You are given a scenario and a few examples of the scenarios and their corresponding requirements of smart contracts.
    Carefully examine the scenarios and their corresponding requirements. Consider how can the requirements be realized in the contract.
    2. Analyze the function checks and constraint of the contract
    Based on the given function signature, you need to analyze the potential checks and constraint for the contract.
    - You need to analyze the arguments of the function signature, consider what are the contributions of the arguments to the function.
    - You should analyze each of the requirements, consider whether the requirements should be checked in the function.
    - You can use the global variables in the contract to help you analyze the function, i.e., msg.sender, msg.value, block.timestamp, etc.
    - You will also be given some state variables, you need to analyze the state variables and consider how can the state variables be used in the function.
    - You need to analyze the requirements, consider how can the requirements be realized in the contract.
    - You should also consider the potential checks between the arguments, because the arguments can be well-designed to bypass the checks.
    - YOUR DESIGNED CHECKS OR CONSTRAINT MUST ONLY REFLECT THE ISOLATION READ AND WRITE ON THE STATE VARIABLES OF DIFFERENT USERS, AND CONTRACTS. SHOULD NOT INCLUDE ANY OTHER FUNCTIONALITY OR SECURITY REQUIREMENTS.
    - YOU SHOULD ALSO CONSIDER THE TRANSPARENCY OF THE BLOCKCHAIN, i.e., all the transaction data is public and can be accessed by anyone. Hence, the checks and constraints should also contains the encryptions like keccak256 etc. to ensure the integrity and security of the contract.

    3. Output Format
    - Please provide a set of arguments and global variables that might need to be compared. 
    - The output should be a json format, with the keys being a list of arguments and global variables that might need to be compared, and the values being the descriptions of the comparisons.
    - THE VARIABLE NAME MUST BE THE SAME AS THE FUNCTION SIGNATURE.
    - YOU SHOULD USE THE ARGUMENTS OF THE FUNCTION AND THE GLOBAL VARIABLES (e.g., msg.sender, msg.value, block.timestamp, etc.) TO HELP YOU TO DESIGN THE CHECKS.
    - YOU ONLY NEED TO OUTPUT THE JSON OBJECT, DO NOT OUTPUT ANY OTHER TEXT.    

    For example, the output should be like this:
    {{
        ["msg.sender","from","amount"]:"Compare the allowed amount of the sender with the amount to be transferred."
    }}

    The general scenario is 
    <Scenario> 
    This contract, named OddEven, is a simple betting game where two players can participate by sending 1 ether and choosing a number. Each player is represented by a struct that holds their address and chosen number. Once two players have joined the game, the contract calculates the sum of their chosen numbers and determines the winner based on whether the sum is odd or even. The winner receives the total balance of the contract. The contract resets after each game, allowing for new players to join and play again. 
    </Scenario>.

    The requirements are:
    1. Each player must be represented by a struct that includes their address and chosen number.
    2. The contract must ensure that only two players can participate in a game at any given time.
    3. The chosen numbers of the players must be stored in a way that is isolated from other players' data.
    4. The sum of the chosen numbers must be calculated securely, ensuring that the integrity of the numbers is maintained using keccak256 hashing.
    5. The determination of the winner based on the odd or even nature of the sum must be executed without exposing the players' chosen numbers to unauthorized access.
    6. The total balance of the contract must be securely transferred to the winner, ensuring that the transaction is recorded and verifiable.
    7. After each game, the contract must reset its state variables to allow new players to join without interference from previous games. 
    </Requirements>.

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
    with open('/home/liuhan/utils_download/checks_test_gpt4omini2.txt','w') as f:
        f.write(res)