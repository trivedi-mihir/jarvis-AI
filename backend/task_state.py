"""Long-running task state — supports multi-step plans."""
import time
import uuid
from typing import List, Dict, Any, Optional


class Task:
    def __init__(self, goal: str):
        self.id = uuid.uuid4().hex[:8]
        self.goal = goal
        self.status = "pending"      # pending | running | waiting_input | success | failed
        self.steps: List[Dict[str, Any]] = []
        self.current_step = 0
        self.created_at = time.time()
        self.updated_at = time.time()
        self.log: List[Dict[str, Any]] = []
        self.result: Optional[str] = None

    def set_plan(self, steps: List[Dict[str, Any]]):
        self.steps = steps
        self.updated_at = time.time()

    def mark_step(self, idx: int, status: str, observation: str = ""):
        if 0 <= idx < len(self.steps):
            self.steps[idx]["status"] = status
            self.steps[idx]["observation"] = observation
        self.updated_at = time.time()

    def add_log(self, **kwargs):
        kwargs["ts"] = time.time()
        self.log.append(kwargs)
        self.updated_at = time.time()

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "goal": self.goal,
            "status": self.status,
            "current_step": self.current_step,
            "steps": self.steps,
            "log": self.log[-50:],
            "result": self.result,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
        }


# In-memory store (single-user local agent)
_TASKS: Dict[str, Task] = {}


def create_task(goal: str) -> Task:
    t = Task(goal)
    _TASKS[t.id] = t
    return t


def get_task(tid: str) -> Optional[Task]:
    return _TASKS.get(tid)


def latest_task() -> Optional[Task]:
    if not _TASKS:
        return None
    return max(_TASKS.values(), key=lambda t: t.created_at)