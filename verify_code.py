from pymongo import MongoClient
import json
from tqdm import tqdm
import ast
import os
def export_multifile(docs,output_folder):
    sourceCode=docs['source']
    contractFolder=os.path.join(output_folder,chain_id, docs['address'])
    contract_name=docs['contract_name']
    for key in sourceCode.keys():
        contractName = key
        if key.endswith(f'{contract_name}.sol'):
            flatten_path=os.path.join(contractFolder, key)
        # print(contractName)
        while os.path.exists(contractFolder + "//" + contractName):
            contractName = key.split(".sol")[0] + "_{}".format(index) + ".sol"
            index += 1
        index = 0
        os.makedirs(os.path.split(contractFolder + "//" + contractName)[0],exist_ok=True)
        with open(contractFolder + "//" + contractName, "w+", encoding='utf-8') as fw:
            fw.write(sourceCode[key]["content"].replace('\r\n', '\n'))
def fix_code(code):
    code_split = code.split('"content":')
    new_code = []
    for code_snippet in code_split:
        if '"source:"' in code_snippet or '"language":' in code_snippet:
            new_code.append(code_snippet)
            continue
        temp = code_snippet.split('"\r\n    }')[0]
        temp = temp.replace('\r', '\\r')
        temp = temp.replace('\n', '\\n')
        temp = temp.replace('\t', '\\t')
        temp = temp+'"\r\n    }'+code_snippet.split('"\r\n    }')[1]
        new_code.append(temp)
    new_code = '"content":'.join(new_code)
    return new_code
if __name__ == "__main__":
    client = MongoClient("mongodb://shuaicpu5.cse.ust.hk:27017/")
    collection_source=client['contracts']['top_contracts']
    # 查询MongoDB集合中的所有文档
    documents = collection_source.find({'source':{'$ne':''}},{})
    all_contracts = []
    cou=0
    for doc in documents:
        id=doc['_id']
        address=doc['address']
        chain_id=doc['chain_id']
        source=doc['source']
        contract_name=doc['contract_name'] if 'contract_name' in doc else ''
        if contract_name=='':
            cou+=1
            continue
        if source.startswith('{'):
            # try:
            try:
                source_load=json.loads(source)
                load_error=False
            except Exception as e:
                load_error=True
            if load_error:
                try:
                    fixed_json = source[1:-1]
                    source_load=json.loads(fixed_json)
                    load_error=False
                except Exception as e:
                    load_error=True
            if load_error:
                try:
                    fixed_json = fix_code(fixed_json)
                    source_load=json.loads(fixed_json)
                    load_error=False
                except Exception as e:
                    load_error=True
            if load_error:
                cou+=1
                print(f"Failed to load source code for address {address}.")
                continue

            if 'sources' in source_load:
                source_code=source_load['sources']
                try:
                    settings=source_load['settings']
                except Exception as e:
                    settings=None
            else:
                source_code=source
                settings=None
            # except Exception as e:
            #     print("error in save_to_mongodb")
            #     print("error line:", e.__traceback__.tb_lineno)
            #     print("error type:", e)
            #     cou+=1
            #     continue
            all_contracts.append({
                'address': address,
                'chain_id': chain_id,
                'source': source_code,
                'settings': settings,
                'contract_name': contract_name
            })
    print(cou)
    export_multifile(all_contracts[0],'/home/liuhan/utils_download/solc_source_code')