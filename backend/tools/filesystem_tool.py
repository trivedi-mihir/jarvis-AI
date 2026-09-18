"""Filesystem operations."""
import os
import shutil
from config import SAFE_LOCATIONS
from .registry import register


def _resolve(path: str) -> str:
    if not path:
        return SAFE_LOCATIONS["desktop"]
    p = path.strip().strip('"').strip("'")
    low = p.lower()
    if low in SAFE_LOCATIONS:
        return SAFE_LOCATIONS[low]
    if os.path.isabs(p):
        return os.path.expandvars(os.path.expanduser(p))
    # Try known base folders
    for base in SAFE_LOCATIONS.values():
        candidate = os.path.join(base, p)
        if os.path.exists(candidate):
            return candidate
    return os.path.expanduser(p)


@register("filesystem", "File and folder operations: create, read, write, move, copy, delete, list, find.", {
    "type": "object",
    "properties": {
        "action": {"type": "string",
            "enum": ["create_folder", "create_file", "read", "write", "append",
                     "move", "copy", "rename", "delete", "list", "find", "exists"]},
        "path": {"type": "string", "description": "Target path or folder name"},
        "content": {"type": "string", "description": "Content to write (for write/append)"},
        "destination": {"type": "string", "description": "Dest for move/copy/rename"},
        "pattern": {"type": "string", "description": "Glob pattern for 'find'"},
        "location": {"type": "string", "description": "Base folder: desktop/downloads/documents/pictures/home"},
    },
    "required": ["action"],
})
def filesystem(args: dict) -> str:
    action = args.get("action")
    raw_path = args.get("path") or ""
    location = args.get("location") or "desktop"

    if action == "create_folder":
        name = raw_path or args.get("name") or "New Folder"
        base = _resolve(location)
        path = os.path.join(base, name) if not os.path.isabs(name) else name
        os.makedirs(path, exist_ok=True)
        return f"Created folder: {path}"

    if action == "create_file":
        path = _resolve(raw_path)
        if not os.path.isabs(path):
            path = os.path.join(_resolve(location), raw_path)
        os.makedirs(os.path.dirname(path) or ".", exist_ok=True)
        with open(path, "w", encoding="utf-8") as f:
            f.write(args.get("content", ""))
        return f"Created file: {path}"

    if action == "read":
        path = _resolve(raw_path)
        with open(path, "r", encoding="utf-8", errors="ignore") as f:
            data = f.read()
        return data[:4000]

    if action == "write":
        path = _resolve(raw_path)
        os.makedirs(os.path.dirname(path) or ".", exist_ok=True)
        with open(path, "w", encoding="utf-8") as f:
            f.write(args.get("content", ""))
        return f"Wrote to {path}"

    if action == "append":
        path = _resolve(raw_path)
        with open(path, "a", encoding="utf-8") as f:
            f.write(args.get("content", ""))
        return f"Appended to {path}"

    if action == "move":
        src = _resolve(raw_path)
        dst = _resolve(args.get("destination", ""))
        shutil.move(src, dst)
        return f"Moved {src} -> {dst}"

    if action == "copy":
        src = _resolve(raw_path)
        dst = _resolve(args.get("destination", ""))
        if os.path.isdir(src): shutil.copytree(src, dst, dirs_exist_ok=True)
        else: shutil.copy2(src, dst)
        return f"Copied {src} -> {dst}"

    if action == "rename":
        src = _resolve(raw_path)
        dst = os.path.join(os.path.dirname(src), args.get("destination", "renamed"))
        os.rename(src, dst)
        return f"Renamed -> {dst}"

    if action == "delete":
        path = _resolve(raw_path)
        if not os.path.exists(path):
            return f"Not found: {path}"
        if os.path.isdir(path): shutil.rmtree(path)
        else: os.remove(path)
        return f"Deleted: {path}"

    if action == "list":
        base = _resolve(location) if location else _resolve(raw_path) if raw_path else SAFE_LOCATIONS["desktop"]
        if os.path.isfile(base):
            return f"File: {base}"
        items = []
        for name in sorted(os.listdir(base))[:60]:
            full = os.path.join(base, name)
            items.append(f"[{'DIR' if os.path.isdir(full) else 'FILE'}] {name}")
        return f"Contents of {base}:\n" + "\n".join(items)

    if action == "find":
        base = _resolve(location)
        pattern = args.get("pattern", "*")
        results = []
        for root, dirs, files in os.walk(base):
            dirs[:] = [d for d in dirs if not d.startswith((".", "$"))]
            for f in files:
                if pattern.lower() in f.lower():
                    results.append(os.path.join(root, f))
                    if len(results) >= 30: break
            if len(results) >= 30: break
        return "\n".join(results) if results else "No matches"

    if action == "exists":
        path = _resolve(raw_path)
        return "EXISTS" if os.path.exists(path) else "NOT FOUND"

    raise ValueError(f"Unknown filesystem action: {action}")