from slither.core.cfg.node import Node

def get_sources(node: Node) -> str:
    """
    Get the source code lines for a given node in the control flow graph.

    Args:
        node (Node): The node for which to retrieve the source code lines.

    Returns:
        List[str]: A list of source code lines corresponding to the node.
    """
    source_file = node.source_mapping.filename.absolute
    with open(source_file, "rb") as f:
        code = f.read()
    sta = node.source_mapping.start
    end = node.source_mapping.end
    lines = code[sta:end].decode("utf-8")
    return lines