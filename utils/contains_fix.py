from slither.core.declarations.function import Function
def __eq__(self, item):
    if hasattr(item, "id") and hasattr(self, "id"):
        return self.id == item.id
    else:
        return False
Function.__hash__ = lambda self: hash(self.id)
Function.__eq__  = __eq__
