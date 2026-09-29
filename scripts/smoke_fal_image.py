"""Smoke test: prove the fal.ai key works end-to-end with a real image call.

Generates one tiny 1024x576 image with the cheapest configured route, saves it
under the project, and prints the ToolResult. This is a live, billable call but
the smallest one available (fractions of a cent).

Usage:
    .venv\\Scripts\\python.exe scripts/smoke_fal_image.py
"""

from __future__ import annotations

import io
import json
import os
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

out_dir = ROOT / "projects" / "nha-su-va-bat-rong" / "assets" / "images"
out_dir.mkdir(parents=True, exist_ok=True)
out_path = out_dir / "smoke_test_fal.jpg"

print("fal key present:", bool((os.environ.get("FAL_KEY") or "").strip()))
print("target:", out_path)
print("--- calling image_selector (preferred flux, tiny size) ---")

selector = registry.get("image_selector")
result = selector.execute(
    {
        "prompt": (
            "A single yellow autumn leaf resting on wet grey stone paving, "
            "warm golden-hour side light, shallow depth of field, photorealistic, "
            "35mm film grain"
        ),
        "preferred_provider": "flux",
        "width": 1024,
        "height": 576,
        "seed": 4242,
        "output_path": str(out_path),
    }
)

print("success:", result.success)
print("error  :", result.error)
try:
    print("data   :", json.dumps(result.data, ensure_ascii=False, indent=2)[:1500])
except Exception:  # noqa: BLE001
    print("data   :", result.data)

print("file exists:", out_path.exists(), "size:", out_path.stat().st_size if out_path.exists() else 0)
