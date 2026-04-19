import pkgutil
import importlib
from typing import List
from .base import Tool


def _discover_tools() -> List[Tool]:
    tools = []
    package_name = __name__
    package_path = __path__

    for _, module_name, _ in pkgutil.iter_modules(package_path):
        module = importlib.import_module(f"{package_name}.{module_name}")
        for attr_name in dir(module):
            attr = getattr(module, attr_name)
            if isinstance(attr, type) and issubclass(attr, Tool) and attr is not Tool:
                tools.append(attr())

    return tools


TOOLS = _discover_tools()

__all__ = ["Tool", "TOOLS"] + [tool.__class__.__name__ for tool in TOOLS]
