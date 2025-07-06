##### !!!!! MAY STILL HAVE BUGS !!!!! #####
## TODO: test more cases

from __future__ import annotations
from typing import List, Tuple, Dict, TypeAlias
from copy import deepcopy
import json
from slither.core.declarations import Function
from slither.slithir.operations.high_level_call import HighLevelCall
from slither.slithir.operations.condition import Condition
from slither.slithir.operations.assignment import Assignment
from slither.slithir.operations.binary import Binary
from slither.slithir.operations.member import Member
from slither.slithir.operations.index import Index
from slither.slithir.variables.constant import Constant
from slither.slithir.variables.variable import Variable
from slither.slithir.variables.local_variable import LocalVariable
from slither.core.declarations import FunctionContract, Modifier
from slither.slithir.operations.internal_call import InternalCall
from slither.slithir.operations.library_call import LibraryCall
from slither.slithir.variables.state_variable import StateVariable
from slither.core.cfg.node import NodeType
from slither.core.cfg.node import Node
from utils import *
SlitherNode: TypeAlias = Node
SlitherNodeType: TypeAlias = NodeType
# --------------------------------------------------------------------- #
# public API                                                            #
# --------------------------------------------------------------------- #
def enumerate_transitions(fn: FunctionContract, *, max_depth: int = 64) -> List[List[str]]:
    # ------------------------------------------------------------------ #
    # helpers                                                            #
    # ------------------------------------------------------------------ #
    def _expr(obj, env: Dict[Variable, str]) -> str | None:
        """Return string representation of IR operand or None if unresolved."""
        if isinstance(obj, Constant):
            return str(obj.value)

        if isinstance(obj, Variable):
            # environment substitution first
            if obj in env:
                return env[obj]
            # skip unknown temporaries
            if isinstance(obj, LocalVariable) and getattr(obj, "temporary", False):
                return None
            return obj.name if hasattr(obj, "name") else str(obj)

        if isinstance(obj, (Member, Index)):
            # Member/Index are first assigned to a temporary, stringify them
            return str(obj)

        if isinstance(obj, Binary):
            l = _expr(obj.variable_left, env)
            r = _expr(obj.variable_right, env)
            if l is None or r is None:
                return None
            return f"({l} {obj.type} {r})"
        return str(obj)

    def _scan_node(node, env0: Dict[Variable, str]) -> tuple[str | None, Dict[Variable, str]]:
        """
        Build the environment from *all* assignments in the node first,
        then resolve the guard with that complete environment.
        """
        env: Dict[Variable, str] = env0.copy()

        # 1) collect assignments (var = const|expr)
        for ir in node.irs:
            if hasattr(ir, "lvalue"):
                if hasattr(ir, "rvalue"):
                    rhs = _expr(ir.rvalue, env)
                elif hasattr(ir, "expression"):
                    rhs = _expr(ir.expression, env)
                else:
                    raise ValueError(f"Unknown IR type: {ir}")
                if rhs is not None:
                    env[ir.lvalue] = rhs
        all_gs = []
        # 2) locate guard and resolve it with the populated env
        for ir in node.irs:
            if node.contains_require_or_assert() and hasattr(ir, "arguments") and ir.arguments and ('require' in str(ir) or 'assert' in str(ir)):
                g = _expr(ir.arguments[0], env)
                if g is not None:
                    all_gs.append(g)
            if isinstance(ir, Condition):
                inner = getattr(ir, "_expression", None)
                if inner is not None:
                    g = _expr(inner, env)
                    if g is not None:
                        all_gs.append(g)
        res_guard = '&&'.join(all_gs)
        if res_guard == '':
            res_guard = None
        return res_guard, env

    # ------------------------------------------------------------------ #
    # non‑recursive DFS                                                  #
    # ------------------------------------------------------------------ #
    StackEntry = Tuple[SlitherNode, List[SlitherNode], List[str], Dict[Variable, str], int, List[SlitherNode]]
    stack: List[StackEntry] = [(fn.entry_point,[], [], {}, 0, [])]
    visited_edges: set[Tuple[int, int]] = set()
    visited_calls: set[Tuple[int, int]] = set()
    paths: List[Tuple[List[str], List[SlitherNode]]] = []

    while stack:
        node, node_so_far, path_so_far, env_in, depth, cont = stack.pop()
        if depth > max_depth:
            continue
        if node == None:
            continue
        succs = list(node.sons)
        if node.type == SlitherNodeType.PLACEHOLDER:
            # placeholder node
            if cont:
                next_node = cont[0]               # resume caller
                stack.append(
                    (next_node,
                    node_so_far,
                    path_so_far,
                    env_out,
                    depth,                       # same depth (no extra nesting)
                    cont[1:] + succs,                    # remaining continuation
                    )
                )
            continue
             
        guard_expr, env_out = _scan_node(node, env_in)
        if guard_expr and node.contains_require_or_assert():
            paths.append((path_so_far + [f"{guard_expr} == False"], node_so_far + [node]))

        if not succs:
            if cont:                              # leaf of current frame
                next_node = cont[0]               # resume caller
                stack.append(
                    (next_node,
                     node_so_far + [node],
                     path_so_far,
                     env_out,
                     depth,                       # same depth (no extra nesting)
                     cont[1:],                    # remaining continuation
                    )
                )                              # exit
            else:                               # leaf of the whole function
                paths.append((path_so_far + [guard_expr] if guard_expr else path_so_far, node_so_far + [node]))
        flag = False
        for ir in node.irs:
            if isinstance(ir, (HighLevelCall,InternalCall,LibraryCall)) and isinstance(ir.function, FunctionContract):
                callee: FunctionContract = ir.function
                # same contract & not view/pure/external
                if callee.contract == fn.contract:
                    tag = (id(node), id(callee))
                    if tag not in visited_calls:
                        visited_calls.add(tag)
                        stack.append(
                            (callee.entry_point, 
                             node_so_far + [node], 
                             path_so_far + ([] if guard_expr is None else [guard_expr]),
                             env_out, 
                             depth + 1,
                             succs + cont)
                        )
                        flag = True
        if flag:
            continue
        for nxt in succs:
            edge = (id(node), id(nxt))
            if edge in visited_edges:
                continue
            visited_edges.add(edge)

            lbl = guard_expr
            if hasattr(node, "son_true") and hasattr(node, "son_false"):
                if nxt == node.son_false:
                    lbl = f"{guard_expr} == False"
            new_path = path_so_far + ([lbl] if lbl else [])
            new_node = node_so_far + [node]
            stack.append((nxt, new_node, new_path, env_out, depth + 1, cont))
        # modifier_chain =  [sta_modifier_nodes[0] for sta_modifier_nodes in all_modifier_stas if sta_modifier_nodes[0]!=None ]
        # if modifier_chain:
        #     # add modifier return
        #     stack.append(
        #         (modifier_chain[0], node_so_far + [node], path_so_far + ([] if guard_expr is None else [guard_expr]),
        #         env_out, depth + 1,  modifier_chain[1:] + succs + cont  if len(modifier_chain) > 1 else succs + cont)
        #     )
    return paths

def get_func_sign_rw_v(path,file) -> List[str]:
    config_path= os.path.join(path, file.replace('.sol', '.json'))
    with open(config_path, 'r') as f:
        config = json.load(f)
    compiler_helper = CompilerHelper(os.path.join(path,file), version=config['version'], optimization=config['opt'], via_ir=config['via_ir'], contract_name=config['contract_name'])
    slither = compiler_helper.get_slither()
    contract = compiler_helper._contract[0]
    res={}
    for fn in contract.functions:
        if fn.is_constructor or fn.is_fallback or fn.is_receive or fn.is_shadowed:
            continue
        if fn.visibility == "public" or fn.visibility == "external":
            function_name = fn.signature[0]
            function_args = ''
            for i in range(len(fn.parameters)):
                if function_args != '':
                    function_args += ', '
                param = fn.parameters[i]
                function_args += f'{fn.signature[1][i]} {param.name}'
            function_name += f'({function_args})'
            function_returns = ', '.join(fn.signature[2])
            function_name += f' returns ({function_returns})' if function_returns else ''
            read_variables = []
            write_variables = []
            calls = []
            not_tps = ['suicide(address)','selfdestruct(address)','abi.encodeCall()','raw_call()','send()']

            for solidty_call in fn.solidity_calls:
    
                if str(solidty_call) in not_tps:
                    calls.append(str(solidty_call))
            for node in fn.all_nodes():
                for var in node.variables_read:
                    if isinstance(var, StateVariable):
                        read_variables.append(str(var))
                for var in node.variables_written:
                    if isinstance(var, StateVariable):
                        write_variables.append(str(var))
            read_variables = list(set(read_variables))
            write_variables = list(set(write_variables))
            calls = list(set(calls))
            res[function_name] = {
                "read_state_variables": read_variables,
                "write_write_variables": write_variables,
            }
    return res
def get_conditions(path,file) -> List[str]:
    config_path= os.path.join(path, file.replace('.sol', '.json'))
    with open(config_path, 'r') as f:
        config = json.load(f)
    compiler_helper = CompilerHelper(os.path.join(path,file), version=config['version'], optimization=config['opt'], via_ir=config['via_ir'], contract_name=config['contract_name'])
    slither = compiler_helper.get_slither()
    contract = compiler_helper._contract[0]
    res={}
    for fn in contract.functions:
        if fn.is_constructor or fn.is_fallback or fn.is_receive:
            continue
        if fn.visibility == "public" or fn.visibility == "external":
            function_name = fn.signature[0]
            function_args = ''
            for i in range(len(fn.parameters)):
                if function_args != '':
                    function_args += ', '
                param = fn.parameters[i]
                function_args += f'{fn.signature[1][i]} {param.name}'
            function_name += f'({function_args})'
            function_returns = ', '.join(fn.signature[2])
            function_name += f' returns ({function_returns})' if function_returns else ''
            max_condition = []
            max_node=[]
            all_checks=[]
            for i, p in enumerate(enumerate_transitions(fn)):
                if len(p[0])>len(max_condition):
                    max_condition = deepcopy(p[0])
                    max_node = p[1]
                    max_node = [n for n in max_node if 'require' in str(n).lower() or 'assert' in str(n).lower() or 'if' in str(n).lower()]
            
            for i in range(len(max_condition)):
                condition = max_condition[i]
                condition = condition.replace("_msgSender()", "msg.sender")
                if condition != '' and "address(0)" not in condition:
                    involved_variables = []
                    ref_variables = []
                    for node in max_node:
                        for var in node.variables_read+node.variables_written:
                            involved_variables.append(str(var))
                            if isinstance(var,StateVariable):
                                ref_variables.append(str(var))
                    ref_variables = list(set(ref_variables))
                    involved_variables = list(set(involved_variables))
                    all_checks.append({
                        "potential_checks": condition,
                        "involved_variables":involved_variables,
                        "descriptions": "",
                        "references": ref_variables
                    })
            res[function_name] = all_checks
                    
    return res

# --------------------------------------------------------------------- #
# quick demo                                                            #
# --------------------------------------------------------------------- #
def get_all_state_variables(path,file) -> List[str]:
    """
    Get all state variables used in the function.
    """
    config_path= os.path.join(path, file.replace('.sol', '.json'))
    with open(config_path, 'r') as f:
        config = json.load(f)
    compiler_helper = CompilerHelper(os.path.join(path,file), version=config['version'], optimization=config['opt'], via_ir=config['via_ir'], contract_name=config['contract_name'])
    slither = compiler_helper.get_slither()
    contract = compiler_helper._contract[0]
    res = []
    for var in contract.state_variables_ordered:
        temp = get_sources(var,file)
        if var.is_constant:
            continue
        res.append(temp)
    return res