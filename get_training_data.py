import os
import json
path = '/home/liuhan/utils_download/most_unrelated'
base_prompt="""
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
    - NOTE THAT DO NOT CONTAIN ANY LOGIC OF THE FUNCTIONALITY, LIKE ASSIGNMENTS OR ADD OR SUBTRACTION, I.E., +=, -=, ETC.
      YOU JUST NEED TO FOCUS ON THE ISOLATION CHECKS AND ENCRYPTION-FOCUSED CHECKS.
        - For example, [the amount should add to the balance of the user, i.e., _balances[msg.sender] = _balances[msg.sender] + amount.] should not be included in the output.
    - TRY TO SPLIT THE CHECKS IF THE CHECKS ARE TWO PURPOSES, YOU CAN SPLIT THEM INTO TWO PARTS.
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
    Each part should be a dictionary, for example, the output should be like this:
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

"""
def get_training_data(path):
    training_data = []
    for file in os.listdir(path):
        if file.endswith('_domain_model.txt'):
            with open(os.path.join(path, file), 'r') as f:
                domain = f.read()
            check_path = os.path.join(path, file.replace('_domain_model.txt', '_4condition.json'))
            with open(check_path, 'r') as f:
                func = json.load(f)
            func_str = str(func)
            usr_path = os.path.join(path, file.replace('.sol', '_1user.txt'))
            with open(usr_path, 'r') as f:
                usr = f.read()
            func_signature_path = os.path.join(path, file.replace('_domain_model.txt', '_function_signature.json'))
            with open(func_signature_path, 'r') as f:
                func_signature = json.load(f)
            func_signature_str = str(func_signature)
            usr_context = f""" User Stories: 
            <User_Stories> {usr} <\User_Stories>
            Domain Models: 
            <Domain_Models>{domain}<\Domain_Models>
            Function Signature: 
            <Function_Signature>{func_signature_str}<\Function_Signature\n"""
            message = [
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
            ]
            training_data.append(message)

            
    return training_data
if __name__ == "__main__":
    training_data = get_training_data(path)
    with open('/home/liuhan/utils_download/training_data.jsonl', 'w') as f:
        for data in training_data:
            json.dump(data, f)
            f.write('\n')
    print(f"Total {len(training_data)} training data collected.")