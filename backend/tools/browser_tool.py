"""Browser control — open URLs, search, and interact via pyautogui."""
import webbrowser
import time
import urllib.parse
from .registry import register

try:
    import pyautogui
except ImportError:
    pyautogui = None


@register("browser", "Open websites, search engines, and interact with the browser.", {
    "type": "object",
    "properties": {
        "action": {"type": "string", "enum": ["open", "search", "youtube_search", "type", "press", "scroll", "back"]},
        "url":    {"type": "string"},
        "query":  {"type": "string"},
        "text":   {"type": "string"},
        "key":    {"type": "string"},
        "amount": {"type": "integer"},
    },
    "required": ["action"],
})
def browser(args: dict) -> str:
    action = args.get("action")

    if action == "open":
        url = args.get("url", "").strip()
        if not url.startswith(("http://", "https://")):
            url = "https://" + url
        webbrowser.open(url)
        return f"Opened {url}"

    if action == "search":
        q = args.get("query", "")
        webbrowser.open("https://www.google.com/search?q=" + urllib.parse.quote(q))
        return f"Searched Google: {q}"

    if action == "youtube_search":
        q = args.get("query", "")
        webbrowser.open("https://www.youtube.com/results?search_query=" + urllib.parse.quote(q))
        return f"Searched YouTube: {q}"

    if action == "type":
        if not pyautogui: raise RuntimeError("pyautogui missing")
        time.sleep(0.5)
        pyautogui.typewrite(args.get("text", ""), interval=0.03)
        return f"Typed into browser"

    if action == "press":
        if not pyautogui: raise RuntimeError("pyautogui missing")
        pyautogui.press(args.get("key", "enter"))
        return f"Pressed {args.get('key')}"

    if action == "scroll":
        if not pyautogui: raise RuntimeError("pyautogui missing")
        pyautogui.scroll(args.get("amount", -5))
        return f"Scrolled {args.get('amount', -5)}"

    if action == "back":
        if not pyautogui: raise RuntimeError("pyautogui missing")
        pyautogui.hotkey("alt", "left")
        return "Went back"

    raise ValueError(f"Unknown browser action: {action}")