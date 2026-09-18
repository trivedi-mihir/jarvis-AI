"""Permission model — dangerous operations must be confirmed."""
from config import DANGEROUS_OPERATIONS
from typing import Dict, Any


# Pending confirmations: confirmation_token -> {op, args, created}
_PENDING: Dict[str, Dict[str, Any]] = {}


def is_dangerous(tool: str, args: Dict[str, Any]) -> bool:
    if tool in DANGEROUS_OPERATIONS:
        return True
    # Any filesystem delete
    if tool == "filesystem" and args.get("action") in ("delete", "delete_folder", "rmdir"):
        return True
    return False


def describe_operation(tool: str, args: Dict[str, Any]) -> str:
    if tool == "filesystem":
        a = args.get("action")
        if a in ("delete", "delete_folder"):
            return f"Permanently delete: {args.get('path')}"
    if tool == "system":
        a = args.get("action")
        if a in ("shutdown", "restart", "sleep", "lock_screen"):
            return f"System action: {a}"
    return f"Run tool '{tool}' with args: {args}"


def request_confirmation(token_id: str, tool: str, args: Dict[str, Any]):
    import time
    _PENDING[token_id] = {
        "tool": tool,
        "args": args,
        "created": time.time(),
        "description": describe_operation(tool, args),
    }


def pop_confirmation(token_id: str):
    return _PENDING.pop(token_id, None)


def get_confirmation(token_id: str):
    return _PENDING.get(token_id)


def list_pending():
    return dict(_PENDING)