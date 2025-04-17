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
def summarize_by_LLMs(desc,model="gpt-4o-mini-2024-07-18"):
    role_content="""
    You are now acting as a smart contract audit expert. You are given a smart contract, and your task is to analyze and summarize its general scenario.
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
    5. Output Format
    Provide several sentences that summarize the general scenario of the contract.

    Your answer should be:
    The general scenario is 
    <Scenario> 
    general scenario 
    </Scenario>.
    """


    try:
        client= OpenAI(api_key=OPENAI_API_KEY,http_client=httpx.Client(proxy=proxy_1))
        response = client.chat.completions.create(
                            model=model,
                            messages=[
                                {"role": "system", "content": role_content},
                                {"role": "user", "content": f'''The contract is <contract> {desc} </contract>'''},
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
    with open(f'/home/liuhan/utils_download/test_contract{temp_cou}.sol','r') as f:
        code=f.read()
    code=truncate_token(code)
    summary=summarize_by_LLMs(code)
    with open(f'/home/liuhan/utils_download/summary_test{temp_cou}.txt','w') as f:
        f.write(summary)
    