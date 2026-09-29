"""Generate the 4-image SAMPLE for nha-su-va-bat-rong at exact 1080x1920.

Why these four:
  s01 courtyard  - no people, lowest risk, establishes the look
  s04 bowl       - the central symbol, ECU, no people
  s08 monk CU    - FIRST TEST of character consistency via a reference image
  s09 700 bowls  - the twist reveal, the most complex frame

Route: seedream_image called DIRECTLY (not via image_selector).
  - image_selector ignores preferred_provider and strips aspect_ratio/resolution
    (bug at tools/graphics/image_selector.py:312), so it cannot express "1080x1920".
  - seedream_image accepts image_size as a custom object -> exact 1080x1920.
  - KNOWN BUG: seedream_image.estimate_cost() raises TypeError on a dict
    image_size (tools/graphics/seedream_image.py:131) AFTER the image is already
    written to disk. We therefore tolerate that exception and verify the file.

Cost: 4 images x $0.03 = $0.12

Usage:
    .venv\\Scripts\\python.exe scripts/gen_sample_v2.py
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
seedream = registry.get("seedream_image")

OUT = ROOT / "projects" / "nha-su-va-bat-rong" / "assets" / "sample"
OUT.mkdir(parents=True, exist_ok=True)

SIZE = {"width": 1080, "height": 1920}
PRICE = 0.03

MONK = (
    "a Vietnamese Buddhist monk about 40 years old with a smooth shaved head, "
    "thin wire-frame glasses, a saffron-brown robe draped over one shoulder, "
    "bare feet and a calm relaxed posture"
)
ELDER = (
    "an elderly Vietnamese Buddhist monk about 60 years old with a smooth shaved head, "
    "a short silver beard and a dark earth-brown robe, turning a string of wooden "
    "prayer beads"
)

STYLE = (
    "Photorealistic cinematic film still, golden-hour side light with long shadows, "
    "volumetric sun shafts, drifting dust motes, thin ground mist, shallow depth of "
    "field, 35mm film grain and halation on highlights, warm palette of amber #F5C518, "
    "earth brown #8C5A2B and shadow brown #2B2118, vertical 9:16 framing, real skin "
    "pores and authentic fabric texture, grounded in reality."
)

SCENES = [
    {
        "id": "s01_courtyard",
        "seed": 1101,
        "prompt": (
            "An ancient East-Asian Buddhist temple courtyard in late autumn, completely "
            "empty and deserted at golden hour. Weathered grey stone paving is covered "
            "with fallen yellow maple leaves, dark timber columns and a curved clay-tile "
            "roof edge frame the view, and a bronze incense burner releases thick curling "
            "smoke. " + STYLE
        ),
    },
    {
        "id": "s04_bowl",
        "seed": 1104,
        "prompt": (
            "An extreme close-up of a single empty ceramic alms bowl with a cracked glaze, "
            "resting on wet grey stone paving in an ancient East-Asian temple courtyard, "
            "one yellow autumn leaf touching its rim mid-fall. The bowl is the only sharp "
            "object in frame, its clay body coarse and imperfect, worn by years of use. "
            + STYLE
        ),
    },
    {
        "id": "s08_monk_reference",
        "seed": 1108,
        "prompt": (
            "A medium close-up portrait of " + MONK + ", standing still in an ancient "
            "East-Asian temple courtyard in late autumn. His face fills the lower two "
            "thirds of the frame, lit from behind so a bright rim of light traces the edge "
            "of his shaved head and cheek while his face stays softly shadowed, fallen "
            "yellow leaves drifting past him out of focus. This is the character reference "
            "image: his face, glasses and robe must read clearly and consistently. "
            + STYLE
        ),
    },
    {
        "id": "s09_700_bowls",
        "seed": 1109,
        "prompt": (
            "A wide interior of a dim temple storage room lined with dark wooden shelves "
            "holding hundreds of identical empty ceramic alms bowls, receding into shadow. "
            "A single shaft of late sunlight falls across the shelves from a high window, "
            "illuminating only the nearest bowls while the rest fade into darkness. Dust "
            "drifts in the light beam. No people. " + STYLE
        ),
    },
]


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


report = []
for scene in SCENES:
    out_path = OUT / f"{scene['id']}.jpg"
    if out_path.exists():
        out_path.unlink()
    print(f"--- {scene['id']}  (seed {scene['seed']})")
    error = None
    try:
        result = seedream.execute({
            "prompt": scene["prompt"],
            "image_size": SIZE,
            "num_images": 1,
            "output_format": "jpeg",
            "output_path": str(out_path),
        })
        if not result.success:
            error = result.error
    except TypeError as exc:
        # Known bug: estimate_cost() crashes on a dict image_size AFTER the image
        # has already been written. Treat a written file as success.
        error = f"estimate_cost bug (image still written): {exc}"
    except Exception as exc:  # noqa: BLE001
        error = f"{type(exc).__name__}: {exc}"

    entry = {
        "id": scene["id"],
        "seed": scene["seed"],
        "path": str(out_path),
        "exists": out_path.exists(),
        "dimensions": dims(out_path) if out_path.exists() else None,
        "bytes": out_path.stat().st_size if out_path.exists() else 0,
        "note": error,
    }
    report.append(entry)
    print("   ", json.dumps(entry, ensure_ascii=False))

ok = [r for r in report if r["exists"]]
print(f"\n{len(ok)}/{len(report)} images written at exact size")
print(f"estimated spend: {len(report)} x ${PRICE} = ${len(report) * PRICE:.2f}")

(OUT / "sample_report_v2.json").write_text(
    json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8"
)
print("report:", OUT / "sample_report_v2.json")
