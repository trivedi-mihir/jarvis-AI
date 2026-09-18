"""Executes a plan step-by-step, observing after each action."""
import time
from config import MAX_AGENT_STEPS, STEP_DELAY
from task_state import Task
from tools import registry
from permissions import is_dangerous, request_confirmation


def execute_plan(task: Task, plan: dict, api_key: str = "") -> dict:
    """
    Runs the plan. Returns:
    {
      "status": "success"|"failed"|"waiting_input",
      "result": "summary",
      "steps_done": N
    }
    """
    steps = plan.get("steps") or []
    if not steps:
        task.status = "success"
        return {"status": "success", "result": plan.get("thought", "Nothing to do."), "steps_done": 0}

    task.set_plan([{"tool": s.get("tool"), "args": s.get("args", {}),
                    "status": "pending", "observation": ""} for s in steps])

    task.status = "running"

    for idx, step in enumerate(steps[:MAX_AGENT_STEPS]):
        task.current_step = idx
        tool_name = step.get("tool")
        args      = step.get("args", {})

        # --- Safety check ---
        if is_dangerous(tool_name, args):
            token = f"c{int(time.time())}_{idx}"
            request_confirmation(token, tool_name, args)
            task.status = "waiting_input"
            task.mark_step(idx, "waiting_confirmation")
            task.add_log(event="needs_confirmation", tool=tool_name, args=args, token=token)
            return {
                "status": "waiting_input",
                "token": token,
                "description": f"Confirmation needed: {tool_name} {args}",
                "steps_done": idx,
            }

        # --- Look up tool ---
        tool = registry.get(tool_name)
        if not tool:
            task.mark_step(idx, "failed", f"Unknown tool: {tool_name}")
            task.add_log(event="unknown_tool", tool=tool_name)
            continue

        # --- Execute ---
        task.add_log(event="execute", tool=tool_name, args=args)
        try:
            result = tool["fn"](args)
            obs = str(result)[:800]
            task.mark_step(idx, "done", obs)
            task.add_log(event="ok", tool=tool_name, result=obs)
        except Exception as e:
            err = str(e)
            task.mark_step(idx, "failed", err)
            task.add_log(event="error", tool=tool_name, error=err)
            task.status = "failed"
            task.result = f"Step {idx+1} failed: {err}"
            return {"status": "failed", "result": task.result, "steps_done": idx}

        time.sleep(STEP_DELAY)

    task.status = "success"
    task.result = "All steps completed"
    return {"status": "success", "result": task.result, "steps_done": len(steps)}