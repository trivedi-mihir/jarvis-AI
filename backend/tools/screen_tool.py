"""Screen capture and analysis primitives."""
import os
from datetime import datetime
import base64
from io import BytesIO
from config import SCREENSHOT_DIR
from .registry import register

try:
    import pyautogui
    pyautogui.FAILSAFE = False
except ImportError:
    pyautogui = None

try:
    from PIL import Image
except ImportError:
    Image = None


@register("screen", "Take a screenshot or get screen info.", {
    "type": "object",
    "properties": {
        "action": {"type": "string", "enum": ["screenshot", "size"]},
    },
    "required": ["action"],
})
def screen(args: dict) -> str:
    action = args.get("action")

    if not pyautogui or not Image:
        raise RuntimeError("pyautogui/Pillow not installed")

    if action == "size":
        w, h = pyautogui.size()
        return f"{w}x{h}"

    if action == "screenshot":
        ts = datetime.now().strftime("%Y%m%d_%H%M%S")
        path = os.path.join(SCREENSHOT_DIR, f"shot_{ts}.png")
        img = pyautogui.screenshot()
        img.save(path)
        return path

    raise ValueError(f"Unknown screen action: {action}")


def screenshot_base64() -> str:
    """Return base64 PNG for vision models."""
    if not pyautogui: return ""
    img = pyautogui.screenshot()
    buf = BytesIO()
    img.save(buf, format="PNG")
    return base64.b64encode(buf.getvalue()).decode()