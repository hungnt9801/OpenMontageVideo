"""Generate the 2-image SAMPLE for project nha-su-va-bat-rong (Muc 1).

Scene 1 (hook, wide, no people — lowest risk) and Scene 4 (ECU of the alms bowl,
the central symbol). Both at native 1080x1920 (9:16) to verify the portrait
preset renders at the exact delivery aspect ratio.

Live, billable: 2 x ~$0.083 = ~$0.17.

Usage:
    .venv\\Scripts\\python.exe scripts/gen_sample_images.py
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
selector = registry.get("image_selector")

OUT_DIR = ROOT / "projects" / "nha-su-va-bat-rong" / "assets" / "sample"
OUT_DIR.mkdir(parents=True, exist_ok=True)

# FLUX has no negative prompt — describe only what is wanted.
# Structure: subject -> action/state -> setting -> lighting -> technical.
STYLE_TAIL = (
    "Photorealistic cinematic still, golden-hour side light with long shadows, "
    "volumetric sun shafts, drifting dust motes, thin ground mist in the distance, "
    "shallow depth of field, 35mm film grain, warm amber #F5C518, earth brown "
    "#8C5A2B and shadow brown #2B2118 palette, vertical 9:16 composition, "
    "generous negative space in the upper third."
)

SCENES = [
    {
        "id": "s01_courtyard",
        "seed": 1101,
        "prompt": (
            "An ancient East-Asian Buddhist temple courtyard in late autumn, completely "
            "empty and deserted at golden hour. Weathered grey stone paving is covered "
            "with fallen yellow maple leaves, dark timber columns and a curved clay-tile "
            "roof edge frame the scene, and a bronze incense burner on the right releases "
            "thick curling smoke. " + STYLE_TAIL
        ),
    },
    {
        "id": "s04_bowl",
        "seed": 1104,
        "prompt": (
            "An extreme close-up of a single empty ceramic alms bowl with a cracked glaze, "
            "resting on wet grey stone paving in an ancient East-Asian temple courtyard, "
            "one yellow autumn leaf touching its rim mid-fall. The bowl is the only object "
            "in focus, its clay body coarse and imperfect. " + STYLE_TAIL
        ),
    },
]

report = []
for scene in SCENES:
    out_path = OUT_DIR / f"{scene['id']}.jpg"
    print(f"--- {scene['id']} -> {out_path.name}")
    result = selector.execute(
        {
            "prompt": scene["prompt"],
            "preferred_provider": "flux",
            "width": 1080,
            "height": 1920,
            "seed": scene["seed"],
            "output_path": str(out_path),
        }
    )
    entry = {
        "id": scene["id"],
        "success": result.success,
        "error": result.error,
        "selected_tool": (result.data or {}).get("selected_tool") if result.data else None,
        "selected_provider": (result.data or {}).get("selected_provider") if result.data else None,
        "path": str(out_path),
        "exists": out_path.exists(),
        "bytes": out_path.stat().st_size if out_path.exists() else 0,
    }
    report.append(entry)
    print("   ", json.dumps(entry, ensure_ascii=False))

(OUT_DIR / "sample_generation_report.json").write_text(
    json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8"
)
print("\nreport written:", OUT_DIR / "sample_generation_report.json")
print("estimated spend: 2 x $0.083 = ~$0.17")
