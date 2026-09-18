"""Application launch / close / list."""
import os
import subprocess
import shutil
import platform
from .registry import register

SYSTEM = platform.system()

# Well-known Windows locations to search
WIN_DIRS = [
    r"C:\Program Files",
    r"C:\Program Files (x86)",
    os.path.expandvars(r"%LOCALAPPDATA%\Programs"),
    os.path.expandvars(r"%APPDATA%"),
    os.path.expandvars(r"%PROGRAMDATA%\Microsoft\Windows\Start Menu\Programs"),
]


def _find_exe(app_name: str):
    """Best-effort executable discovery."""
    name = app_name.lower().strip()

    # Common shell commands
    for cmd in (app_name, app_name + ".exe"):
        found = shutil.which(cmd)
        if found:
            return found

    # Search known folders (shallow — depth 4)
    tokens = [name, name.replace(" ", "")]
    for base in WIN_DIRS:
        if not os.path.isdir(base): continue
        for root, dirs, files in os.walk(base):
            depth = root[len(base):].count(os.sep)
            if depth > 4:
                dirs[:] = []
                continue
            for f in files:
                fl = f.lower()
                if fl.endswith(".exe") and any(t in fl for t in tokens):
                    return os.path.join(root, f)
    return None


@register("application", "Launch, close, or list applications installed on the computer.", {
    "type": "object",
    "properties": {
        "action": {"type": "string", "enum": ["open", "close", "list"]},
        "name":   {"type": "string", "description": "Application name, e.g. 'chrome', 'notepad'"},
    },
    "required": ["action"],
})
def application(args: dict) -> str:
    action = args.get("action")
    name   = (args.get("name") or "").strip()

    if action == "list":
        # Quick scan of Program Files & start menu
        found = []
        for base in WIN_DIRS[:3]:
            if not os.path.isdir(base): continue
            for item in os.listdir(base):
                full = os.path.join(base, item)
                if os.path.isdir(full):
                    found.append(item)
        return "Installed applications (top-level):\n" + "\n".join(sorted(set(found))[:80])

    if action == "open":
        if not name:
            raise ValueError("Application name required")

        # 1. Known shortcuts
        shortcuts = {
            "chrome": "chrome.exe", "firefox": "firefox.exe", "edge": "msedge.exe",
            "notepad": "notepad.exe", "calculator": "calc.exe", "calc": "calc.exe",
            "explorer": "explorer.exe", "file explorer": "explorer.exe",
            "paint": "mspaint.exe", "cmd": "cmd.exe", "terminal": "wt.exe",
            "powershell": "powershell.exe", "task manager": "taskmgr.exe",
            "vs code": "code.exe", "vscode": "code.exe", "code": "code.exe",
            "spotify": "Spotify.exe", "discord": "Discord.exe",
        }
        s = shortcuts.get(name.lower())
        if s:
            found = shutil.which(s)
            if found:
                subprocess.Popen([found])
                return f"Launched {name}"

        # 2. Discovery
        exe = _find_exe(name)
        if exe:
            try:
                os.startfile(exe)
                return f"Launched {name} ({exe})"
            except Exception:
                subprocess.Popen([exe])
                return f"Launched {name} ({exe})"

        # 3. Let Windows try
        try:
            os.startfile(name)
            return f"Launched {name} via Windows"
        except Exception:
            raise RuntimeError(f"Could not find application: {name}")

    if action == "close":
        if not name:
            raise ValueError("Application name required")
        proc = name if name.endswith(".exe") else name + ".exe"
        r = subprocess.run(["taskkill", "/F", "/IM", proc],
                           capture_output=True, text=True)
        if r.returncode != 0:
            raise RuntimeError(f"Could not close {name}")
        return f"Closed {name}"

    raise ValueError(f"Unknown application action: {action}")