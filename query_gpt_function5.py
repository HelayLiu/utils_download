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
def summarize_by_LLMs(desc,examples,model="gpt-4.1-mini"):
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
    - Analyze the function signature and read/written state variables to identify their roles and contributions.
    - Identify isolation checks and constraints based on the Domain Models and User Stories:
        - Read/Write Isolation:
            · Use arguments/global variables (msg.sender, msg.value, this, etc.) to enforce per-user/contract access (e.g., msg.sender == _owner).
        - Cross-Contract Encapsulation:
            · Validate external contract interactions (e.g., _externalContract in whitelist).
        - Integrity via Hashing:
            · If a state variable is private, consider that it is necessary to using keccak256 or other hashing to ensure the integrity of seemingly private data (e.g., luckyNumber = keccak256(_luckyNumber)).
    - NOTE THAT DO NOT CONTAIN ANY LOGIC OF THE FUNCTIONALITY, LIKE ASSIGNMENTS OR ADD OR SUBTRACTION, I.E., =, +=, -=, ETC.
      YOU JUST NEED TO FOCUS ON THE ISOLATION CHECKS AND ENCRYPTION-FOCUSED CHECKS.
        - For example, the amount should add to the balance of the user, i.e., _balances[msg.sender] = _balances[msg.sender] + amount.
    - TRY TO SPLIT THE CHECKS IF THE CHECKS USING AND, YOU CAN SPLIT THEM INTO TWO PARTS.
        - For example, 
            [
                {{
                    "involved_variables": ["msg.sender", "_patient", "msg.value"],
                    "potential_checks": "msg.sender == _patient && msg.value > 0",
                    "descriptions": "Verify msg.sender == _patient to enforce write access to _encryptedRecords and msg.value > 0 to ensure a valid transaction."
                }}
            ]
            you should split them into two parts:
            [
                {{
                    "involved_variables": ["msg.sender", "_patient"],
                    "potential_checks": "msg.sender == _patient",
                    "descriptions": "Verify msg.sender == _patient to enforce write access to _encryptedRecords."
                }},
                {{
                    "involved_variables": ["msg.value"],
                    "potential_checks": "msg.value > 0",
                    "descriptions": "Ensure msg.value > 0 to validate the transaction amount."
                }}
            ]            
        
    3. Output Format
    You should ONLY output a JSON object in the following formate without any other text. 
    In your response, you should include three parts:
    - Involved variables: A list of all the involved variables in the function signature and global variables.
    - Potential checks: The constraints of the potential checks should be done in the function.
    - Descriptions: A sentences of the description of the isolation checks and encryption-focused checks.
    Each part should be a dictionary, for example, the output should be like this:
    [{{
        "involved_variables": ["msg.sender", "_patient"],
        "potential_checks": "msg.sender == _patient",
        "descriptions": "Verify msg.sender == _patient to enforce write access to _encryptedRecords."
    }},
    {{
        "involved_variables": ["_encryptedData", "recordHash"],
        "potential_checks": "keccak256(_encryptedData) == recordHash",
        "descriptions": "Ensure keccak256(_encryptedData) == recordHash to validate data integrity."
    }}]


    """

    usr_content=f"""
        The general User Stories are:  
    - As a user, I want my ERC20 token balance to be isolated from others, ensuring that my transactions do not affect other users' balances.
    - As a user, I want to mint ERC20 tokens by interacting with ERC721 and ERC1155 tokens, ensuring that my actions are secure and do not interfere with other users' transactions.
    - As a user, I want to unwrap my ERC20 tokens back into ERC1155 tokens, with the assurance that my balance is accurately calculated and that I receive the correct amount of tokens in return.
    - As a user, I want to ensure that my token transfers are protected against reentrancy attacks, so that my funds remain secure during transactions.
    - As a contract owner, I want to control the opening and closing of the minting process, ensuring that I can manage the supply of tokens effectively.

    This contract serves as a wrapper for ERC20 tokens, allowing users to mint tokens based on their holdings of ERC721 and ERC1155 tokens. It ensures user-specific state isolation by maintaining individual balances in a mapping, preventing any unintended state leakage between users. The contract also implements reentrancy guards to protect against potential attacks during token transfers and minting operations.

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

    The function signature is:
    <function_signature>
     function onERC721Received(
        address,
        address from,
        uint256,
        bytes calldata
    ) external returns (bytes4)
    </function_signature>
    This function has write the following state variables:
    <written_state_variables>
    mapping(address owner => uint256) private _balancesOfOwner;
    uint256 private _holders;
    mapping(address account => uint256) private _balances;
    uint256 private _totalSupply;
    </written_state_variables>
    This function has read the following state variables:
    <read_state_variables>
    bool private _opened;
    IERC721 public immutable erc721Contract;
    uint256 private constant ERC721_RATIO = 400 * 1e18;
    </read_state_variables>
    """
    try:
        client= OpenAI(api_key=OPENAI_API_KEY,http_client=httpx.Client(proxy=proxy_1))
        response = client.chat.completions.create(
                            model=model,
                            messages=[
                                {"role": "system", "content": role_content},
                                {"role": "user", "content": usr_content},
                            ],
                            # temperature = 0,
                            seed=42,
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
    res=summarize_by_LLMs("test","test")
    with open('/home/liuhan/utils_download/checks_test_gpt4o3mini_new1.txt','w') as f:
        f.write(res)