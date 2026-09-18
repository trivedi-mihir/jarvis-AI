"""Read text/PDF files."""
import os
from .registry import register


@register("document", "Read a document's content (txt, md, pdf, json, csv).", {
    "type": "object",
    "properties": {
        "path": {"type": "string"},
    },
    "required": ["path"],
})
def document(args: dict) -> str:
    path = args.get("path", "")
    if not path:
        raise ValueError("path required")
    path = os.path.expanduser(path)
    if not os.path.exists(path):
        raise FileNotFoundError(path)

    ext = os.path.splitext(path)[1].lower()

    if ext == ".pdf":
        try:
            from pypdf import PdfReader
        except ImportError:
            raise RuntimeError("Install pypdf: pip install pypdf")
        reader = PdfReader(path)
        text = "\n".join((p.extract_text() or "") for p in reader.pages[:20])
        return text[:6000]

    with open(path, "r", encoding="utf-8", errors="ignore") as f:
        return f.read()[:6000]