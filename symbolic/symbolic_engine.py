import time

from slither.core.expressions import Literal
from slither.core.solidity_types import ElementaryType
from slither.slithir.variables import Constant
from z3 import Solver, sat, unsat, Z3Exception, unknown, ExprRef, BitVecVal, ModelRef, BitVecRef, BitVecNumRef, Or
from .slither_op_parser import SlitherOpParser
from .sequence import TxSeqGenerationResult, TxSequence, Transaction
from typing import Set, List, Dict, TypeAlias, FrozenSet, Tuple, Optional
from icfg import ICFGNode, SlicedGraph
from .symbolic_state import SymbolicState
from slither.core.variables import StateVariable
from slither.core.declarations import Function, Contract
from .memory_model import MemoryModel, MULocation
from .variable_monitor import VariableMonitor
from .default_ctx import DEFAULT_ATTACKER_CTX, DEFAULT_DEPLOYER_CTX, DEFAULT_TX_CTX

# ANSI 转义码
RED = "\033[91m"
GREEN = "\033[92m"
YELLOW = "\033[93m"
BLUE = "\033[94m"
MAGENTA = "\033[95m"
CYAN = "\033[96m"
RESET = "\033[0m"

# 符号执行输出结果
# [FrozenSet[ICFGNode]:program point
# Dict[TxSequence, bool]:TxSequence is secure
# 如果是
SymbolicExecResult: TypeAlias = Dict[FrozenSet[ICFGNode], Dict[TxSequence, Tuple[bool, Optional[ModelRef], List[SymbolicState]]]]


class SymbolicEngine:
    def __init__(self):
        self.solver: Solver = Solver()
        self.variable_monitor: VariableMonitor = VariableMonitor()
        self.slither_op_parser: SlitherOpParser = SlitherOpParser(self.solver)

    def execute(self, sliced_graph: SlicedGraph, all_tx_sequences: TxSeqGenerationResult) -> SymbolicExecResult:
        # 部署合约构造函数执行，存储初始化
        # 1.持久化存储，持久存在于交易之间
        start_time = time.time()
        init_storage: MemoryModel = MemoryModel(MULocation.STORAGE)
        # 2.设置合约创建时候的默认值对应的符号值
        self.init_contract_creation_sym_storage(sliced_graph, init_storage)
        # 3.逐一执行构造函数序列（按照父类-子类的次序）
        self.exec_constructor_sequence(sliced_graph, init_storage)
        # 返回执行结果，提供给Logger使用
        SymbolicExecRes: SymbolicExecResult = dict()
        check_count = 1
        for base_path_tx_seqs_map in all_tx_sequences.values():
            for base_path in base_path_tx_seqs_map.keys():
                tx_seq_set: Set[TxSequence] = base_path_tx_seqs_map[base_path][0]
                perm_nodes: List[ICFGNode] = base_path_tx_seqs_map[base_path][1]
                for one_seq in tx_seq_set:
                    # 每次执行完毕一次交易序列，重置约束求解器，清空约束
                    self.solver.reset()
                    # 拷贝构造函数执行后的storage
                    tx_storage: MemoryModel = init_storage.copy()
                    # 特判，消除误报：执行完构造函数中的address变量，一定不能指向attacker地址
                    self.assert_addr_not_attacker_in_constructor(tx_storage)
                    # 执行一组交易序列,找到一组可行解
                    is_feasible, model, state_list = self.exec_one_tx_sequence(tx_storage, one_seq)
                    # 保存执行结果供上层调用者处理
                    SymbolicExecRes.setdefault(frozenset(perm_nodes), dict()).setdefault(one_seq, (is_feasible, model, state_list))
                    # 输出执行结果
                    contract_name = sliced_graph.icfg.main_contract.name
                    self.log_symbolic_execution_res(is_feasible, one_seq, perm_nodes, tx_storage, model, contract_name, check_count)
                    check_count += 1
        end_time = time.time()
        time_cost = end_time - start_time
        print(f"Execution time: {time_cost}")
        return SymbolicExecRes

    def exec_constructor_sequence(self, sliced_graph: SlicedGraph, init_storage: MemoryModel):
        # 在每一个交易序列执行之前，先按照合约继承的顺序，执行一遍constructor函数
        main_contract = sliced_graph.icfg.main_contract
        # 所有继承的合约（包含主合约本身）
        contract_inherit_order: List[Contract] = [c for c in main_contract.inheritance_reverse] + [main_contract]
        constructor_exec_list: List[Function] = []
        # 按照合约继承顺序，依次查找所有构造函数
        for inherit_contract in contract_inherit_order:
            # 从所有继承的构造函数（无序，包含主合约本身）中查找当前inherit_contract的构造函数
            for constructor in main_contract.constructors:
                if constructor.contract_declarer == inherit_contract:
                    constructor_exec_list.append(constructor)
        # 逐一执行每一个构造函数
        for constr in constructor_exec_list:
            constr_slices = sliced_graph.func_slices_map[constr]
            constr_tx = Transaction(constr_slices[0])
            constr_init_state: SymbolicState = SymbolicState(solver=self.solver,
                                                             monitor=self.variable_monitor,
                                                             tx=constr_tx,
                                                             tx_storage=init_storage,
                                                             tx_ctx=DEFAULT_DEPLOYER_CTX)
            self.slither_op_parser.parse_tx_ops(constr_init_state)

    def exec_one_tx_sequence(self, tx_storage: MemoryModel, tx_sequence: TxSequence) -> Tuple[bool, Optional[ModelRef], List[SymbolicState]]:
        # 设置默认的交易执行上下文
        state_list: List[SymbolicState] = []
        for txindex in range(len(tx_sequence.txs)):
            tx = tx_sequence.txs[txindex]
            # 默认最后一个函数一定是由攻击者调用，而其他函数可以通过部署者/攻击者调用
            CTX = DEFAULT_ATTACKER_CTX if txindex == len(tx_sequence.txs) - 1 else DEFAULT_TX_CTX
            # 设置下一次执行的的初始状态 符号执行每一个交易，保存交易的中间状态
            tx_init_state: SymbolicState = SymbolicState(solver=self.solver,
                                                         monitor=self.variable_monitor,
                                                         tx=tx,
                                                         tx_storage=tx_storage,
                                                         tx_ctx=CTX)
            self.slither_op_parser.parse_tx_ops(tx_init_state)
            # 检查结果是否是“不可满足的”，说明合约是安全的
            state_list.append(tx_init_state)
            if self.solver.check() == unsat:
                return False, None, state_list
        try:
            return True, self.solver.model(), state_list
        except Z3Exception:
            return False, None, state_list

    @staticmethod
    def init_contract_creation_sym_storage(sliced_graph: SlicedGraph, init_storage: MemoryModel):
        main_contract = sliced_graph.icfg.main_contract
        inited_state_vars: List[StateVariable] = list(filter(lambda sv: sv.initialized, main_contract.state_variables))
        for isv in inited_state_vars:
            # 获取初始值
            isv_exp = isv.expression
            if isv_exp is not None and isinstance(isv_exp, Literal):
                isv_type = isv_exp.type
                isv_value = isv_exp.value
                if isinstance(isv_type, ElementaryType):
                    sym_isv_constant = init_storage.create_symbolic_constant(Constant(val=isv_value, constant_type=isv_type))
                    init_storage[isv] = sym_isv_constant

    def log_symbolic_execution_res(self, is_feasible: bool, txs: TxSequence, program_points: List[ICFGNode], storage: MemoryModel,
                                   model: ModelRef, contract_name: str, check_count: int) -> None:
        print(
            f"{YELLOW}================================ GALA SYMBOLIC EXECUTION RESULT {check_count} FOR {contract_name} ================================{RESET}")
        # 输出攻击者和部署者的地址
        deployer_addr = DEFAULT_DEPLOYER_CTX["msg.sender"]
        attacker_addr = DEFAULT_ATTACKER_CTX["msg.sender"]
        print(f"Default Deployer: {deployer_addr} ({int(deployer_addr, 16)})")
        print(f"Default Attacker: {attacker_addr} ({int(attacker_addr, 16)})")
        # 输出所有的权限集
        print(f"{CYAN}====> Program Points <===={RESET}")
        [print(str(pn)) for pn in program_points]
        # 输出权限集对应的交易序列
        print(f"{CYAN}====> Generated Tx Sequence <===={RESET}")
        print(f"constructor -> {str(txs)}")
        # 输出符号执行结果
        print(f"{CYAN}====> Symbolic Execution Result <===={RESET}")
        if not is_feasible:
            print(f"{GREEN}No Solution Found. The Txs Execution Path Is Infeasible{RESET}")
        else:
            print(f"{RED}Current Txs Execution Path Is Feasible{RESET}")
            print(f"{CYAN}====> One Solution <===={RESET}")
            for var in model:
                var_value = model[var]
                if isinstance(var_value, BitVecNumRef) and var.name().startswith("addr_"):  # 地址类型
                    var_value_hex = hex(var_value.as_long())
                    print(f"{var.name().removeprefix('addr_')} = {var_value_hex}")
                else:
                    print(f"{var.name()} = {var_value}")
        # Assert
        print(f"{CYAN}====> Solver Assertions <===={RESET}")
        print(self.solver.assertions())
        # 存储的信息
        print(f"{CYAN}====> Final Storage Value <===={RESET}")
        for state_var in storage.MU.keys():
            sym_state_val = storage[state_var]
            if isinstance(sym_state_val, BitVecNumRef) and state_var.type == "address":  # 地址类型
                var_value_hex = hex(sym_state_val.as_long())
                print(f"{state_var.name} = {var_value_hex}")
            else:
                print(f"{state_var.name} = {sym_state_val}")

    def assert_addr_not_attacker_in_constructor(self, tx_storage: MemoryModel):
        for var, sym_var in tx_storage.MU.items():
            var_type = var.type
            if isinstance(var_type, ElementaryType) and var_type.name == "address":
                attacker_sym_addr = BitVecVal(int(DEFAULT_ATTACKER_CTX['msg.sender'], 16), 256)
                self.solver.add(sym_var != attacker_sym_addr)

    # def init_constructor(init_storage: MemoryModel, sliced_graph: SlicedGraph) -> None:
    #     if sliced_graph.icfg.main_contract.constructor is None:
    #         return
    #     constructor: Function = sliced_graph.icfg.main_contract.constructor
    #     constr_slice = sliced_graph.func_slices_map[constructor][0]
    #     for sv_write_node in constr_slice.sv_write_nodes:
    #         # 如果是address类型的变量，我们要判断msg.sender/tx.origin是否可能流向状态变量
    #         if hasattr(sv_write_node, "lvalue") and str(sv_write_node.lvalue.type) == "address":
    #             perm: Permission = sliced_graph.icfg.graph.nodes[sv_write_node]["permission"]
    #             solidity_vars_flow = perm.state_var_write_taint_result[constr_slice].solidity_vars_flow_to_sink
    #             for svf in solidity_vars_flow:
    #                 if svf.name in DEFAULT_CONSTRUCTOR_CTX.keys():
    #                     # 如果流向了状态变量，将storage中该状态变量的初始值置为1，用以模拟构造函数的执行
    #                     default_addr = DEFAULT_CONSTRUCTOR_CTX[svf.name]
    #                     init_storage[sv_write_node.lvalue] = BitVecVal(int(default_addr, 16), 160)
if __name__ == "__main__":
    pass
