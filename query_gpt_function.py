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
    You are now acting as a smart contract developer expert. You are given a scenario and a few requirements of smart contracts, and your task is to analyze and summarize the potential checks based on the given function signature.
    Instructions:
    1. Scenario and Requirements Learning
    You are given a scenario and a few examples of the scenarios and their corresponding requirements of smart contracts.
    Carefully examine the scenarios and their corresponding requirements. Consider how can the requirements be realized in the contract.
    2. Analyze the function checks
    Based on the given function signature, you need to analyze the potential checks for the contract.
    - You need to analyze the arguments of the function signature, consider what are the contributions of the arguments to the function.
    - You can use the global variables in the contract to help you analyze the function, i.e., msg.sender, msg.value, block.timestamp, etc.
    - You will also be given some state variables, you need to analyze the state variables and consider how can the state variables be used in the function.
    - You need to analyze the requirements, consider how can the requirements be realized in the contract.
    - You should also consider the potential checks between the arguments, because the arguments can be well-designed to bypass the checks.
    - YOUR DESIGNED CHECKS MUST ONLY REFLECT THE ISOLATION OF THE STATE VARIABLES OF DIFFERENT USERS, TRANSACTIONS, AND CONTRACTS. SHOULD NOT INCLUDE ANY OTHER FUNCTIONALITY OR SECURITY REQUIREMENTS.
    - DO NOT INCLUDE ANY STATE VARIABLES IN THE CHECKS.
    3. Output Format
    - Please provide a set of arguments and global variables that might need to be compared. Please do not use state variables.
    - The output should be a json format, with the keys being a list of arguments and global variables that might need to be compared, and the values being the descriptions of the comparisons.
    - THE VARIABLE NAME MUST BE THE SAME AS THE FUNCTION SIGNATURE.
    - YOU SHOULD USE THE ARGUMENTS OF THE FUNCTION AND THE GLOBAL VARIABLES (e.g., msg.sender, msg.value, block.timestamp, etc.) TO HELP YOU TO DESIGN THE CHECKS.
    - YOU ONLY NEED TO OUTPUT THE JSON OBJECT, DO NOT OUTPUT ANY OTHER TEXT.    

    For example, the output should be like this:
    {{
        ["msg.sender","from","amount"]:"Compare the allowed amount of the sender with the amount to be transferred."
    }}

    The scenario is:
    <Scenario>
    The `MarginTradingHook` contract is designed to facilitate margin trading within a decentralized finance (DeFi) ecosystem. It allows users to open and manage leveraged positions on various assets, utilizing collateral and borrowing mechanisms. The contract supports functionalities such as opening positions, increasing margin, adding or removing collateral, repaying debt, and placing stop-loss or take-profit orders. It interacts with lending pools and utilizes a swap helper for token exchanges, ensuring efficient management of collateral and debt. Unique features include the ability to handle native token deposits and refunds, as well as a structured order management system for executing trades based on market conditions. The contract also incorporates security measures through role-based access control and health checks for positions, ensuring that users maintain adequate collateralization.
    </Scenario>.

    The requirements are:
    <Requirements>
    <requirement> The contract must ensure that each user's leveraged positions are isolated, preventing unauthorized access to another user's position data.</requirement>
    <requirement> The contract must ensure that collateral and debt amounts for each user are accurately tracked and cannot be manipulated by other users or transactions.</requirement>
    <requirement> The contract must ensure that all orders placed by users, including stop-loss and take-profit orders, are uniquely identified and cannot be accessed or modified by unauthorized parties.</requirement>
    <requirement> The contract must ensure that the state variables related to each user's margin trading activities, such as collateral, debt, and position status, are maintained separately to prevent interference from other users.</requirement>
    </Requirements>

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
    The state variables are:
    <state_variables>
    address public immutable CORE;
    address public immutable POS_MANAGER;
    mapping(address => uint) public lastPosIds;
    mapping(address => mapping(uint => uint)) public initPosIds;
    uint private constant ONE_E18 = 1e18;
    uint private constant ONE_E36 = 1e36;
    bytes32 private constant GOVERNOR = keccak256('governor');
    address public immutable WNATIVE;
    address public swapHelper;
    mapping(address => mapping(address => address)) private __quoteAssets;
    mapping(uint => Order) private __orders;
    mapping(uint => MarginPos) private __marginPositions;
    mapping(uint => uint[]) private __posOrderIds;
    uint public lastOrderId;
    </state_variables>
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
                        )
    except Exception as e:
        print('Error in response')
        print(e)
        return None
    return response.choices[0].message.content

if __name__ == "__main__":
    res=summarize_by_LLMs("test","test")
    with open('/home/liuhan/utils_download/checks_test_gpt4omini.txt','w') as f:
        f.write(res)