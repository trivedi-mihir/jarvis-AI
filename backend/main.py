"""JARVIS FastAPI server — local-only agent."""
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import Optional
import uvicorn

import agent
from task_state import latest_task, get_task
from tools import registry
from tools.screen_tool import screenshot_base64
from vision import describe_screen


app = FastAPI(title="JARVIS Agent", version="7.0.0")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"], allow_credentials=False,
    allow_methods=["*"], allow_headers=["*"],
)


class ChatReq(BaseModel):
    message: str
    api_key: str = ""
    model:   str = ""


class ConfirmReq(BaseModel):
    task_id: str
    api_key: str = ""


class VisionReq(BaseModel):
    api_key: str = ""
    question: str = ""


@app.get("/")
def root():
    return {"name": "JARVIS Agent", "version": "7.0.0"}


@app.get("/status")
def status():
    return {
        "ok": True,
        "version": "7.0.0",
        "capabilities": registry.names(),
    }


@app.post("/chat")
def chat(req: ChatReq):
    result = agent.handle_request(req.message, req.api_key, req.model)
    if result.get("handled"):
        # Include debug task
        result["task"] = latest_task().to_dict() if latest_task() else None
    return result


@app.post("/confirm")
def confirm(req: ConfirmReq):
    return agent.resume_task(req.task_id, req.api_key)


@app.get("/task/latest")
def task_latest():
    t = latest_task()
    return t.to_dict() if t else None


@app.get("/tools")
def tools_list():
    return registry.all_tools()


@app.post("/vision")
def vision(req: VisionReq):
    b64 = screenshot_base64()
    description = describe_screen(b64, req.api_key, req.question)
    return {"screenshot_b64": b64, "description": description}


if __name__ == "__main__":
    print("=" * 60)
    print("  JARVIS AGENT SERVER")
    print("  http://127.0.0.1:8000")
    print("=" * 60)
    uvicorn.run(app, host="127.0.0.1", port=8000, log_level="info")