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
        Role: You are a Smart Contract Security Architect specializing in State Isolation Bugs

        Input Processing Steps:
        1. User Story & Domain Model Analysis
            - Identify:
                a) Actor Types (human users, contracts, roles)
                b) State Variable Isolation Requirements (storage segregation patterns and variables requiring hashing/encryption)
                c) Access Control Matrix (write/read permissions per actor)

        2. Function Decomposition
            For each function:
                a) Create variable inventory:
                    - Input parameters
                    - Global variables
                    - Accessed state variables (read/write)
                b) Derive isolation requirements:
                    - Read-path constraints (decryption, hash verification)
                    - Write-path constraints (ownership, role-based access)
                c) Flag cross-domain state interactions

        3. Constraint Generation Rules
            - Atomic Checks Principle:
                * Split compound conditions (&&/||) into individual checks, avoid occurring `&&` conditions.
                * Example: "A && B" becomes two separate checks
            - Deduplication Protocol:
                * Merge identical constraints on multiple variables
                * Example: msg.sender checks on different mappings
            - Cryptographic Enforcement:
                * Explicit hash/encryption validation before sensitive operations
                * Prevention of raw data exposure for committed values
            - Coarse Principle:
                * When multiple checks are required in a single function, just include the maximum one check for each function.
                * Example: If a function requires both ownership and specific address checks, only include the specific address check if it is more critical for isolation.

        Output Requirements:
        - Strict JSON format with NO explanatory text
        - No markdown formatting
        - Each entry must follow schema:
        {{<Function Signature1>:
        [
        {{
            "potential_checks": "atomic_expression_using_only_operators_and_functions_in_involved_variables",
            "involved_variables":  ["array_of_contract_variables_in_potential_checks"],
            "descriptions": "explain_the_purpose_of_the_check_in_enforcing_state_isolation",
            "references": ["list_of_the_domain_models"]
        }},...]
        <Function Signature_2>:[...]
        }}
        Validation Safeguards:
        1. Reject any functional logic (+=, -=) apart from cryptographic checks
        2. Filter out non-isolation related checks
        3. Require cryptographic verification for precommitted values
        4. Enforce principal-of-least-privilege in access checks
        5. Ensure the involved variables are occurred in the function signature or global variables and in the potential_checks.
        6  Reject any checks are repeated or duplicated.
        7. Try to reduce the potential_checks to the minimum.
        7. Risk Prioritization Filter:
            - Exclude basic validity checks that don't impact core security properties:
                * Numerical lower bounds (e.g., amount > 0)
                * Non-zero address checks (e.g., recipient != address(0))
                * Non-critical range validations
            - Only include checks that directly enforce state isolation bugs.
        
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

    <Function1>
    The function signature is:
    <function_signature>
     function onERC1155Received(
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
    </written_state_variables>
    This function has read the following state variables:
    <read_state_variables>
    IERC1155 public immutable erc1155Contract;
    uint256 public immutable tokenID;
    uint256 private constant ERC1155_RATIO = 400_000 * 1e18;
    </read_state_variables>
    </Function1>

    <Function2>
    The function signature is:
    <function_signature>
     function onERC721Received(
        address,
        address from,
        uint256 id,
        bytes calldata
    ) external returns (bytes4)
    </function_signature>
    This function has write the following state variables:
    <written_state_variables>
    mapping(address owner => uint256) private _balancesOfOwner;
    uint256 private _holders;
    mapping(address account => uint256) private _balances;
    </written_state_variables>
    This function has read the following state variables:
    <read_state_variables>
    IERC721 public immutable erc721Contract;
    uint256 public immutable tokenID;
    uint256 private constant ERC721_RATIO = 1_000_000 * 1e18;
    </read_state_variables>
    </Function2>
    """
    #     This function doing the following functionality:
    # The function validates the token ID, potentially mints new tokens for the sender based on the received amount and a predefined ratio (ERC1155_RATIO), and always returns its function selector to acknowledge the receipt of ERC-1155 tokens.
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
    print(f"Prompt tokens: {response.usage.prompt_tokens}")
    print(f"Completion tokens: {response.usage.completion_tokens}")
    return response.choices[0].message.content

if __name__ == "__main__":
    res=summarize_by_LLMs("test","test")
    with open('/home/liuhan/utils_download/checks_test_gpt4o3mini_new1.txt','w') as f:
        f.write(res)