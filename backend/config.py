"""JARVIS config — paths, models, permissions."""
import os
import platform

SYSTEM = platform.system()
HOME      = os.path.expanduser("~")
DESKTOP   = os.path.join(HOME, "Desktop")
DOWNLOADS = os.path.join(HOME, "Downloads")
DOCUMENTS = os.path.join(HOME, "Documents")
PICTURES  = os.path.join(HOME, "Pictures")
JARVIS_HOME = os.path.join(HOME, ".jarvis")
os.makedirs(JARVIS_HOME, exist_ok=True)

SAFE_LOCATIONS = {
    "desktop": DESKTOP, "downloads": DOWNLOADS,
    "documents": DOCUMENTS, "pictures": PICTURES, "home": HOME,
}

# Vision-capable models on OpenRouter (free where possible)
VISION_MODELS = [
    "openai/gpt-4o-mini",              # cheap, reliable
    "openai/gpt-4o",                   # best
    "anthropic/claude-3.5-sonnet",     # excellent vision
    "google/gemini-2.0-flash-exp:free",# free, vision
]

PLANNER_MODEL_DEFAULT = "openai/gpt-4o-mini"

# Operations that always require user confirmation
DANGEROUS_OPERATIONS = {
    "delete_path", "shutdown", "restart", "sleep", "lock_screen",
    "install_software", "kill_process", "send_email", "make_purchase",
    "modify_registry", "format_disk",
}

MAX_AGENT_STEPS = 25          # hard cap on autonomous actions
STEP_DELAY = 0.6              # seconds between actions
SCREENSHOT_DIR = os.path.join(JARVIS_HOME, "screenshots")
os.makedirs(SCREENSHOT_DIR, exist_ok=True)