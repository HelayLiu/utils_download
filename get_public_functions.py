import os
import json
from utils import *
path="/home/liuhan/utils_download/most_unrelated"
for file in os.listdir(path):
    if file.endswith('.sol'):
        config_path= os.path.join(path, file.replace('.sol', '.json'))
        with open(config_path, 'r') as f:
            config = json.load(f)
        compiler_helper = CompilerHelper(os.path.join(path,file), version=config['version'], optimization=config['opt'], via_ir=config['via_ir'], contract_name=config['contract_name'])
        compiler_helper.get_slither()
        contract= compiler_helper._contract[0]
        all_functions= set()
        for func in contract.functions:
            if func.is_constructor or func.is_fallback or func.is_receive:
                continue
            if func.visibility=="public" or func.visibility=="external":
                all_functions.add(func.signature_str)
        with open(os.path.join(path, file.replace('.sol', '_public_functions.json')), 'w') as f:
            f.write(json.dumps(list(all_functions), indent=4, ensure_ascii=False))
        