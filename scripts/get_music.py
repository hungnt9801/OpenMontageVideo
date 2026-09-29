"""Download a royalty-free music bed from Pixabay (free, no key required).

Usage:
    .venv\\Scripts\\python.exe scripts/get_music.py
"""

from __future__ import annotations

import io
import json
import sys
from pathlib import Path

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

try:
    from dotenv import load_dotenv

    load_dotenv(ROOT / ".env", override=False)
except Exception:  # noqa: BLE001
    pass

from tools.tool_registry import registry  # noqa: E402

registry.discover()
tool = registry.get("pixabay_music")
print("tool status:", tool.get_info().get("status"))

OUT = ROOT / "projects" / "nha-su-va-bat-rong" / "assets" / "music"
OUT.mkdir(parents=True, exist_ok=True)

QUERIES = [
    "meditation ambient bamboo flute singing bowl calm",
    "zen temple ambient no drums",
    "sparse piano meditation ambient",
]

for index, query in enumerate(QUERIES):
    out_path = OUT / f"bed_candidate_{index + 1}.mp3"
    print(f"\n--- query: {query}")
    try:
        result = tool.execute({
            "query": query,
            "min_duration": 90,
            "max_duration": 240,
            "output_path": str(out_path),
        })
    except Exception as exc:  # noqa: BLE001
        print("   error:", type(exc).__name__, exc)
        continue

    print("   success:", result.success, "| error:", result.error)
    if result.data:
        print("   data:", json.dumps(result.data, ensure_ascii=False)[:700])
    if out_path.exists():
        print(f"   saved: {out_path.name}  {out_path.stat().st_size} bytes")
    if index == 0 and out_path.exists():
        break
