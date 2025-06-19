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
def main(doc):
    _id=doc['_id']
    try:

            # if "all_state" in doc and doc['all_state'] is not None:
            #     continue

        
        if not doc['success']:
            return
        if 'all_state' in doc and doc['all_state'] is not None  and doc['all_state'] != '':
            return
        code=doc['code']
        contract_name=doc['contract_name']
        version=doc['version'].split('+')[0].replace('v','')
        opt=True if doc['optimization']=='1' else False
        via_ir=doc.get('viaIR', False)
        with open(f"/home/liuhan/utils_download/{_id}.sol", 'w') as f:
            f.write(code)
        config= {
            'contract_name': contract_name,
            'version': version,
            'opt': opt, 
            'via_ir': via_ir,
        }
        with open(f"/home/liuhan/utils_download/{_id}.json", 'w') as f:
            json.dump(config, f, indent=4)
        
        all_state=get_all_state_variables("/home/liuhan/utils_download", f"{_id}.sol")

        all_state_str = '\n'.join(all_state)
        # collection_source.update_one(
        #     {'_id': _id},
        #     {'$set': {'all_state': all_state_str}}
        # )
        print(f"Processed contract {_id} successfully with {len(all_state)} state variables.")
    except Exception as e:
        print(f"Error processing contract {_id}: {e}")
        return
    finally:
        if os.path.exists(f"/home/liuhan/utils_download/{_id}.sol"):
            os.remove(f"/home/liuhan/utils_download/{_id}.sol")
        if os.path.exists(f"/home/liuhan/utils_download/{_id}.json"):
            os.remove(f"/home/liuhan/utils_download/{_id}.json")
if __name__ == "__main__":
    # from pymongo import MongoClient
    # client=MongoClient("mongodb://shuaicpu5.cse.ust.hk:27017/")
    # collection_source=client['contracts']['top_contracts']
    # docs=collection_source.find({'used':True},{'_id':1,'code':1,'contract_name':1,'version':1,'optimization':1,'viaIR':1,'success':1,'all_state':1})
    # for doc in tqdm(docs):
    #     main(doc)
    # docs=list(docs)
    # import multiprocessing
    # pool= multiprocessing.Pool(processes=20)
    # pool.map(main, docs)
    

    # all_state=get_all_state_variables("/home/liuhan/utils_download", "temp.sol")
    path="/home/liuhan/utils_download"
    file="test_contract4.sol"
    ll_funcs = get_func_sign_rw_v(path, file)
    # with open(os.path.join(path, file.replace('.sol', '_function_wrv.json')), 'w') as f:
    #     json.dump(ll_funcs, f, indent=4)
    # all_state= get_all_state_variables(path, file)
    # with open(os.path.join(path, file.replace('.sol', '_state.txt')), 'w') as f:
    #     f.write('\n'.join(all_state))
    # path="/home/liuhan/utils_download/most_unrelated"
    # # files=["105","106","107","108","109","100","101","102","103","104"]
    # for file in tqdm(os.listdir(path)):
    # # for f in tqdm(files):
    #     # file=f"most_unrelated_{f}.sol"
    #     if file.endswith('.sol'):
    #         # if file!= "most_unrelated_109.sol":
    #         #     continue
    #         # if os.path.exists(os.path.join(path, file.replace('.sol', '_state.txt'))):
    #         #     continue
    #         # all_state= get_all_state_variables(path, file)
    #         # with open(os.path.join(path, file.replace('.sol', '_state.txt')), 'w') as f:
    #         #     f.write('\n'.join(all_state))
    #         all_funcs = get_func_sign_rw_v(path, file)
    #         with open(os.path.join(path, file.replace('.sol', '_function_wrv.json')), 'w') as f:
    #             json.dump(all_funcs, f, indent=4)
            # condition_save_path=os.path.join(path,file.replace('.sol','_4condition.json'))
            # if os.path.exists(condition_save_path):
            #     continue
            # condition=get_conditions(path,file)
            # ds_generate_path=os.path.join(path,file.replace('.sol','_deepseek_res.txt'))
            # with open(ds_generate_path, 'r') as f:
            #     data = f.read()
            # usr, model, checks = split(data)
            # with open(condition_save_path, 'w') as f:
            #     json.dump(condition, f, indent=4)
            # usr_save_path=os.path.join(path,file.replace('.sol','_1user.txt'))
            # with open(usr_save_path, 'w') as f:
            #     f.write('\n'.join(usr))
            # model_save_path=os.path.join(path,file.replace('.sol','_2model.txt'))
            # with open(model_save_path, 'w') as f:
            #     f.write('\n'.join(model))
            # checks_save_path=os.path.join(path,file.replace('.sol','_3checks.txt'))
            # with open(checks_save_path, 'w') as f:
            #     f.write('\n'.join(checks))

