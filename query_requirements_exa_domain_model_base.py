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
def truncate_token(text: str, model: str = 'gpt-4o-mini', max_token=120000) -> int:
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
    Please analyze the given smart contract and generate User Stories and Domain Models focused on state isolation across users and contracts.

    Structure your response as: 
    The general User Stories are:  
    <User Stories>  
    [Concise bullet points highlighting state isolation use cases]  
    </User Stories>  

    The Domain Models are:  
    <Domain Models>  
    [Bullet points detailing isolation mechanisms of the state variable for users/contracts, with variable visibility and encryption details]  
    </Domain Models>
    """


    try:
        client= OpenAI(api_key=OPENAI_API_KEY,http_client=httpx.Client(proxy=proxy_1))
        response = client.chat.completions.create(
                            model=model,
                            messages=[
                                {"role": "system", "content": role_content},
                                {"role": "user", "content": f'''The contract is <Contract> {desc} </Contract>'''},
                            ],
                            temperature = 0,
                        )
    except Exception as e:
        print('Error in response')
        print(e)
        return None
    return response.choices[0].message.content

if __name__ == "__main__":
    temp_cou=''
    root_path = f"/home/liuhan/utils_download/similar_code{temp_cou}"
    os.makedirs(root_path, exist_ok=True)
    cou=0
    for file in tqdm(os.listdir(root_path)):
        if file.endswith('.sol'):
            cou+=1
            with open(os.path.join(root_path,file),'r') as f:
                code=f.read()
            code, len_tokens=truncate_token(code)
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
            with open(os.path.join(root_path,f"{file}_gpt4omini_general.txt"),'w') as f:
                f.write(requirement)