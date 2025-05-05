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
    You are a smart contract developer expert. Given User Stories, your task is to derive Domain Models that strictly enforce isolation of read/write operations on state variables across users and contracts, with cryptographic integrity guarantees. You will be provided with several examples of Domain Models and their corresponding User Stories. These examples have the same scenario as the one you are given. 

    Instructions:
    1. User Stories Learning
    - Analyze provided User Stories to identify:
        · Actors: User types (e.g., regular users, admins) and contract types (e.g., parent/external contracts).
        · Isolation Needs: Variables requiring read/write isolation (e.g., user-specific balances, contract-specific settings).
        · Encryption Triggers: Data where blockchain transparency conflicts with privacy (e.g., sensitive user details).
    2. Design Domain Models
    Derive models exclusively addressing:
    - Read/Write Isolation:
        · How variables restrict read/write access per actor (e.g., private variables with getter/setter functions).
        · Example: 
            _profile: mapping(address => bytes32) private _profile;
            - This mapping ensures that each user's profile is isolated and can only be accessed by the user themselves.
    - Cross-Actor Isolation:
        · Separation between user-user and user-contract states (e.g., internal variables for inherited contracts).
    - Integrity & Encryption:
        · Use of keccak256 or other hashing to ensure data integrity of some private data (e.g., luckyNumber = keccak256(_luckyNumber)).
        
    3. Output Format
    You should only output the Domain Models of the contract.
    The Domain Models are:  
    <Domain Models>  
    - [State Variable 1]:
        · [Description of how it enforces isolation]
    - [State Variable 2]:
        · [Description of how it enforces isolation] 
    </Domain Models>

    The EXAMPLES are:
    {examples}

    """


    try:
        client= OpenAI(api_key=OPENAI_API_KEY,http_client=httpx.Client(proxy=proxy_1))
        response = client.chat.completions.create(
                            model=model,
                            messages=[
                                {"role": "system", "content": role_content},
                                {"role": "user", "content": f'''The user stories are <User Stories> {desc} </User Stories>.
                                        The state variables are 
                                        <State Variables>
                                        IERC1155 public immutable erc1155Contract;
                                        IERC721 public immutable erc721Contract;
                                        uint256 public immutable tokenID;

                                        uint256 public constant _maxTotalSupply = 431_386_000 * 1e18;
                                        uint256 private constant ERC721_RATIO = 400 * 1e18; // 1 ERC721 = 400 * 10^18 ERC20
                                        uint256 private constant ERC1155_RATIO = 400_000 * 1e18; // 1 ERC1155 = 400_000 * 10^18 ERC20

                                        address private constant _mintAddress01 = address(0x7A1B3bA1a848696f2AD29dC85923DCA078F1bF1E);
                                        address private constant _mintAddress02 = address(0x49b7f6414999551FA27C2b3abd588928A6334C96);
                                        address private constant _mintAddress03 = address(0x8f9e2f10CC75D7e765F5fB7fCAcE8A3fDE9D23FF);
                                        address private constant _mintAddress04 = address(0x5222f9facd6998DE73d45175efE56A38639Ed10b);
                                        address private constant _mintAddress05 = address(0xbB8891671e8FA53E616bb826C800d78C748fe963);
                                        address private constant _mintAddress06 = address(0x6A355388555433CD876D1C01485523Ec1f464690);
                                        address private constant _mintAddress07 = address(0xa9F6299A7DEAafc4a92AcB73fdF02ED4C72ce3b2);
                                        address private constant _mintAddress08 = address(0xa9F6299A7DEAafc4a92AcB73fdF02ED4C72ce3b2);

                                        // total init mint: 258_831_600 * 10^18
                                        uint256 private constant _mintAmount01 = 172_554_400 * 1e18;
                                        uint256 private constant _mintAmount02 = 3_451_088 * 1e18;
                                        uint256 private constant _mintAmount03 = 9_490_492 * 1e18;
                                        uint256 private constant _mintAmount04 = 14_365_154 * 1e18;
                                        uint256 private constant _mintAmount05 = 8_627_720 * 1e18;
                                        uint256 private constant _mintAmount06 = 21_569_300 * 1e18;
                                        uint256 private constant _mintAmount07 = 14_408_292 * 1e18;
                                        uint256 private constant _mintAmount08 = 14_365_154 * 1e18;

                                        bool private _opened;
                                        mapping(address account => uint256) private _balances;

                                        mapping(address account => mapping(address spender => uint256)) private _allowances;

                                        uint256 private _totalSupply;

                                        string private _name;
                                        string private _symbol;
                                        address private _owner;

                                        </State Variables>
                                        '''},
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
    root_path = f"/home/liuhan/utils_download/similar_code{temp_cou}"
    os.makedirs(root_path, exist_ok=True)
    example_str=""
    cou=0
    for file in tqdm(os.listdir(root_path)):
        if file.endswith('_gpt4omini_withgraph.txt'):
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