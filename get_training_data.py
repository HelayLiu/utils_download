import os
import json
import tiktoken
path = '/home/liuhan/utils_download/most_unrelated'
base_prompt=f"""
    Role: You are a smart contract security architect. Given User Stories and Domain Models, your task is to analyze the function and derive checks/constraints that enforce the read/write isolation of state variables.
    Instructions:
    1. User Stories & Domain Models Learning
    - Review User Stories to identify:
        · Actors: User types (e.g., regular users, admins) and contracts.
        · Corresponding Domain Models with the given state variables.
        · Isolation Rules: Domain Models defining state variable isolation rules, such as writing access control and encryption requirements for reading state variables.
    2. Function Analysis
    - Analyze the function signature, read/write state variables, and the summary of the functionality to identify their roles and contributions; you should understand what the function is doing.
    - For each function, if it contains read/write state variables that enable isolation checks in the Domain Models, you should generate the isolation checks and constraints for the function.
        - Read Isolation:
            · For each read state variable, ensure it hashes the variable if it is required by the Domain Models (e.g., using keccak256).
        - Write Isolation:
            · For each written state variable, ensure it restricts the write access to the specific user or contract as defined in the Domain Models.
        *** KEEP IN MIND NEVER IGNORE THE KEY CHECKS IF IT CAN CAUSE SIGNIFICANT LOSS ***
    - DO NOT CONTAIN ANY LOGIC OF THE FUNCTIONALITY, LIKE ASSIGNMENTS OR ADD OR SUBTRACTION, I.E., +=, -=, ETC.
      YOU JUST NEED TO FOCUS ON THE ISOLATION CHECKS, i.e., the checks that ensure read (e.g., hashing variable) and write (e.g., enabling access control) isolation of the state variables.
        - For example, [the amount should add to the balance of the user, i.e., _balances[msg.sender] = _balances[msg.sender] + amount.] should not be included in the output.
    - TRY TO SPLIT THE CHECKS IF THEY USE AND.
        - For example, 
            [
                {{
                    "involved_variables": ["msg.sender", "_patient", "msg.value"],
                    "potential_checks": "msg.sender == _patient && msg.value > 0",
                    "descriptions": "Verify msg.sender == _patient to enforce write access to _encryptedRecords and msg.value > 0 to ensure a valid transaction."
                    "reference": ["_balances"]
                }}
            ]
            You should split them into two parts:
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
        - If the checks are intended to achieve a similar goal, you should union them.
           · For example, if two of the state variables both need to check the ownership of the user, you can union them together.
              i.e., _balances[msg.sender] and _allowances[msg.sender][spender] should both check the authorization of the user, i.e., msg.sender == authorizedUser, you can union them together.

    4. Output Format
    You should ONLY output a JSON object in the following format without any additional text. 
    The JSON objects should be a dictionary with the following fields:
    - Keys:   The function signature of the function, e.g., function submitNumber(uint256 _number) public payable.
    - Values: A list of checks that should be done in the function, each check is a JSON object with the following fields:
        - Involved variables: A list of all the involved variables of the checks in the function signature and global variables, e.g, msg.sender, _patient, _encryptedData, recordHash, etc. 
        - Potential checks: The specific constraints of the potential checks should be done in the function, e.g., A == B, C = keccak256(D), etc. 
        - Descriptions: A sentence of the description of the isolation checks and encryption-focused checks.
        - Reference: A list of all the state variables that lead to the checks, e.g., _balances, _encryptedData, recordHash, etc.
    For example, the output should be like this:
    {{
        "function submitNumber(uint256 _number) public payable":
        [
            {{
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
            }}
        ]
        "<function_signature>": 
        [
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
def len_token(text: str, model: str = 'gpt-4o-mini', max_token=128000) -> int:
    try:
        encoding = tiktoken.encoding_for_model(model)
    except KeyError:
        encoding = tiktoken.get_encoding("cl100k_base")
    tokens = encoding.encode(text)
    len_tokens = len(tokens)
    return  len_tokens
    
def get_training_data(path):
    training_data = []
    total_tokens = 0
    # for file in os.listdir(path):
        # if file.endswith('_2model.txt'):
        #     with open(os.path.join(path, file), 'r') as f:
        #         domain = f.read()
        #     check_path = os.path.join(path, file.replace('_2model.txt', '_4condition_new.json'))
        #     with open(check_path, 'r') as f:
        #         func = json.load(f)
        #     func_str = str(func)
        #     usr_path = os.path.join(path, file.replace('.sol', '_1user.txt'))
        #     with open(usr_path, 'r') as f:
        #         usr = f.read()
        #     func_signature_path = os.path.join(path, file.replace('_2model.txt', '_function_wrv.json'))
        #     with open(func_signature_path, 'r') as f:
        #         func_signature = json.load(f)
        #     func_signature_str = str(func_signature)
        #     usr_context = f""" User Stories: 
        #     <User_Stories> {usr} </User_Stories>
        #     Domain Models: 
        #     <Domain_Models>{domain}</Domain_Models>
        #     Function Signature: 
        #     <Functions>{func_signature_str}</Functions>"""
        #     tokens = base_prompt + usr_context + func_str
        #     lens= len_token(tokens)
        #     message = {"messages":[
        #         {
        #             "role": "system",
        #             "content": base_prompt
        #         },
        #         {
        #             "role": "user",
        #             "content": usr_context
        #         },
        #         {
        #             "role": "assistant",
        #             "content": func_str
        #         }
        #     ]}
        #     training_data.append(message)
        #     total_tokens += lens
    for file in os.listdir(path):
        if file.endswith('domain_models_41_mini_res.txt'):
            with open(os.path.join(path, file), 'r') as f:
                domain = f.read()
            check_path = os.path.join(path, file.replace('domain_models_41_mini_res.txt', '_4condition_new.json'))
            with open(check_path, 'r') as f:
                func = json.load(f)
            func_str = str(func)
            usr_path = os.path.join(path, file.replace('.sol', '_1user.txt'))
            with open(usr_path, 'r') as f:
                usr = f.read()
            func_signature_path = os.path.join(path, file.replace('domain_models_41_mini_res.txt', '_function_wrv.json'))
            with open(func_signature_path, 'r') as f:
                func_signature = json.load(f)
            func_signature_str = str(func_signature)
            usr_context = f""" User Stories: 
            <User_Stories> {usr} </User_Stories>
            Domain Models: 
            <Domain_Models>{domain}</Domain_Models>
            Function Signature: 
            <Functions>{func_signature_str}</Functions>"""
            tokens = base_prompt + usr_context + func_str
            lens= len_token(tokens)
            message = {"messages":[
                {
                    "role": "system",
                    "content": base_prompt
                },
                {
                    "role": "user",
                    "content": usr_context
                },
                {
                    "role": "assistant",
                    "content": func_str
                }
            ]}
            training_data.append(message)
            total_tokens += lens
    for file in os.listdir(path):
        if file.endswith('domain_models_o4_mini_res.txt'):
            with open(os.path.join(path, file), 'r') as f:
                domain = f.read()
            check_path = os.path.join(path, file.replace('domain_models_o4_mini_res.txt', '_4condition_new.json'))
            with open(check_path, 'r') as f:
                func = json.load(f)
            func_str = str(func)
            usr_path = os.path.join(path, file.replace('.sol', '_1user.txt'))
            with open(usr_path, 'r') as f:
                usr = f.read()
            func_signature_path = os.path.join(path, file.replace('domain_models_o4_mini_res.txt', '_function_wrv.json'))
            with open(func_signature_path, 'r') as f:
                func_signature = json.load(f)
            func_signature_str = str(func_signature)
            usr_context = f""" User Stories: 
            <User_Stories> {usr} </User_Stories>
            Domain Models: 
            <Domain_Models>{domain}</Domain_Models>
            Function Signature: 
            <Functions>{func_signature_str}</Functions>"""
            tokens = base_prompt + usr_context + func_str
            lens= len_token(tokens)
            message = {"messages":[
                {
                    "role": "system",
                    "content": base_prompt
                },
                {
                    "role": "user",
                    "content": usr_context
                },
                {
                    "role": "assistant",
                    "content": func_str
                }
            ]}
            training_data.append(message)
            total_tokens += lens
            
    return training_data, total_tokens
if __name__ == "__main__":
    training_data,total_tokens = get_training_data(path)
    print(f"Total tokens in training data: {total_tokens}")
    print(f"Total cost for training data: {(total_tokens)/1000000 * 5} USD")
    with open('/home/liuhan/utils_download/training_data.jsonl', 'w') as f:
        for data in training_data:
            json.dump(data, f)
            f.write('\n')
    print(f"Total {len(training_data)} training data collected.")