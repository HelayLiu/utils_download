
from pathlib import Path

from crytic_compile import CryticCompile
from .solidity_version import get_solc_path_from_version, get_available_solc_versions, get_solc_path
from slither.slither import Slither
from .find_main_contracts import find_main_contracts
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

    def get_slither(self):
        if self._slither is None:
            cry_cmp_res = self.get_compiler_info()
            self._slither = Slither(cry_cmp_res)
        if self._contract is None:
            self._contract = find_main_contracts(self._slither.contracts,self.contract_name)
        return self._slither
if __name__ == "__main__":
    # Example usage
    compiler_helper = CompilerHelper("/home/liuhan/utils_download/test_contract2.sol", version="0.5.0", optimization=False, via_ir=False, contract_name="OddEven")
    slither = compiler_helper.get_slither()
    print(slither)
