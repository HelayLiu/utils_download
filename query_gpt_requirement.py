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
    You are now acting as a smart contract developer expert. You are given some examples of the scenarios and their corresponding requirements of smart contracts, and your task is to analyze and summarize the requirements of the contract based on a given scenario.
    Instructions:
    1. Scenario and Requirements Learning
    You are given several examples of the scenarios and their corresponding requirements of smart contracts.
    Carefully examine the scenarios and their corresponding requirements. See how the requirements are derived from the scenarios.
    2. Design Requirements
    Based on the given scenario, you need to design the requirements for the contract.
    - The requirements should be designed based on the scenario.
    - The requirements should be clear, concise, and unambiguous.
    - THE REQUIREMENTS MUST ONLY REFLECT THE ISOLATION OF READ AND WRITE ON THE STATE VARIABLES OF DIFFERENT USERS, AND CONTRACTS. SHOULD NOT INCLUDE ANY OTHER FUNCTIONALITY REQUIREMENTS.
    - The requirements should not describe the implementation details but rather the expected behavior and constraints of the contract. 
    - The requirements should also consider the keccak256 etc. encryption and the hash of the state variables to ensure the integrity and security of the contract.
    3. Output Format
    Provide several sentences that summarize the requirements of the contract.
    Your answer should be:
    The requirements are:
    <Requirements>
    requirements
    </Requirements>.

    The EXAMPLES are:
    {examples}

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
    root_path = f"/home/liuhan/utils_download/simliar_code{temp_cou}"
    os.makedirs(root_path, exist_ok=True)
    example_str=""
    cou=0
    for file in tqdm(os.listdir(root_path)):
        if file.endswith('.txt'):
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