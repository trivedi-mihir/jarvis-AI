"""Mouse and keyboard input via pyautogui."""
from .registry import register

try:
    import pyautogui
    pyautogui.FAILSAFE = True
except ImportError:
    pyautogui = None


def _ok():
    if not pyautogui: raise RuntimeError("pyautogui missing")


@register("input", "Control mouse and keyboard.", {
    "type": "object",
    "properties": {
        "action": {"type": "string",
            "enum": ["click", "double_click", "right_click", "move", "drag",
                     "scroll", "type", "press", "hotkey", "wait"]},
        "x": {"type": "integer"}, "y": {"type": "integer"},
        "text": {"type": "string"},
        "key": {"type": "string"},
        "keys": {"type": "array", "items": {"type": "string"}},
        "amount": {"type": "integer"},
        "duration": {"type": "number"},
    },
    "required": ["action"],
})
def input_tool(args: dict) -> str:
    _ok()
    a = args.get("action")

    if a == "click":
        pyautogui.click(args.get("x"), args.get("y"), duration=0.15)
        return f"Clicked ({args.get('x')},{args.get('y')})"
    if a == "double_click":
        pyautogui.doubleClick(args.get("x"), args.get("y"))
        return "Double-clicked"
    if a == "right_click":
        pyautogui.rightClick(args.get("x"), args.get("y"))
        return "Right-clicked"
    if a == "move":
        pyautogui.moveTo(args.get("x"), args.get("y"), duration=args.get("duration", 0.2))
        return f"Moved to ({args.get('x')},{args.get('y')})"
    if a == "drag":
        x, y = args.get("x"), args.get("y")
        pyautogui.dragTo(x, y, duration=args.get("duration", 0.4), button="left")
        return f"Dragged to ({x},{y})"
    if a == "scroll":
        pyautogui.scroll(args.get("amount", -5))
        return "Scrolled"
    if a == "type":
        pyautogui.typewrite(args.get("text", ""), interval=0.02)
        return f"Typed {len(args.get('text',''))} chars"
    if a == "press":
        pyautogui.press(args.get("key", "enter"))
        return f"Pressed {args.get('key')}"
    if a == "hotkey":
        keys = args.get("keys") or []
        if not keys: raise ValueError("keys required")
        pyautogui.hotkey(*keys)
        return f"Hotkey {'+'.join(keys)}"
    if a == "wait":
        import time; time.sleep(args.get("duration", 1.0))
        return f"Waited {args.get('duration', 1.0)}s"

    raise ValueError(f"Unknown input action: {a}")