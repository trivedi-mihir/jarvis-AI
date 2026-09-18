"""System information and control."""
import platform
import os
import time
import subprocess
from .registry import register

try:
    import psutil
except ImportError:
    psutil = None


def _fmt(n):
    for u in ["B","KB","MB","GB","TB"]:
        if n < 1024: return f"{n:.1f} {u}"
        n /= 1024
    return f"{n:.1f} PB"


@register("system", "Read system information or perform system actions.", {
    "type": "object",
    "properties": {
        "action": {"type": "string",
            "enum": ["info", "ram", "cpu", "disk", "battery", "processes",
                     "shutdown", "restart", "sleep", "lock_screen"]},
    },
    "required": ["action"],
})
def system(args: dict) -> str:
    a = args.get("action")

    if a == "info":
        return (f"OS: {platform.system()} {platform.release()}\n"
                f"Host: {platform.node()}\n"
                f"CPU: {platform.processor() or platform.machine()}\n"
                f"RAM: {_fmt(psutil.virtual_memory().total) if psutil else '?'}\n"
                f"Python: {platform.python_version()}")

    if a == "ram":
        vm = psutil.virtual_memory()
        return f"{_fmt(vm.total)} total, {_fmt(vm.available)} free ({vm.percent}% used)"

    if a == "cpu":
        return f"{psutil.cpu_percent(interval=0.5)}% usage, {psutil.cpu_count()} cores"

    if a == "disk":
        root = "C:\\" if os.name == "nt" else "/"
        du = psutil.disk_usage(root)
        return f"{_fmt(du.used)} used / {_fmt(du.total)} total ({du.percent}%)"

    if a == "battery":
        b = psutil.sensors_battery()
        if not b: return "No battery"
        return f"{b.percent:.0f}% ({'charging' if b.power_plugged else 'on battery'})"

    if a == "processes":
        ps = []
        for p in psutil.process_iter(["name", "memory_percent"]):
            try:
                ps.append((p.info["name"], p.info["memory_percent"]))
            except: pass
        ps.sort(key=lambda x: x[1] or 0, reverse=True)
        return "\n".join(f"{n} — {m:.1f}%" for n, m in ps[:15])

    if a == "shutdown":
        subprocess.run(["shutdown", "/s", "/t", "30"])
        return "Shutting down in 30s — type 'shutdown /a' to cancel"
    if a == "restart":
        subprocess.run(["shutdown", "/r", "/t", "30"])
        return "Restarting in 30s"
    if a == "sleep":
        subprocess.run(["rundll32.exe", "powrprof.dll,SetSuspendState", "0,1,0"])
        return "Sleeping"
    if a == "lock_screen":
        subprocess.run(["rundll32.exe", "user32.dll,LockWorkStation"])
        return "Locked"

    raise ValueError(f"Unknown system action: {a}")