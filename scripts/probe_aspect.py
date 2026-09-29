"""Probe which image route returns a true 9:16 frame (1080x1920).

The flux_image wrapper sends `image_size: {width, height}`; fal snapped that to
portrait_4_3 (1056x1440). This script tests alternative routes and reports the
real pixel dimensions each one returns.

Routes probed:
  A) seedream_image with enum image_size = "portrait_16_9"
  B) flux_image with portrait-ish custom dims that fal is more likely to honor
  C) image_selector routing to seedream (enum path through the selector)

Live, billable: ~3 images, roughly $0.10-0.25 total.

Usage:
    .venv\\Scripts\\python.exe scripts/probe_aspect.py
"""

from __future__ import annotations

import io
import json
import os
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


def run(label: str, tool_name: str, inputs: dict, out_name: str) -> None:
    tool = registry.get(tool_name)
    out_path = OUT / out_name
    print(f"\n--- {label}  (tool={tool_name})")
    result = tool.execute({**inputs, "output_path": str(out_path)})
    entry = {
        "label": label,
        "tool": tool_name,
        "success": result.success,
        "error": result.error,
        "path": str(out_path),
        "exists": out_path.exists(),
        "dimensions": dims(out_path) if out_path.exists() else None,
    }
    results.append(entry)
    print("   ", json.dumps(entry, ensure_ascii=False))


# A) Seedream with explicit portrait enum (1080x1920 at 2K tier).
run(
    "A-seedream-enum-16_9",
    "seedream_image",
    {"prompt": PROMPT, "image_size": "portrait_16_9", "num_images": 1},
    "A_seedream_16_9.jpg",
)

# B) FLUX with custom dims that fal is likelier to honor as portrait 9:16.
run(
    "B-flux-custom-9x16",
    "flux_image",
    {"prompt": PROMPT, "width": 1080, "height": 1920, "seed": 1101,
     "model": "flux-pro/v1.1"},
    "B_flux_9x16.jpg",
)

# C) Through the selector, asking for the ratio + a resolution tier.
selector = registry.get("image_selector")
out_path = OUT / "C_selector_seedream_16_9.jpg"
print("\n--- C-selector-aspect-ratio-hint  (tool=image_selector)")
res = selector.execute({
    "prompt": PROMPT,
    "preferred_provider": "seedream",
    "aspect_ratio": "9:16",
    "output_path": str(out_path),
})
entry = {
    "label": "C-selector-aspect-ratio-hint",
    "tool": "image_selector",
    "success": res.success,
    "error": res.error,
    "selected_tool": (res.data or {}).get("selected_tool") if res.data else None,
    "path": str(out_path),
    "exists": out_path.exists(),
    "dimensions": dims(out_path) if out_path.exists() else None,
}
results.append(entry)
print("   ", json.dumps(entry, ensure_ascii=False))

print("\n===== SUMMARY =====")
for entry in results:
    print(f"  {entry['label']:<32} {str(entry['dimensions']):<14} ok={entry['success']}")

(OUT / "aspect_probe_report.json").write_text(
    json.dumps(results, ensure_ascii=False, indent=2), encoding="utf-8"
)
print("\nreport:", OUT / "aspect_probe_report.json")
