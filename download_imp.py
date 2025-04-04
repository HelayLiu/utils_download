import requests
import json
import time
from random import randint
from pymongo import MongoClient
import multiprocessing
api_keys=["B69GNP1IXCXJUGTWVCZPW4PS6KFDQ9MNJ1",
        "TRUHXX8K4D5E4665M22FUYZ6F4ZP4SC6UQ",
        "373ZPPAM1QZYS55Q5AW24BKW124BGPMPIA",
        "75FE5RHNXQJPRY6A4EGXTWJKE4M7783W6F",
        "Q8K1J5WIXHVQWV1XHVFF1INTPHWFZP5AZV",
        "KWPEX5CZ437P2JRB2U7WZ37VQFAVZFXXP6",
        "VVD8W64K6A78ZI6IFPDA9M8NSI7VFTRK1T",
        "ETZD3M1CXH644842GQCMAKXVVEE9U4RGFA",
        "FZHNXTAQND5NM1FK4WSXSIHTW7ZIAKQ8CM",
        "DUBWVVR8H7PY1XGNJTQ9M1PBEJGBUB81N4",
        "BTXJUGF5C8FVVP3KG1F1816G1FPMTX18R8",
        "UPA8FNQ5EYVUXB3HG3NPUJN55U3SP7PGMC"]
def get_key():
    try:
        randomNum = randint(0, len(api_keys) - 1)
        return api_keys[randomNum]
    except Exception as e:
        print("--------------------------------------")
        print("error in get_key")
        print("error line:", e.__traceback__.tb_lineno)
        print("error type:", e)
        print("--------------------------------------")
def send_request(chain_id,address):
    try:
        api_key=get_key()
        url=f"https://api.etherscan.io/v2/api?chainid={chain_id}&module=contract&action=getsourcecode&&address={address}&apikey={api_key}"
        response=requests.get(url)
        if response.status_code!=200 or response.content==b'{"status":"0","message":"NOTOK"}':
            raise Exception
        else:
            return json.loads(response.content)['result'][0]
    except Exception as e:
        print("--------------------------------------")
        print("error in send_request")
        print("error line:", e.__traceback__.tb_lineno)
        print("error type:", e)
        print("--------------------------------------")
        return None

def save_to_mongodb(related_id,related_address,chain,chain_id,trans_num,implementation,result):
    try:
        source=result['SourceCode']
        version=result['CompilerVersion']
        contract_name=result['ContractName']
        optimization=result['OptimizationUsed']
        optimization_runs=result['Runs']
        client = MongoClient("mongodb://shuaicpu5.cse.ust.hk:27017/")
        collection_source=client['contracts']['top_contracts']
        collection_source.insert_one({'address':implementation,
                                      'chain':chain,
                                      'chain_id':chain_id,
                                      'trans_num':trans_num,
                                      'related_address':related_address,
                                      'related_id':related_id,
                                      'is_implementation':True,
                                      'source': source,
                                      'version': version,
                                      'contract_name': contract_name,
                                      'optimization': optimization,
                                      'optimization_runs': optimization_runs})
        # collection_source.update_one({'_id': id}, {'$set': {'source': source,
        #                                         'version': version,
        #                                         'contract_name': contract_name,
        #                                         'optimization': optimization,
        #                                         'optimization_runs': optimization_runs,
        #                                         'implementation': implementation}})
        print(f"Updated document with impletment {implementation} in MongoDB.")
        client.close()
    except Exception as e:
        print("--------------------------------------")
        print("error in save_to_mongodb")
        print("error line:", e.__traceback__.tb_lineno)
        print("error type:", e)
        print("--------------------------------------")

def main(args):
    implementation=args['implementation']
    chain_id=args['chain_id']
    chain=args['chain']
    related_address=args['address']
    related_id=args['id']
    trans_num=args['trans_num']
    cou=0
    while True:
        result=send_request(chain_id,implementation)
        if result is None:
            print(f"Failed to get source code for address {implementation}. Retrying...")
            time.sleep(5)
        else:
            print(f"Successfully retrieved source code for address {implementation}.")
            break
        if cou>10:
            print(f"Failed to get source code for address {implementation} after multiple attempts.")
            break
        cou+=1
    if result is not None:
        save_to_mongodb(related_id,related_address,chain,chain_id,trans_num,implementation,result)
    else:
        print(f"Failed to get source code for address {implementation}.")
if __name__=="__main__":
    # MongoDB连接
    client = MongoClient("mongodb://shuaicpu5.cse.ust.hk:27017/")
    collection_source=client['contracts']['top_contracts']
    # 查询MongoDB集合中的所有文档
    documents = collection_source.find({'source':{'$ne':''}},{'_id':1,'address':1,'chain_id':1,'chain':1,'implementation':1,'trans_num':1})
    # 遍历每个文档
    contract_address_list=[]
    for doc in documents:
        id=doc['_id']
        address=doc['address']
        chain_id=doc['chain_id']
        if 'implementation' not in doc:
            continue
        implementation=doc['implementation']
        find_id=collection_source.count_documents({'related_id':id})
        if find_id >0:
            continue
        if implementation!='':
        # if 'contract_name' in doc:
        #     continue
        # if not source.startswith('{'):
        #     continue
            contract_address_list.append({'id':id,'address':address,'implementation':implementation,'chain_id':chain_id, 'chain':doc['chain'],'trans_num':doc['trans_num']})
    # for contract in contract_address_list:
    #     main(contract)
    print(f"Total contracts to process: {len(contract_address_list)}")
    time.sleep(5)
    pool=multiprocessing.Pool(processes=20)
    pool.map(main, contract_address_list)