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
def truncate_token(text: str, model: str = 'gpt-o3-mini', max_token=128000) -> int:
    try:
        encoding = tiktoken.encoding_for_model(model)
    except KeyError:
        encoding = tiktoken.get_encoding("cl100k_base")
    tokens = encoding.encode(text)
    tokens = tokens[-max_token:]
    len_tokens = len(tokens)
    truncated_code = encoding.decode(tokens)
    return truncated_code, len_tokens
def summarize_by_LLMs(desc='',model="gpt-4.1-mini"):
    role_content="""
    Roles:  You are a smart contract security expert specializing in symbolic execution analysis. Your task is to rigorously evaluate whether critical security checks are implemented in a contract by analyzing provided symbolic execution results and a list of potential checks.

    Instructions:
    1. Map Checks to Constraints
        - For each potential check in the list:
            a. Cross-reference it with all symbolic execution constraints to determine if the check is enforced.
            b. If no constraint explicitly enforces the check, flag it as missing.
    2. Vulnerability Analysis
        - For each missing check:
            a. Judge whether the absence of the check could lead to a state isolation vulnerability, i.e., the state should be isolated but is not across different users and contracts.
            b. Reference specific paths/constraints in the symbolic results that fail to mitigate the risk.

    3. Constraint Relevance Assessment
        - If a check is marked as "conducted," justify by listing exact constraints from the symbolic results that correspond to the check.
        - If constraints exist but are irrelevant to the check, explain why they do not address the vulnerability.

    Output Format:
    You should first output whether the check is all conducted in the contract or not using the following format:
    [Yes/No]:
    - [Yes/No]: "The check is all conducted in the contract." or "The check is not all conducted in the contract."
    Then, you should only output the potential checks that are not conducted in the contract.
    Structure your response as:
    The potential checks that are not conducted in the contract are:
    <Potential Checks>
    - [Potential Check 1]:
    - [Description of why the check is needed]
    - [Potential Check 2]:
    - [Description of why the check is needed]
    </Potential Checks>
    """

    User_content=f"""
    The potential checks are:
    <Potential Checks>
    [
    {{
        "involved_variables": ["from", "_balances", "_balancesOfOwner"],
        "potential_checks": "msg.sender == address(erc1155Contract)",
        "descriptions": "Ensures that only the authorized ERC1155 contract can trigger the onERC1155Received function, preventing unauthorized state modifications and preserving user-specific balance isolation.",
        "references": ["_balances", "_balancesOfOwner", "erc1155Contract"]
    }},
    {{
        "involved_variables": ["from", "_balances"],
        "potential_checks": "from != address(0)",
        "descriptions": "Prevents state changes from the zero address to avoid unintended balance assignments, maintaining integrity of user-specific balances.",
        "references": ["_balances"]
    }}
    ]
    </Potential Checks>

    The symbolic execution result is:
    <symbolic_execution_result>
    Execution Constraints:
    Constraint 1: (_status == ENTERED) == False
    Constraint 2: (id == tokenID) == True
    Constraint 3: (msg.sender ==
    erc1155Contract) ==
    True
    Constraint 4: Or(addr_from == addr_account,
    addr__mintAddress04 == addr_account,
    addr__mintAddress01 == addr_account,
    addr__mintAddress05 == addr_account,
    addr__mintAddress02 == addr_account,
    addr_from == addr_account,
    addr__mintAddress03 == addr_account,
    addr__mintAddress07 == addr_account,
    addr__mintAddress08 == addr_account,
    addr__mintAddress06 == addr_account)
    Constraint 5: Or(_mintAmount06 == value,
    ERC721_RATIO == value,
    _mintAmount05 == value,
    _mintAmount02 == value,
    _mintAmount08 == value,
    _mintAmount01 == value,
    _mintAmount07 == value,
    amount*ERC1155_RATIO == value,
    remainderERC20Amount == value,
    _mintAmount03 == value,
    _mintAmount04 == value)
    Constraint 6: (_maxTotalSupply > _totalSupply + value) == True
    Constraint 7: (0 == addr_account) == False
    Constraint 8: (0 == addr_from) == False
    Constraint 9: (_balances[addr_from] < value) == False
    Constraint 10: (0 == addr_to) == False
    Constraint 11: (0 == _balancesOfOwner[addr_account]) == True

    </symbolic_execution_result>
    """
    # <Contract Description>
    # This contract serves as a wrapper for ERC20 tokens, allowing users to mint tokens based on their holdings of ERC721 and ERC1155 tokens. It ensures user-specific state isolation by maintaining individual balances in a mapping, preventing any unintended state leakage between users. The contract also implements reentrancy guards to protect against potential attacks during token transfers and minting operations.
    # </Contract Description>
    # The function signature is:
    # <function_signature>
    #  function onERC1155Received(
    #     address,
    #     address from,
    #     uint256 id,
    #     uint256 amount,
    #     bytes calldata
    # ) external returns (bytes4)
    # </function_signature>
    # This function has write the following state variables:
    # <written_state_variables>
    # mapping(address owner => uint256) private _balancesOfOwner;
    # uint256 private _holders;
    # mapping(address account => uint256) private _balances;
    # uint256 private _totalSupply;
    # </written_state_variables>
    # This function has read the following state variables:
    # <read_state_variables>
    # uint256 public immutable tokenID;
    # IERC721 public immutable erc721Contract;
    # </read_state_variables>
    try:
        client= OpenAI(api_key=OPENAI_API_KEY,http_client=httpx.Client(proxy=proxy_1))
        response = client.chat.completions.create(
                            model=model,
                            messages=[
                                {"role": "system", "content": role_content},
                                {"role": "user", "content": User_content},
                            ],
                            temperature = 0,
                            seed=0,
                            top_p=0
                        )
    except Exception as e:
        print('Error in response')
        print(e)
        return None
    return response.choices[0].message.content

if __name__ == "__main__":
    temp_cou=3
    # with open(f'/home/liuhan/utils_download/test_contract{temp_cou}.sol','r') as f:
    #     code=f.read()
    # code=truncate_token(code)
    summary=summarize_by_LLMs()
    with open(f'/home/liuhan/utils_download/result_1.txt','w') as f:
        f.write(summary)
    