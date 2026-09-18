"""
JARVIS Agent — top-level entry.
Receives a natural-language goal, plans, executes, and returns a result.
"""
from task_state import create_task, latest_task
from planner import plan
from executor import execute_plan
from tools import registry


def handle_request(message: str, api_key: str, model: str = "") -> dict:
    """
    Returns:
    {
      "handled": true/false,
      "task": {...},
      "reply": "..."
    }
    """
    if not message.strip():
        return {"handled": False, "reply": ""}

    # Try planner first — does it want a tool?
    context = ""
    last = latest_task()
    if last and last.status == "success":
        context = f"Previous task: {last.goal}\nResult: {last.result}"

    plan_result = plan(message, context, api_key, model)

    if plan_result.get("impossible"):
        # Let AI reply normally (frontend will call AI fallback)
        return {"handled": False, "reason": plan_result["impossible"]}

    steps = plan_result.get("steps") or []
    if not steps:
        return {"handled": False}

    task = create_task(message)
    exec_result = execute_plan(task, plan_result, api_key)

    return {
        "handled": True,
        "task": task.to_dict(),
        "reply": _summary(task, exec_result),
        "exec": exec_result,
    }


def resume_task(task_id: str, api_key: str = "") -> dict:
    """Continue a task after user confirmation."""
    from permissions import pop_confirmation
    from task_state import get_task
    task = get_task(task_id)
    if not task:
        return {"handled": False, "reply": "Task not found"}

    pending = pop_confirmation(task_id)
    if not pending:
        return {"handled": False, "reply": "No pending confirmation"}

    # Execute the confirmed tool
    tool = registry.get(pending["tool"])
    if not tool:
        return {"handled": False, "reply": "Tool vanished"}
    try:
        result = tool["fn"](pending["args"])
        task.add_log(event="confirmed_run", tool=pending["tool"], result=str(result))
        task.status = "success"
        task.result = str(result)
        return {"handled": True, "reply": f"✓ {result}", "task": task.to_dict()}
    except Exception as e:
        task.status = "failed"
        return {"handled": True, "reply": f"⚠ {e}", "task": task.to_dict()}


def _summary(task, exec_result: dict) -> str:
    lines = []
    for i, s in enumerate(task.steps, 1):
        status = s.get("status", "pending")
        icon = {"done": "✓", "failed": "✕", "waiting_confirmation": "⏳", "pending": "○"}.get(status, "•")
        lines.append(f"{icon} Step {i}: {s.get('tool')} — {s.get('observation','')[:80]}")
    head = "**Task " + task.status + "**"
    if task.result:
        head += f"\n\n{task.result}"
    return head + "\n\n" + "\n".join(lines)


def get_tool_list():
    return registry.all_tools()