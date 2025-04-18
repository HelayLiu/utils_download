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
    You are now acting as a smart contract developer expert. You are given a smart contract, and your task is to analyze and summarize the scenario and the requirements of the contract.
    Instructions:
    1. Code Analysis
    First, inline all inherited contracts to get a complete view of the code.
    Carefully examine the state variables and functions.
    2. Contextual Understanding
    Understand the context in which the contract operates. This includes its role within a larger system (e.g., DeFi, NFT, DAO, etc.), its potential interactions with other contracts, and its intended use cases.
    3. Scenario and Purpose
    Provide a clear and concise summary of the contract's general scenario and purpose. This should include:
    - The main functionality of the contract.
    - The specific use cases it addresses.
    - Any unique features or mechanisms it employs.
    4. Inheritance Awareness
    If the contract inherits from one or more parent contracts, you must also consider the functional and security requirements imposed by those parent contracts.
    5. Design Requirements
    Based on the given scenario, you need to design the requirements for the contract.
    - The requirements should be designed based on the scenario.
    - The requirements should be clear, concise, and unambiguous.
    - THE REQUIREMENTS MUST ONLY REFLECT THE ISOLATION OF THE STATE VARIABLES OF DIFFERENT USERS, TRANSACTIONS, AND CONTRACTS. SHOULD NOT INCLUDE ANY OTHER FUNCTIONALITY OR SECURITY REQUIREMENTS.
    - THE REQUIREMENTS SHOULD ALSO INCLUDE THE VISIBILITY OF STATE VARIABLES, for example, "The amount of the transaction should be private to the contract and not accessible to other users."
    - The requirements should not describe the implementation details but rather the expected behavior and constraints of the contract. 
    6. Output Format
    Provide several sentences that summarize the general scenario of the contract.
    Your answer should be:
    The general scenario is
    <Scenario>
    general scenario
    </Scenario>.
    The requirements are:
    <Requirements>
    requirements
    </Requirements>.
    """


    try:
        client= OpenAI(api_key=OPENAI_API_KEY,http_client=httpx.Client(proxy=proxy_1))
        response = client.chat.completions.create(
                            model=model,
                            messages=[
                                {"role": "system", "content": role_content},
                                {"role": "user", "content": f'''The scenario is <scenario> {desc} </scenario>'''},
                            ],
                            temperature = 0,
                        )
    except Exception as e:
        print('Error in response')
        print(e)
        return None
    return response.choices[0].message.content

if __name__ == "__main__":
    temp_cou=2
    root_path = f"/home/liuhan/utils_download/similar_code{temp_cou}"
    os.makedirs(root_path, exist_ok=True)
    cou=0
    for file in tqdm(os.listdir(root_path)):
        if file.endswith('.sol'):
            cou+=1
            with open(os.path.join(root_path,file),'r') as f:
                code=f.read()
            code, len_tokens=truncate_token(code)
            re_try=0
            while True:

                requirement=summarize_by_LLMs(code,"")
                if requirement is None:
                    re_try+=1
                    if re_try>10:
                        print("Error in response")
                        break
                    continue
                else:
                    break
            with open(os.path.join(root_path,f"{file}.txt"),'w') as f:
                f.write(requirement)