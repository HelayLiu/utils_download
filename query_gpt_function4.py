import requests
import re
import json
from openai import OpenAI
from tqdm import tqdm
import httpx
import os
import tiktoken
from config import OPENAI_API_KEY
from pydantic import BaseModel
proxy_1 = "http://127.0.0.1:20171"
# 配置 HTTP 代理地址
proxies = {
    "http": "http://127.0.0.1:20171",
    "https": "http://127.0.0.1:20171",
}

class FunctionChecks(BaseModel):
    
    potential_checks: str
    involved_variables: list[str]
    descriptions: str
    reference: list[str]
class FunctionChecksList(BaseModel):
    function_signature: str
    checks: list[FunctionChecks]
class FunctionChecksListResponse(BaseModel):
    result: list[FunctionChecksList]
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
def summarize_by_LLMs(desc,examples,model="gpt-4.1-mini-2025-04-14"):
    role_content=f"""
    Role: You are a smart contract security architect. Given User Stories and Domain Models, your task is to analyze function and the write/read state variables and derive checks/constraints that enforce state isolation and cryptographic integrity.
    Instructions:
    1. User Stories & Domain Models Learning
    - Review User Stories to identify:
        · Actors: User types (e.g., regular users, admins) and contracts.
        · Corresponding Domain Models with the given state variables.
        · Isolation Rules: Domain Models defining state variable isolation (e.g., private mapping(address => bytes)).
        · Encryption Needs: Variables requiring hashing (e.g., keccak256) per Domain Models.
    2. Function Analysis
    - Analyze the function signature and read/written state variables to identify their roles and contributions, you should understand what the function is doing.
    - Identify isolation checks and constraints based on the Domain Models and User Stories:
        - Read Isolation:
            · For each read state variable, ensure it should check the related Domain Models (e.g., hashing)
        - Write Isolation:
            · For each written state variable, ensure it should check the related Domain Models (e.g., checking ownership, access control).
    - NOTE THAT DO NOT CONTAIN ANY LOGIC OF THE FUNCTIONALITY, LIKE ASSIGNMENTS OR ADD OR SUBTRACTION, I.E., =, +=, -=, ETC.
      YOU JUST NEED TO FOCUS ON THE ISOLATION CHECKS AND ENCRYPTION-FOCUSED CHECKS.
        - For example, [the amount should add to the balance of the user, i.e., _balances[msg.sender] = _balances[msg.sender] + amount.] should not be included in the output.
    - TRY TO SPLIT THE CHECKS IF THE CHECKS USING AND, YOU CAN SPLIT THEM INTO TWO PARTS.
        - For example, 
            [
                {{
                    "involved_variables": ["msg.sender", "_patient", "msg.value"],
                    "potential_checks": "msg.sender == _patient && msg.value > 0",
                    "descriptions": "Verify msg.sender == _patient to enforce write access to _encryptedRecords and msg.value > 0 to ensure a valid transaction."
                    "reference": ["_balances"]
                }}
            ]
            you should split them into two parts:
            [
                {{
                    "involved_variables": ["msg.sender", "_patient"],
                    "potential_checks": "msg.sender == _patient",
                    "descriptions": "Verify msg.sender == _patient to enforce write access to _encryptedRecords.",
                    "reference": ["_balances"]
                }},
                {{
                    "involved_variables": ["msg.value"],
                    "potential_checks": "msg.value > 0",
                    "descriptions": "Ensure msg.value > 0 to validate the transaction amount.",
                    "reference": ["_balances"]
                }}
            ]            
        
    3. Union of checks:
        - If the checks are intended to achieve a similar goal, you should union them together.
           · For example, if two of the state variables are both need to check the ownership of the user, you can union them together.
              i.e., _balances[msg.sender] and _allowances[msg.sender][spender] should both check the authorization of the user, i.e., msg.sender == authorizedUser, you can union them together.

    4. Output Format
    You should ONLY output a JSON object in the following formate without any other text. 
    In your response, you should include four parts:
    - Involved variables: A list of all the involved variables of the checks in the function signature and global variables, e.g, msg.sender, _patient, _encryptedData, recordHash, etc. 
    - Potential checks: The specific constraints of the potential checks should be done in the function, e.g., A == B, C = keccak256(D), etc. 
    - Descriptions: A sentences of the description of the isolation checks and encryption-focused checks.
    Each part should be a dictionary, for example, the output should be like this:
    {{"function_signature": "function submitNumber(uint256 _number) public payable",
    "checks":
    [{{
        "potential_checks": "msg.sender == _patient",
        "involved_variables": ["msg.sender", "_patient"],
        "descriptions": "Verify msg.sender == _patient to enforce write access to _encryptedRecords."
        "reference": ["_balances"]
    }},
    {{
        "involved_variables": ["_encryptedData", "recordHash"],
        "potential_checks": "recordHash = keccak256(_encryptedData)",
        "descriptions": "Ensure keccak256(_encryptedData) to validate data integrity."
        "reference": ["recordHash"]
    }}]
    "function_signature": "..."
    "checks": [
        {{
            "potential_checks": "...",
            "involved_variables": [...],
            "descriptions": "...",
            "reference": [...]
        }},
        ...
    ]
    }}

  
    """

    usr_content=f"""

      The general User Stories are: 
    <User Stories> 
    1. As a user, I want to open a margin position with specific parameters, so that I can trade with leverage while ensuring my collateral is properly managed.
    2. As a user, I want to increase my margin position by depositing additional collateral, so that I can maintain or enhance my trading capacity.
    3. As a user, I want to add stop-loss and take-profit orders to my margin positions, so that I can automate my trading strategy and manage risk effectively.
    4. As a user, I want to cancel my active orders if my trading conditions change, ensuring I have control over my trading actions.
    5. As a user, I want to repay my debt associated with a margin position, so that I can reduce my leverage and manage my financial exposure.
    6. As a user, I want to remove collateral from my margin position, so that I can retrieve my assets when I no longer need them.
    7. As a user, I want to view the details of my margin positions and orders, so that I can make informed trading decisions based on my current status.
    8. As a governor, I want to set and manage quote assets for trading pairs, ensuring that the trading environment remains flexible and responsive to market conditions.
    </User Stories>
    
    The Domain Models are:
    <Domain Models>  
        - ONE_E18:
            · Read restricted to None.
            · Write restricted to None.
        - ONE_E36:
            · Read restricted to None.
            · Write restricted to None.
        - GOVERNOR:
            · Read restricted to Contract only.
            · Write restricted to Contract only.
        - WNATIVE:
            · Read restricted to None.
            · Write restricted to Contract only (immutable).
        - swapHelper:
            · Read restricted to Contract only.
            · Write restricted to Contract only.
        - __quoteAssets: mapping(address => mapping(address => address)) private __quoteAssets;
            · Read restricted to Contract only.
            · Write restricted to Contract only.
        - __orders: mapping(uint => Order) private __orders;
            · Read restricted to Order owner (user) and Contract only.
            · Write restricted to Order owner (user) and Contract only.
        - __marginPositions: mapping(uint => MarginPos) private __marginPositions;
            · Read restricted to Position owner (user) and Contract only.
            · Write restricted to Position owner (user) and Contract only.
        - __posOrderIds: mapping(uint => uint[]) private __posOrderIds;
            · Read restricted to Position owner (user) and Contract only.
            · Write restricted to Position owner (user) and Contract only.
        - lastOrderId:
            · Read restricted to Contract only.
            · Write restricted to Contract only.
    </Domain Models>
    The function is:
    <Function>
    {{"function updateOrder(
        uint _posId,
        uint _orderId,
        uint _triggerPrice_e36,
        address _tokenOut,
        uint _limitPrice_e36,
        uint _collAmt
    ) external;":{{
    "write_state_variables": [
    __orders]
    "read_state_variables": [
    initPosIds,
    __marginPositions]
    }}
    "function openPos(
        uint16 _mode,
        address _viewer,
        address _tokenIn,
        uint _amtIn,
        address _borrPool,
        uint _borrAmt,
        address _collPool,
        bytes calldata _data,
        uint _minHealth_e18
    ) returns (uint posId, uint initPosId, uint health_e18)": {{"write_state_variables": [
    __marginPositions,
    posId,initPosIds
    "read_state_variables": []

    }}
    </Function>
    """
    try:
        client= OpenAI(api_key=OPENAI_API_KEY,http_client=httpx.Client(proxy=proxy_1))
        response = client.beta.chat.completions.parse(
                            model=model,
                            messages=[
                                {"role": "system", "content": role_content},
                                {"role": "user", "content": usr_content},
                            ],
                            temperature = 0,
                            seed=0,
                            response_format=FunctionChecksListResponse
    
                        )
        
        res=json.loads(response.choices[0].message.content)
    except Exception as e:
        print('Error in response')
        print(e)
        return None
    return res

if __name__ == "__main__":
    res=summarize_by_LLMs("test","test")#,'ft:gpt-4.1-mini-2025-04-14:hkust-cybersecurity-lab::BieHcNJb')
    with open('/home/liuhan/utils_download/checks_test_41_order1.json','w') as f:
        json.dump(res, f, indent=4)