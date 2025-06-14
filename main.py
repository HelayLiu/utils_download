from process_condition import *
from tqdm import tqdm
def split(data):
    lines= data.split('\n')
    usr = []
    model = []
    checks = []
    is_thinking = False
    is_user = False
    is_model = False
    is_check = False
    for line in lines:
        if '<THINKING_CONTENT>' in line:
            is_thinking = True
            continue
        if '</THINKING_CONTENT>' in line:
            is_thinking = False
            continue
        if is_thinking:
            continue
        if '<User Stories>' in line:
            is_user = True
            continue
        if '</User Stories>' in line:
            is_user = False
            continue
        if '<Domain Models>' in line:
            is_model = True
            continue
        if '</Domain Models>' in line:
            is_model = False
            continue
        if '<Specific Checks in Functions>' in line:
            is_check = True
            continue
        if '</Specific Checks in Functions>' in line:
            is_check = False
            continue
        
        line = line.replace('**', '')
        if is_user:
            usr.append(line)
        elif is_model:
            model.append(line)
        elif is_check:
            checks.append(line)
    return usr, model, checks
if __name__ == "__main__":
    path="/home/liuhan/utils_download/most_unrelated"
    files=["105","106","107","108","109","100","101","102","103","104"]
    # for file in tqdm(os.listdir(path)):
    for f in tqdm{files}:
        file=f"most_unrelated_{f}.sol"
        if file.endswith('.sol'):
            # if os.path.exists(os.path.join(path, file.replace('.sol', '_state.txt'))):
            #     continue
            # all_state= get_all_state_variables(path, file)
            # with open(os.path.join(path, file.replace('.sol', '_state.txt')), 'w') as f:
            #     f.write('\n'.join(all_state))
            condition_save_path=os.path.join(path,file.replace('.sol','_4condition.json'))
            if os.path.exists(condition_save_path):
                continue
            condition=get_conditions(path,file)
            ds_generate_path=os.path.join(path,file.replace('.sol','_deepseek_res.txt'))
            with open(ds_generate_path, 'r') as f:
                data = f.read()
            usr, model, checks = split(data)
            with open(condition_save_path, 'w') as f:
                json.dump(condition, f, indent=4)
            usr_save_path=os.path.join(path,file.replace('.sol','_1user.txt'))
            with open(usr_save_path, 'w') as f:
                f.write('\n'.join(usr))
            model_save_path=os.path.join(path,file.replace('.sol','_2model.txt'))
            with open(model_save_path, 'w') as f:
                f.write('\n'.join(model))
            checks_save_path=os.path.join(path,file.replace('.sol','_3checks.txt'))
            with open(checks_save_path, 'w') as f:
                f.write('\n'.join(checks))

