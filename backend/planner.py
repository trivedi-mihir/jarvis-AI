"""
Planner — turns a user goal into a plan of tool calls.
Uses an LLM (OpenRouter) with function-calling style JSON output.
"""
import json
import re
import requests
from config import PLANNER_MODEL_DEFAULT
from tools import registry


PLANNER_SYSTEM = """You are JARVIS, an autonomous Windows computer agent.
You MUST respond ONLY with valid JSON matching this schema:

{
  "thought": "brief reasoning",
  "steps": [
    {"tool": "tool_name", "args": {...}},
    ...
  ],
  "needs_confirmation": false
}

Rules:
- Use ONLY tools from the provided tool list.
- If the task is a single action, return one step.
- If multiple actions are needed, return them in ORDER.
- Never invent tools.
- If the user's request cannot be done with the available tools, respond with:
  {"thought": "...", "steps": [], "needs_confirmation": false, "impossible": "reason"}
"""


def _extract_json(text: str) -> dict:
    """Robustly extract JSON from model output."""
    text = text.strip()
    # Strip code fences
    text = re.sub(r"^```(?:json)?\s*", "", text)
    text = re.sub(r"\s*```$", "", text)
    # Try direct parse
    try:
        return json.loads(text)
    except Exception:
        pass
    # Find first {...}
    m = re.search(r"\{[\s\S]*\}", text)
    if m:
        try:
            return json.loads(m.group(0))
        except Exception:
            pass
    return {"thought": text[:200], "steps": []}


def plan(goal: str, context: str, api_key: str, model: str = "") -> dict:
    """
    Ask the LLM to produce a JSON plan.
    Returns: {"thought", "steps":[{tool,args}], "needs_confirmation", "impossible"?}
    """
    if not api_key:
        return {
            "thought": "No API key — cannot plan autonomously.",
            "steps": [],
            "impossible": "Add your OpenRouter API key in Settings.",
        }

    tools = registry.all_tools()

    tool_doc = "\n".join(
        f"- {t['name']}: {t['description']}\n  schema: {json.dumps(t['schema'])}"
        for t in tools
    )

    user = f"""USER GOAL:
{goal}

CONVERSATION CONTEXT:
{context or '(none)'}

AVAILABLE TOOLS:
{tool_doc}

Return ONLY the JSON plan."""

    model = model or PLANNER_MODEL_DEFAULT
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
                    {"role": "system", "content": PLANNER_SYSTEM},
                    {"role": "user", "content": user},
                ],
                "temperature": 0.2,
                "max_tokens": 900,
            },
            timeout=45,
        )
        if r.status_code != 200:
            return {
                "thought": f"Planner HTTP {r.status_code}",
                "steps": [],
                "impossible": r.text[:200],
            }
        data = r.json()
        content = data.get("choices", [{}])[0].get("message", {}).get("content", "")
        parsed = _extract_json(content)
        if "steps" not in parsed:
            parsed["steps"] = []
        return parsed
    except Exception as e:
        return {"thought": f"Planner error: {e}", "steps": [], "impossible": str(e)}