import os
import json
from utils import *
from tqdm import tqdm
from process_condition import *
path="/home/liuhan/utils_download/most_unrelated"
# files=["105","106","107","108","109","100","101","102","103","104"]
for file in tqdm(os.listdir(path)):
# for f in files:
    if not file.startswith('most_unrelated_') or not file.endswith('.sol'):
        continue
    func_file=os.path.join(path, file.replace('.sol', '_public_functions_new.json'))
    with open(func_file, 'r') as f:
        func = json.load(f)
    check_file = os.path.join(path, file.replace('.sol', '_4condition.json'))
    with open(check_file, 'r') as f:
        checks = json.load(f)
    new_checks = {}
    for fn in checks:
        if fn in func:
            new_checks[fn] = checks[fn]
    new_checks_file = os.path.join(path, file.replace('.sol', '_4condition_new.json'))
    with open(new_checks_file, 'w') as f:
        json.dump(new_checks, f, indent=4)