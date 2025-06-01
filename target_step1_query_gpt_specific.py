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
    Roles: You are a smart contract developer and requirements engineering expert. Your task is to analyze a given smart contract and generate User Stories of the contract.

    Instructions:
    1. Identify Actors
    - Identify the main actors in the contract (e.g., users, external contracts).
    - Determine the interactions between these actors and the contract.
    - Ignore the incorrect actions in the contract against your knowledge.
    2. User Stories
    - Summarize the contract's purpose and use cases, emphasizing:
        · How user-specific state isolation is enforced including:
        - Write isolation: Ensure that each user's state is isolated from others (i.e., access control).
        - Read isolation: Ensure that users can only read their own state (i.e., encrypted data).

    - Example: "As a user, I want my encrypted voting preferences isolated from others, even though the blockchain is public."
    3. Output Format
    You should only output the User Stories of the contract.
    Structure your response as: 
    The general User Stories are:  
    <User Stories>  
    [Several sentences that summarize the User Stories of the contract]
    </User Stories> 
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
    temp_cou=3
    with open(f'/home/liuhan/utils_download/test_contract{temp_cou}.sol','r') as f:
        code=f.read()
    code=truncate_token(code)
    summary=summarize_by_LLMs(code)
    with open(f'/home/liuhan/utils_download/summary_test{temp_cou}.txt','w') as f:
        f.write(summary)
    