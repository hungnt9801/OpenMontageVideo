"""Probe 2: can we get EXACTLY 1080x1920 (true 9:16 at delivery size)?

Findings so far:
  - flux_image @ 1080x1920  -> fal snapped it to portrait_4_3 = 1056x1440  (wrong)
  - seedream_image "portrait_16_9" -> 1152x2048 (correct ratio, larger than delivery)
  - image_selector drops aspect_ratio/resolution and ignores preferred_provider
    (bug at tools/graphics/image_selector.py:312), so it must be bypassed when the
    request needs a specific frame size.

This script tests seedream with an explicit custom image_size object.
Also grabs a Pexels stock still at the same ratio to price the $0 route.

Live, billable: 1 image (~$0.03) + 1 free Pexels call.

Usage:
    .venv\\Scripts\\python.exe scripts/probe_exact_size.py
"""

from __future__ import annotations

import io
import json
import subprocess
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

OUT = ROOT / "projects" / "nha-su-va-bat-rong" / "assets" / "probe"
OUT.mkdir(parents=True, exist_ok=True)

PROMPT = (
    "An ancient East-Asian Buddhist temple courtyard in late autumn, completely empty "
    "and deserted at golden hour, weathered grey stone paving covered with fallen yellow "
    "maple leaves, dark timber columns and a curved clay-tile roof edge framing the view, "
    "a bronze incense burner on the right releasing thick curling smoke. Photorealistic "
    "cinematic still, golden-hour side light with long shadows, volumetric sun shafts, "
    "shallow depth of field, 35mm film grain, vertical composition."
)


def dims(path: Path) -> str:
    try:
        out = subprocess.run(
            ["ffprobe", "-v", "error", "-select_streams", "v:0",
             "-show_entries", "stream=width,height", "-of", "csv=p=0", str(path)],
            capture_output=True, text=True, timeout=30,
        )
        return out.stdout.strip() or "?"
    except Exception as exc:  # noqa: BLE001
        return f"probe-failed:{exc}"


results = []

# --- D) seedream with an explicit custom size object -> true 1080x1920
seedream = registry.get("seedream_image")
d_path = OUT / "D_seedream_custom_1080x1920.jpg"
print("--- D: seedream_image image_size = {width:1080, height:1920}")
res = seedream.execute({
    "prompt": PROMPT,
    "image_size": {"width": 1080, "height": 1920},
    "num_images": 1,
    "output_path": str(d_path),
})
entry = {
    "label": "D-seedream-custom-1080x1920",
    "success": res.success,
    "error": res.error,
    "exists": d_path.exists(),
    "dimensions": dims(d_path) if d_path.exists() else None,
    "estimated_cost_usd": seedream.estimate_cost({"image_size": "portrait_16_9"}),
}
results.append(entry)
print("   ", json.dumps(entry, ensure_ascii=False))

# --- E) Pexels stock still at portrait orientation, $0
pexels = registry.get("pexels_image")
e_path = OUT / "E_pexels_stock_portrait.jpg"
print("\n--- E: pexels_image (free stock, portrait)")
res_e = pexels.execute({
    "query": "buddhist temple courtyard autumn leaves incense",
    "orientation": "portrait",
    "output_path": str(e_path),
})
entry_e = {
    "label": "E-pexels-stock-portrait",
    "success": res_e.success,
    "error": res_e.error,
    "exists": e_path.exists(),
    "dimensions": dims(e_path) if e_path.exists() else None,
    "estimated_cost_usd": 0.0,
}
results.append(entry_e)
print("   ", json.dumps(entry_e, ensure_ascii=False))

print("\n===== SUMMARY =====")
for entry in results:
    print(f"  {entry['label']:<32} {str(entry['dimensions']):<14} ok={entry['success']}")

(OUT / "exact_size_probe_report.json").write_text(
    json.dumps(results, ensure_ascii=False, indent=2), encoding="utf-8"
)
print("\nreport:", OUT / "exact_size_probe_report.json")
