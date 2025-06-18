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
def summarize_by_LLMs(funcs,examples,model="gpt-4.1-mini"):
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
    In your response, you should include three parts:
    - Involved variables: A list of all the involved variables of the checks in the function signature and global variables, e.g, msg.sender, _patient, _encryptedData, recordHash, etc. 
    - Potential checks: The specific constraints of the potential checks should be done in the function, e.g., A == B, C = keccak256(D), etc. 
    - Descriptions: A sentences of the description of the isolation checks and encryption-focused checks.
    - Reference: A list of all the state variables that lead to the isolation checks and encryption-focused checks.
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
- As an owner, I want to securely manage the contract by changing ownership, pausing, unpausing, draining native funds, and migrating to a new contract, so that I can maintain control and ensure safe upgrades or emergency stops.  
- As a message relayer (L2 message relayer), I want to send and receive authenticated messages between L2 and L1, ensuring only authorized relayers can interact with the contract to maintain secure cross-chain communication.  
- As a deposit processor on L1, I want to send staking requests to L2, so that tokens can be staked on behalf of targets on L2 in a controlled and verifiable manner.  
- As a staking target, I want to receive approved OLAS token deposits for staking, ensuring that only valid and verified staking targets receive tokens, and that amounts do not exceed allowed limits.  
- As a user or system interacting with the contract, I want queued staking requests to be redeemable later if immediate staking is not possible (e.g., due to paused state or insufficient balance), so that no staking incentives are lost and can be processed when conditions allow.  
- As the contract, I want to isolate write access by enforcing ownership and relayer-only permissions, preventing unauthorized state changes or message processing.  
- As the contract, I want to isolate read access by restricting sensitive state changes and event emissions to authorized actors, ensuring that only relevant parties can observe or trigger state transitions.  
- As the contract, I want to maintain internal state isolation per staking batch nonce and target, so that staking requests and withheld amounts are tracked individually and securely without interference between different users or batches.  
- As the contract, I want to withhold OLAS tokens for invalid or excessive staking requests, isolating these amounts until they can be resolved or synced back to L1, ensuring that invalid requests do not affect valid staking operations.  
- As the contract, I want to prevent reentrancy attacks by using a locking mechanism during critical state changes, ensuring that user-specific state updates are atomic and isolated.  
- As the DAO or owner, I want to manually process or restore staking data that failed to be delivered from L1, so that the system can recover from bridge or message delivery failures without losing user funds or state.  
    </User Stories>
    

    The Domain Models are:
    <Domain Models>  
        - owner: address public  
            · Write restricted to current owner only (ownership transfer functions).  
            · Read unrestricted (public).  

        - paused: uint8 public  
            · Write restricted to owner only (pause/unpause functions).  
            · Read unrestricted (public).  

        - _locked: uint8 internal  
            · Write restricted internally to contract during critical state changes to prevent reentrancy.  
            · Read restricted internally (private).  

        - withheldAmount: uint256 public  
            · Write restricted to internal contract logic managing invalid or excessive staking requests and manual recovery by owner/DAO.  
            · Read unrestricted (public).  

        - stakingBatchNonce: uint256 public  
            · Write restricted to internal contract logic incrementing per staking batch processed.  
            · Read unrestricted (public).  
            · Isolates staking batches to track requests and state per batch nonce.  

        - stakingQueueingNonces: mapping(bytes32 => bool) public  
            · Write restricted to internal contract logic managing queued staking requests per unique nonce and target.  
            · Read unrestricted (public).  
            · Isolates queued staking requests per batch nonce and target to prevent interference.  

        - olas: address public immutable  
            · Write restricted to contract deployment only (immutable).  
            · Read unrestricted (public).  

        - stakingFactory: address public immutable  
            · Write restricted to contract deployment only (immutable).  
            · Read unrestricted (public).  

        - l2MessageRelayer: address public immutable  
            · Write restricted to contract deployment only (immutable).  
            · Read unrestricted (public).  
            · Write access restricted in functions to only this relayer for message sending/receiving.  

        - l1DepositProcessor: address public immutable  
            · Write restricted to contract deployment only (immutable).  
            · Read unrestricted (public).  
            · Write access restricted in functions to only this processor for sending staking requests.  

        - l1SourceChainId: uint256 public immutable  
            · Write restricted to contract deployment only (immutable).  
            · Read unrestricted (public).  

        - l2TokenRelayer: address public immutable  
            · Write restricted to contract deployment only (immutable).  
            · Read unrestricted (public).  

        - RECEIVE_MESSAGE: bytes4 public constant  
            · Immutable constant, no write access after deployment.  
            · Read unrestricted (public).  

        - MAX_CHAIN_ID: uint256 public constant  
            · Immutable constant, no write access after deployment.  
            · Read unrestricted (public).  

        - GAS_LIMIT: uint256 public constant  
            · Immutable constant, no write access after deployment.  
            · Read unrestricted (public).  

        - MAX_GAS_LIMIT: uint256 public constant  
            · Immutable constant, no write access after deployment.  
            · Read unrestricted (public).  

        - BRIDGE_PAYLOAD_LENGTH: uint256 public constant  
            · Immutable constant, no write access after deployment.  
            · Read unrestricted (public).  
    </Domain Models>

    The functions are:
    <Functions>
    {funcs}
    </Functions>
    """
    #     This function doing the following functionality:
    # The function validates the token ID, potentially mints new tokens for the sender based on the received amount and a predefined ratio (ERC1155_RATIO), and always returns its function selector to acknowledge the receipt of ERC-1155 tokens.
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
        json_res = json.loads((response.choices[0].message.content))
    except Exception as e:
        print('Error in response')
        print(e)
        return None
    print(f"Prompt tokens: {response.usage.prompt_tokens}")
    print(f"Completion tokens: {response.usage.completion_tokens}")
    return json_res

if __name__ == "__main__":
    with open('/home/liuhan/utils_download/test_contract4_function_wrv.json','r') as f:
        content = json.load(f)
    res=summarize_by_LLMs(content,"test")#,model="ft:gpt-4.1-mini-2025-04-14:hkust-cybersecurity-lab::BieHcNJb")
    with open('/home/liuhan/utils_download/checks4_test_.json','w') as f:
        json.dump(res,f,indent=4)