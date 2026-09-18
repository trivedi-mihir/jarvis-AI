"""Real time and date."""
from datetime import datetime
from .registry import register


@register("time", "Get current time or date.", {
    "type": "object",
    "properties": {
        "action": {"type": "string", "enum": ["time", "date"]},
    },
    "required": ["action"],
})
def time_tool(args: dict) -> str:
    a = args.get("action")
    if a == "time":
        return datetime.now().strftime("%I:%M %p").lstrip("0")
    if a == "date":
        return datetime.now().strftime("%A, %B %d, %Y")
    raise ValueError(f"Unknown time action: {a}")