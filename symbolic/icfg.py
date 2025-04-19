from enum import Enum, auto

from networkx import MultiDiGraph
from slither.core.declarations import Contract, Function, FunctionContract
from slither.core.variables import StateVariable
from typing import TypeAlias, Union, Tuple, Optional, Dict, List, Set
from slither.core.cfg.node import Node
from slither.slithir.operations.operation import Operation

SSAIRNode: TypeAlias = Operation
SlitherNode: TypeAlias = Node
ICFGNode: TypeAlias = Union[SlitherNode, SSAIRNode]
ICFGEdge: TypeAlias = Tuple[ICFGNode, ICFGNode]


class EdgeType(Enum):
    IF_TRUE = auto()
    IF_FALSE = auto()
    GENERAL = auto()
    FUNCTION_CALL = auto()
    MODIFIER_CALL = auto()
    # CALL_RETURN = auto()
    # SINK_EDGE_FOR_MODIFIER = auto()
    # SINK_EDGE_FOR_FUNCTION = auto()


class ICFG:
    def __init__(self, main_contract: Contract):
        # ICFG本体
        self.graph: MultiDiGraph = MultiDiGraph()
        # 合约本体
        self.main_contract: Contract = main_contract
        # 一些索引节点
        # 记录constructor函数对哪些StateVariable进行了初始化操作/哪些SV直接被赋初始值
        self.sv_with_init_value: Set[StateVariable] = set()
        # 记录每一个函数的entry point
        self.func_entry_point_map: Dict[Function, SlitherNode] = {}
        # 记录每一个函数的exit point
        self.func_exit_point_map: Dict[Function, SlitherNode] = {}
        # 记录对每一个state variable的读和写的操作，按照函数进行划分
        # self.sv_read_fn_map: Dict[StateVariable, Dict[Function, Set[ICFGNode]]] = {}
        self.sv_write_fn_map: Dict[StateVariable, Dict[Function, Set[ICFGNode]]] = {}

class SlicedPath:
    def __init__(self, slice_func: Function, path: List[ICFGNode]):
        self.slice_func: Function = slice_func
        self.nodes: List[ICFGNode] = path
        self.ops: List[SSAIRNode] = list(filter(lambda n: isinstance(n, SSAIRNode), path))
        self.req_nodes: List[ICFGNode] = []
        self.sv_write_nodes: List[ICFGNode] = []
        self.call_nodes: List[ICFGNode] = []  # 函数调用节点
        self.condition_node_edge_type_map: Dict[ICFGNode, EdgeType] = {}

    def __str__(self):
        return f"{str(self.slice_func)}: {' -> '.join(map(str, self.nodes))}"


class SlicedGraph:
    def __init__(self, icfg: ICFG):
        self.icfg: ICFG = icfg
        # 所有的执行路径切片,按照函数进行划分
        self.func_slices_map: Dict[Function, List[SlicedPath]] = {}
        # Very Important
        # state_var_write_slice_map用于记录可以trigger state var被写的所有执行路径，以及到达write node所有的requirement节点
        self.state_var_write_slice_map: Dict[StateVariable, Dict[ICFGNode, Dict[SlicedPath, List[ICFGNode]]]] = {}
        # perm_node_slice_map用于记录可以到达一个permission node的所有执行路径,以及到达perm_node的所有requirement节点
        self.program_point_slice_map: Dict[ICFGNode, Dict[SlicedPath, List[ICFGNode]]] = {}
