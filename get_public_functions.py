import os
import json
from utils import *
from tqdm import tqdm
path="/home/liuhan/utils_download/most_unrelated"
# files=["105","106","107","108","109","100","101","102","103","104"]
for file in tqdm(os.listdir(path)):
# for f in files:
    if not file.startswith('most_unrelated_') or not file.endswith('.sol'):
        continue
    config_path= os.path.join(path, file.replace('.sol', '.json'))
    with open(config_path, 'r') as f:
        config = json.load(f)
    compiler_helper = CompilerHelper(os.path.join(path,file), version=config['version'], optimization=config['opt'], via_ir=config['via_ir'], contract_name=config['contract_name'])
    compiler_helper.get_slither()
    contract= compiler_helper._contract[0]
    all_functions= set()
    for func in contract.functions:
        if func.is_constructor or func.is_fallback or func.is_receive or func.is_shadowed:
            continue
        if func.visibility=="public" or func.visibility=="external":
            fn = func
            function_name = fn.signature[0]
            function_args = ''
            for i in range(len(fn.parameters)):
                if function_args != '':
                    function_args += ', '
                param = fn.parameters[i]
                function_args += f'{fn.signature[1][i]} {param.name}'
            function_name += f'({function_args})'
            function_returns = ', '.join(fn.signature[2])
            function_name += f' returns ({function_returns})' if function_returns else ''
            all_functions.add(function_name)
    with open(os.path.join(path, file.replace('.sol', '_public_functions_new.json')), 'w') as f:
        json.dump(list(all_functions), f, indent=4)
        