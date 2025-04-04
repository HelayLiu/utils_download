from pymongo import MongoClient
import json
from tqdm import tqdm
import shutil
import os
import subprocess
def export_multifile(docs,output_folder):
    sourceCode=docs['source']
    chain_id=docs['chain_id']
    contractFolder=os.path.join(output_folder,chain_id, docs['address'])
    contract_name=docs['contract_name']
    flag=False
    for key in sourceCode.keys():
        contractName = key
        if key.endswith(f'/{contract_name}.sol') or key==f'{contract_name}.sol':
            flag=True
            flatten_path=os.path.join(contractFolder, key)
            if '/' in key:
                contract_path = key.replace(key.split('/')[-1], '')
            else:
                contract_path = '.'
            # if 'src' in key:
            #     contract_path = 'src'
            # elif 'contracts' in key:
            #     contract_path = 'contracts'
            # else:
            #     contract_path = key.split('/')[0]
        # print(contractName)
        while os.path.exists(contractFolder + "//" + contractName):
            contractName = key.split(".sol")[0] + "_{}".format(index) + ".sol"
            index += 1
        index = 0
        os.makedirs(os.path.split(contractFolder + "//" + contractName)[0],exist_ok=True)
        with open(contractFolder + "//" + contractName, "w+", encoding='utf-8') as fw:
            fw.write(sourceCode[key]["content"].replace('\r\n', '\n'))
    if not flag:
        for key in sourceCode.keys():
            if f'contract {contract_name} is' in sourceCode[key]["content"] or "contract {} {".format(contract_name) in sourceCode[key]["content"]:
                flag=True
                flatten_path=os.path.join(contractFolder, key)
    return contractFolder,contract_path,flatten_path

def forge_init(path,contract_path, flatten_path,version,viair,remappings,evmVersion):
    forge_init_cmd = f"forge init . --force --no-git"
    subprocess.run(forge_init_cmd, shell=True, stderr=subprocess.PIPE, stdout=subprocess.PIPE, cwd=path)
    with open(os.path.join(path, "foundry.toml"), "r") as f:
        lines = f.readlines()
    flag=False
    for i, line in enumerate(lines):
        if "src =" in line:
            lines[i] = f'src = "{contract_path}"\n'
        # if "lib/" in line or "libs/" in line:
        #     lines[i] = line.replace('src/','')
        if line.startswith('# See more config options'):
            lines[i] = ''
        if line.startswith('remappings =') and remappings is not None and remappings != []:
            lines[i] = ''
            flag=True
        if flag and remappings is not None:
            lines[i] = ''
        if lines[i].endswith(']') and remappings is not None and remappings != []:
            lines[i] = ''
            flag=False
    lines= [line for line in lines if line.strip() != '']
    if remappings is not None and remappings != []:
        lines.append('remappings = [\n')
        lines.extend([f'    "{remapping}",\n' for remapping in remappings])
        lines.append(']\n')
        lines.append('solc_version = "{}"\n'.format(version))
    if viair:
        lines.append('optimizer = true\n')
        lines.append('optimizer_runs = 200\n')
        lines.append('via_ir  = true\n')
    if evmVersion is not None and evmVersion != '':
        lines.append('evm_version = "{}"\n'.format(evmVersion))
    with open(os.path.join(path, "foundry.toml"), "w") as f:
        f.writelines(lines)
    forge_build_cmd = f"forge build"
    res=subprocess.run(forge_build_cmd, shell=True, stderr=subprocess.PIPE, stdout=subprocess.PIPE, cwd=path)
    if res.returncode != 0:
        print("forge build failed")
        print(res.stderr.decode())
        return False
    print("forge build success")
    forge_faltten_cmd = f"forge flatten {flatten_path} | sed '/SPDX-License-Identifier/d' | sed '/pragma solidity/d' | (echo '// SPDX-License-Identifier: MIT'; echo 'pragma solidity ^{version};'; cat) > {path}/flattened.sol"
    res=subprocess.run(forge_faltten_cmd, shell=True, stderr=subprocess.PIPE, stdout=subprocess.PIPE, cwd=path)
    if res.returncode != 0:
        print("forge flatten failed")
        print(res.stderr.decode())
        return False
    print("forge flatten success")
    return True
def save_to_mongodb(id, file_path,viair):
    client = MongoClient("mongodb://shuaicpu5.cse.ust.hk:27017/")
    collection = client['contracts']['top_contracts']
    with open(os.path.join(file_path,'flattened.sol'), 'r') as f:
        code= f.read()
    collection.update_one({'_id': id}, {'$set': {'code': code, 'viaIR': viair}})
    client.close()
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

def process_multifile(args):
    if os.path.exists(os.path.join(args['output_folder'],args['chain_id'], args['address'])):
        return
    settings=args['settings']
    solc_version=args['solc_version']
    if settings is not None:
        if 'remappings' in settings:
            remappings=settings['remappings']
        else:
            remappings=None
        if 'viaIR' in settings:
            viair=settings['viaIR']
        else:
            viair=False
        if 'evmVersion' in settings:
            evmVersion=settings['evmVersion']
        else:
            evmVersion=None
    else:
        remappings=None
        viair=False
        evmVersion=None
    try:
        path,contract_path,flatten_path=export_multifile(args,args['output_folder'])
        init_res=forge_init(path,contract_path, flatten_path, solc_version, viair, remappings,evmVersion)
        if not init_res:
            print("forge init failed")
            shutil.rmtree(path)
            return
    except Exception as e:
        print(f"error in process {args['chain_id']} : {args['address']}")
        print("error line:", e.__traceback__.tb_lineno)
        print("error type:", e)
        if os.path.exists(os.path.join(args['output_folder'],args['chain_id'], args['address'])):
            shutil.rmtree(os.path.join(args['output_folder'],args['chain_id'], args['address']))
        return
    save_to_mongodb(args['_id'], path,viair)
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
        version=doc['version']
        version=version.split('+')[0]
        version=version.replace('v','')
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
                source_code=source_load
                settings=None
            # except Exception as e:
            #     print("error in save_to_mongodb")
            #     print("error line:", e.__traceback__.tb_lineno)
            #     print("error type:", e)
            #     cou+=1
            #     continue
            all_contracts.append({
                '_id': id,
                'address': address,
                'chain_id': chain_id,
                'source': source_code,
                'settings': settings,
                'contract_name': contract_name,
                'output_folder': '/home/liuhan/top_contracts',
                'solc_version': version,
            })
    # with open('all_contracts.json', 'w') as f:
    #     json.dump(all_contracts, f, indent=4)
    for arg in tqdm(all_contracts):
        process_multifile(arg)
    # print(cou)
    # path,contract_path,flatten_path=export_multifile(all_contracts[0],'/home/liuhan/utils_download/solc_source_code')
    # forge_init(path,contract_path, flatten_path, viair=True)
