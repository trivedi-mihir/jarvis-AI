"""Dynamic tool registry — tools self-register on import."""
from typing import Callable, Dict, Any, List

_TOOLS: Dict[str, Dict[str, Any]] = {}


def register(name: str, description: str, schema: Dict[str, Any]):
    """
    Decorator: @register('open_app', 'Open an application', {...})
    Registers a tool callable under `name`.
    """
    def wrapper(fn: Callable):
        _TOOLS[name] = {
            "name": name,
            "description": description,
            "schema": schema,
            "fn": fn,
        }
        return fn
    return wrapper


def get(name: str):
    return _TOOLS.get(name)


def all_tools() -> List[Dict[str, Any]]:
    return [
        {"name": t["name"], "description": t["description"], "schema": t["schema"]}
        for t in _TOOLS.values()
    ]


def names() -> List[str]:
    return list(_TOOLS.keys())