"""Vision-language model client — enables true screen understanding."""
import base64
import json
import requests
from config import VISION_MODELS, PLANNER_MODEL_DEFAULT


def _b64_to_data_url(b64: str) -> str:
    return f"data:image/png;base64,{b64}"


def describe_screen(b64_png: str, api_key: str, question: str = "") -> str:
    """
    Send screenshot to a vision model and return its description.
    Falls back through a list of models until one works.
    """
    if not api_key:
        return "(No API key — cannot analyze screen)"

    prompt = question or (
        "Describe what is currently visible on this Windows screen. "
        "List any visible windows, buttons, menus, dialog boxes, and text. "
        "Be concise and structured."
    )

    for model in VISION_MODELS:
        try:
            r = requests.post(
                "https://openrouter.ai/api/v1/chat/completions",
                headers={
                    "Authorization": f"Bearer {api_key}",
                    "Content-Type": "application/json",
                    "HTTP-Referer": "http://127.0.0.1:5500",
                    "X-Title": "JARVIS Agent",
                },
                json={
                    "model": model,
                    "messages": [
                        {"role": "user", "content": [
                            {"type": "text", "text": prompt},
                            {"type": "image_url", "image_url": {"url": _b64_to_data_url(b64_png)}},
                        ]},
                    ],
                    "max_tokens": 600,
                },
                timeout=30,
            )
            if r.status_code == 200:
                data = r.json()
                text = data.get("choices", [{}])[0].get("message", {}).get("content", "")
                if text:
                    return f"[{model}]\n{text}"
            else:
                continue
        except Exception:
            continue

    return "(Vision models unavailable — check your OpenRouter key)"