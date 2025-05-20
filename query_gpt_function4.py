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
    - Analyze the function signature and read/written state variables to identify their roles and contributions.
    - Identify isolation checks and constraints based on the Domain Models and User Stories:
        - Read/Write Isolation:
            · Use arguments/global variables (msg.sender, msg.value, this, etc.) to enforce per-user/contract access (e.g., msg.sender == _owner).
        - Cross-Contract Encapsulation:
            · Validate external contract interactions (e.g., _externalContract in whitelist).
        - Integrity via Hashing:
            · If a state variable is private, consider that it is necessary to using keccak256 or other hashing to ensure the integrity of seemingly private data (e.g., luckyNumber = keccak256(_luckyNumber)).
    3. Output Format
    You should ONLY output a JSON object in the following formate without any other text. 
    In your response, you should include three parts:
    - Involved variables: A list of all the involved variables in the function signature and global variables.
    - Potential checks: A string of the potential checks should be done in the function.
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

    The general User Stories are:  
    1. As a user, I want to open a margin position with specific parameters, so that I can trade with leverage while ensuring my collateral is properly managed.
    2. As a user, I want to increase my margin position by depositing additional collateral, so that I can maintain or enhance my trading capacity.
    3. As a user, I want to add stop-loss and take-profit orders to my margin positions, so that I can automate my trading strategy and manage risk effectively.
    4. As a user, I want to cancel my active orders if my trading conditions change, ensuring I have control over my trading actions.
    5. As a user, I want to repay my debt associated with a margin position, so that I can reduce my leverage and manage my financial exposure.
    6. As a user, I want to remove collateral from my margin position, so that I can retrieve my assets when I no longer need them.
    7. As a user, I want to view the details of my margin positions and orders, so that I can make informed trading decisions based on my current status.
    8. As a governor, I want to set and manage quote assets for trading pairs, ensuring that the trading environment remains flexible and responsive to market conditions.

    In this contract, user-specific state isolation is enforced through mappings that store individual user positions and orders, ensuring that each user's data is kept private and secure. Cross-contract interactions are carefully managed to prevent unintended state leakage, allowing users to interact with the contract without exposing their sensitive information.

    The Domain Models are:
    <Domain Models>  
    - **CORE**: address public immutable;  
    - This variable is public and immutable, allowing all users to access the core contract address while ensuring that it cannot be changed, maintaining the integrity of the contract's core functionality.

    - **POS_MANAGER**: address public immutable;  
    - This variable is public and immutable, allowing all users to access the position manager contract address while ensuring that it cannot be changed, preserving the integrity of position management.

    - **lastPosIds**: mapping(address => uint) public;  
    - This mapping tracks the last position ID for each user, ensuring that each user's position IDs are isolated and can be accessed independently without affecting others.

    - **initPosIds**: mapping(address => mapping(uint => uint)) public;  
    - This mapping stores the initial position IDs for each user and their respective positions, ensuring that each user's initial positions are tracked separately and securely.

    - **__quoteAssets**: mapping(address => mapping(address => address)) private;  
    - This private mapping stores the quote assets for each user, ensuring that sensitive information about user-specific assets is not exposed to others.

    - **__orders**: mapping(uint => Order) private;  
    - This private mapping stores orders associated with specific IDs, ensuring that order details are isolated and can only be accessed by authorized functions, preventing unauthorized access.

    - **__marginPositions**: mapping(uint => MarginPos) private;  
    - This private mapping stores margin positions associated with specific IDs, ensuring that each user's margin positions are isolated and protected from other users.

    - **__posOrderIds**: mapping(uint => uint[]) private;  
    - This private mapping links position IDs to their associated order IDs, ensuring that each user's orders are tracked independently and securely.

    - **lastOrderId**: uint public;  
    - This variable tracks the last order ID issued, allowing all users to see the most recent order ID while ensuring that the order management process remains secure and isolated per user.

    - **swapHelper**: address public;  
    - This variable is public and allows users to access the swap helper contract address, ensuring that interactions with external contracts are transparent while maintaining user-specific state isolation.

    - **ONE_E18**: uint private constant;  
    - This constant is used for calculations involving 18 decimal places, ensuring that precision is maintained in financial operations without exposing sensitive data.

    - **ONE_E36**: uint private constant;  
    - This constant is used for calculations involving 36 decimal places, ensuring that precision is maintained in financial operations without exposing sensitive data.

    - **GOVERNOR**: bytes32 private constant;  
    - This constant is used to identify the governance role within the contract, ensuring that only authorized users can perform governance-related actions without exposing sensitive information.  
    </Domain Models>
    """

    usr_content=f"""
    The function signature is:
    <function_signature>
    function updateOrder(
        uint _posId,
        uint _orderId,
        uint _triggerPrice_e36,
        address _tokenOut,
        uint _limitPrice_e36,
        uint _collAmt
    ) external;
    </function_signature>
    This function has write the following state variables:
    <written_state_variables>
    mapping(uint => Order) private __orders;
    </written_state_variables>
    This function has read the following state variables:
    <read_state_variables>
    mapping(address => mapping(uint => uint)) public initPosIds;
    mapping(uint => Order) private __orders;
    mapping(uint => MarginPos) private __marginPositions;
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
                            temperature = 0,
                            seed = 0,
                        )
    except Exception as e:
        print('Error in response')
        print(e)
        return None
    return response.choices[0].message.content

if __name__ == "__main__":
    res=summarize_by_LLMs("test","test")
    with open('/home/liuhan/utils_download/checks_test_gpt41nano_new_with_def.txt','w') as f:
        f.write(res)