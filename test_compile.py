import os
from pymongo import MongoClient
from tqdm import tqdm
from solidity_version import *
from pathlib import Path
from crytic_compile import CryticCompile
class CompilerHelper:
    """
    Helper class to extract compiler information from a Solidity file.
    """

    def __init__(self, sol_file: str | Path, version: str = None, optimization: bool = False, via_ir: bool = False, contract_name: str = None):
        self.sol_file = Path(sol_file)
        self._slither  = None
        self.version = version
        self.optimization = optimization
        self.via_ir = via_ir
        self._contract = None
        self.solc_path = None
        self.contract_name = contract_name

    def get_compiler_info(self) -> dict:
        """Return the compiler version and optimization settings."""
        if self.version==None:
            self.version, self.solc_path = get_solc_path(self.sol_file)
        if self.solc_path == None:
            get_available_solc_versions()
            self.solc_path = get_solc_path_from_version(self.version)
        if self.via_ir:
            solc_args="--optimize --via-ir"
        elif self.optimization:
            solc_args="--optimize"
        else:
            solc_args=""
        cry_cmp_res = CryticCompile(
            target=str(self.sol_file),
            solc=self.solc_path,
            solc_args=solc_args
        )
        return cry_cmp_res


def compile(args):
    code=args['code']
    version=args['version']
    via_ir=args['via-ir']
    address=args['address']
    print(f"Compiling contract at address {address} with version {version} and via_ir={via_ir}")
    optimization=True if args['optimization']=='1' else False
    import tempfile
    with tempfile.NamedTemporaryFile(suffix='.sol',delete=True) as temp_file:
        temp_file.write(code.encode('utf-8'))
        temp_file_path = temp_file.name
        cp=CompilerHelper(temp_file_path,version=version,optimization=optimization,via_ir=via_ir)
        try:
            res=cp.get_compiler_info()
            if res==None:
                raise ValueError("res is None")
        except Exception as e:
            print(f"Error compiling contract at address {address}: {e}")
            res = None
    client=MongoClient("mongodb://shuaicpu5.cse.ust.hk:27017/")
    collection=client['contracts']['top_contracts']
    success=False if res==None else True
    collection.update_one(
        {'_id':args['_id']},
        {'$set':{
            'success':success
        }}
    )
if __name__ == "__main__":

    client=MongoClient("mongodb://shuaicpu5.cse.ust.hk:27017/")
    collection_source=client['contracts']['top_contracts']
    docs=collection_source.find({'code':{'$exists':True}},{'code':1,'viaIR':1,'version':1,'address':1,'optimization':1,'_id':1})
    res=[]
    for doc in tqdm(docs):
        temp={}
        temp['_id']=doc['_id']
        temp['code']=doc['code']
        temp['via-ir']=doc['viaIR'] if 'viaIR' in doc else False
        version=doc['version']
        version=version.split('+')[0]
        version=version.split('v')[-1]
        temp['version']=version
        temp['optimization']=doc['optimization'] if 'optimization' in doc else '0'
        temp['address']=doc['address']
        res.append(temp)
    from multiprocessing import Pool
    pool=Pool(processes=40)
    pool.map(compile,res)
    # for i in res:
    #     compile(i)
    #     break