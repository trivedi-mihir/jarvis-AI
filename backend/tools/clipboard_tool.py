"""Clipboard read/write."""
from .registry import register

try:
    import pyperclip
except ImportError:
    pyperclip = None


@register("clipboard", "Read or write the clipboard.", {
    "type": "object",
    "properties": {
        "action": {"type": "string", "enum": ["read", "write"]},
        "text":   {"type": "string"},
    },
    "required": ["action"],
})
def clipboard(args: dict) -> str:
    if not pyperclip:
        raise RuntimeError("pyperclip not installed")
    a = args.get("action")
    if a == "read":
        return pyperclip.paste() or ""
    if a == "write":
        pyperclip.copy(args.get("text", ""))
        return "Copied to clipboard"
    raise ValueError(f"Unknown clipboard action: {a}")