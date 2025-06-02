from slither.core.declarations import Contract
from typing import List
def find_main_contracts(contracts: List[Contract], main_contract_name: str = "MainContract", num_limit: int = 1) -> List[Contract]:
    """
    Find the main contracts from a list of contracts.
    
    Args:
        contracts (List[Contract]): A list of Contract objects.
        main_contract_name (str): The name of the main contract to look for. Default is "MainContract".
        If set to "MainContract", it will find all contracts that are not inherited by any other contract.
        If set to a specific contract name, it will find that specific contract.
    Returns:
        List[Contract]: A list of main Contract objects.
    """
    main_contracts = []
    all_inheritance = {}
    if main_contract_name!= "MainContract":
        for contract in contracts:
            if contract.name == main_contract_name:
                main_contracts.append(contract)
    else:
        for contract in contracts:
            for base in contract.inheritance:
                if base.name not in all_inheritance:
                    all_inheritance[base.name] = 0
                all_inheritance[base.name] += 1
        for contract in contracts:
            if contract.name not in all_inheritance and contract.is_library == False and contract.contract_kind=='contract' and contract.is_fully_implemented==True and contract.is_abstract==False:
                main_contracts.append(contract)
        main_contracts = sorted(
            main_contracts,
            key=lambda x: x.contract.source_mapping.start,
            reverse=True
        )
        if num_limit > 0:
            main_contracts = main_contracts[:num_limit]
    return main_contracts