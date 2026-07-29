#!/usr/bin/env python3
from pathlib import Path
import re

ROOT = Path(__file__).resolve().parents[1]
EXCLUDED = {".git", "__pycache__"}
FORBIDDEN = ("shaan" + "sisodia", "tail100d11" + ".ts.net", "SISO_Workspace/" + ".SystemDB",
             "OPENROUTER_" + "API_KEY=", "youtube-ai-" + "research/.env")
CREDENTIAL = re.compile(r"\b(?:sk|gh[opsu])[-_][A-Za-z0-9_-]{16,}\b")
checked = 0
for path in ROOT.rglob("*"):
    if not path.is_file() or any(part in EXCLUDED for part in path.parts):
        continue
    try:
        text = path.read_text(encoding="utf-8")
    except UnicodeDecodeError:
        continue
    checked += 1
    if any(value in text for value in FORBIDDEN) or CREDENTIAL.search(text):
        raise SystemExit(f"publication check failed: {path.relative_to(ROOT)}")
print(f"EVIDENCE_ENGINES_PUBLICATION_OK ({checked} text files)")
