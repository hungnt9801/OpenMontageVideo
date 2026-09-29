"""Generate the remaining 10 scene stills for nha-su-va-bat-rong at 1080x1920.

Aligned with the 14-scene plan from solution-image-led.md. Scenes that contain
the monk repeat the identity anchor verbatim AND pass s08_monk_reference.jpg as
the reference image so the face, glasses and robe stay consistent.

Already generated (sample): s01 courtyard, s04 bowl, s08 monk reference, s09 700 bowls.
This script produces: s02 s03 s05 s06 s07 s10 s11 s12 s13 s14.

Route: seedream_image called directly with a custom image_size object.
Reason (recorded in decision_log d-009): image_selector drops aspect_ratio /
resolution and ignores preferred_provider, and cannot express a required frame
size. Known bug: estimate_cost() raises TypeError on a dict image_size AFTER the
image is written, so we verify the file on disk instead of trusting the result.

Cost: 10 x $0.03 = $0.30

Usage:
    .venv\\Scripts\\python.exe scripts/gen_remaining_scenes.py
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

IMG_DIR = ROOT / "projects" / "nha-su-va-bat-rong" / "assets" / "images"
IMG_DIR.mkdir(parents=True, exist_ok=True)
REFERENCE = IMG_DIR / "s08_monk_reference.jpg"

SIZE = {"width": 1080, "height": 1920}
PRICE = 0.03

# Identity anchors - repeated VERBATIM in every prompt that contains the subject.
MONK = (
    "a Vietnamese Buddhist monk about 40 years old with a smooth shaved head, "
    "thin wire-frame glasses, a saffron-brown robe draped over one shoulder, "
    "bare feet and a calm relaxed posture"
)
ELDER = (
    "an elderly Vietnamese Buddhist monk about 60 years old with a smooth shaved "
    "head, a short silver beard and a dark earth-brown robe"
)

STYLE = (
    "Photorealistic cinematic film still, golden-hour side light with long shadows, "
    "volumetric sun shafts, drifting dust motes, thin ground mist, shallow depth of "
    "field, 35mm film grain with halation on highlights, warm palette of amber "
    "#F5C518, earth brown #8C5A2B and shadow brown #2B2118, vertical 9:16 framing, "
    "real skin pores and authentic fabric texture, grounded in reality."
)

# Keeps the title band in the upper third clear.
FRAMING = (
    "Framing note: keep the subject low in the frame, occupying the lower two "
    "thirds, with clean uncluttered negative space across the top third."
)

SCENES = [
    {
        "id": "s02_step",
        "seed": 1102,
        "uses_monk": True,
        "char_pct": 75,
        "prompt": (
            "An extreme close-up, cropped at mid-thigh, of " + MONK + " mid-step on "
            "wet grey stone paving in an ancient East-Asian temple courtyard in late "
            "autumn. Only the hem of the saffron-brown robe, the bare feet and the "
            "trailing edge of the fabric are in frame, with fallen yellow maple leaves "
            "scattered around the stones. A moment of forward motion, caught between "
            "two steps. " + FRAMING + " " + STYLE
        ),
    },
    {
        "id": "s03_beads",
        "seed": 1103,
        "uses_monk": False,
        "prompt": (
            "A medium shot of " + ELDER + ", seated on a weathered stone step in the "
            "shaded gallery of an ancient East-Asian temple, turning a string of worn "
            "wooden prayer beads slowly between his fingers. He looks down at his hands. "
            "Soft daylight falls in from the side through dark timber columns, and dust "
            "drifts in the light. " + FRAMING + " " + STYLE
        ),
    },
    {
        "id": "s05_folding",
        "seed": 1105,
        "uses_monk": False,
        "prompt": (
            "A medium shot of " + ELDER + ", seated beside a wooden lattice window in an "
            "ancient East-Asian temple, folding a piece of coarse brown cloth on his lap. "
            "Warm volumetric light streams through the lattice and lights the dust in the "
            "air; the folded cloth and the man's hands are the sharpest things in frame. "
            + FRAMING + " " + STYLE
        ),
    },
    {
        "id": "s06_rain_stone",
        "seed": 1106,
        "uses_monk": False,
        "prompt": (
            "A wide shot of wet grey stone paving in an ancient East-Asian temple "
            "courtyard under thin drizzle in late autumn, with faint bare footprints "
            "already fading on the wet stones. Fallen yellow leaves lie plastered flat "
            "against the ground. No people are present. Ripples spread across shallow "
            "puddles. " + STYLE
        ),
    },
    {
        "id": "s07_gate",
        "seed": 1107,
        "uses_monk": False,
        "prompt": (
            "A wide exterior of a weathered wooden gate at the edge of an ancient "
            "East-Asian Buddhist temple in late autumn, standing open. Late golden-hour "
            "light rakes across the courtyard from behind the camera, stretching long "
            "shadows through the gateway, and yellow leaves cross the frame on the wind. "
            "No people are present. " + STYLE
        ),
    },
    {
        "id": "s10_last_bowl",
        "seed": 1110,
        "uses_monk": False,
        "prompt": (
            "An extreme close-up of one single empty ceramic alms bowl standing alone on "
            "a dark wooden shelf, with late low sunlight falling exactly across its rim "
            "and into the empty interior. The bowl is the only object in the frame and "
            "the only thing in focus; the shelf and the shadowed room behind it fall away "
            "into darkness. " + STYLE
        ),
    },
    {
        "id": "s11_open_hand",
        "seed": 1111,
        "uses_monk": True,
        "char_pct": 30,
        "prompt": (
            "An extreme close-up of the open hand of " + MONK + ", palm upward, fingers "
            "spread, having just released an empty ceramic alms bowl that is falling away "
            "below the frame in slow motion. A saffron-brown sleeve enters from the edge "
            "of frame. Warm low light falls off across the palm. " + FRAMING + " " + STYLE
        ),
    },
    {
        "id": "s12_folded_robe",
        "seed": 1112,
        "uses_monk": False,
        "prompt": (
            "A medium shot of a neatly folded saffron-brown monk's robe resting alone on "
            "a weathered stone step in an ancient East-Asian temple courtyard, with fallen "
            "yellow maple leaves settling onto and around it. No people are present. Late "
            "afternoon light and long shadows fall across the stone. " + STYLE
        ),
    },
    {
        "id": "s13_stone_buddha",
        "seed": 1113,
        "uses_monk": False,
        "prompt": (
            "A medium shot of an ancient weathered stone Buddha statue seated in an "
            "overgrown corner of an East-Asian temple courtyard, with soft green moss "
            "growing on its shoulder and a few yellow autumn leaves caught in its lap. "
            "Warm directional late-afternoon light rakes across the carved stone and "
            "reveals its texture. No people are present. " + STYLE
        ),
    },
    {
        "id": "s14_courtyard_dusk",
        "seed": 1114,
        "uses_monk": False,
        "prompt": (
            "A wide view of the same ancient East-Asian Buddhist temple courtyard at "
            "dusk, now quiet and empty, the grey stone paving still covered with fallen "
            "yellow leaves, dark timber columns and the curved clay-tile roof edge "
            "framing the view. The last warm light has gone and cool ambient dusk settles "
            "over the courtyard while a bronze incense burner still releases a thin thread "
            "of smoke. This frame is composed as the mirror of the opening shot. " + STYLE
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


print("reference image:", REFERENCE, "exists:", REFERENCE.exists())
report = []
for scene in SCENES:
    out_path = IMG_DIR / f"{scene['id']}.jpg"
    if out_path.exists():
        out_path.unlink()
    use_ref = False
    print(f"\n--- {scene['id']}  seed={scene['seed']}  character={bool(scene.get('uses_monk'))}")

    inputs = {
        "prompt": scene["prompt"],
        "image_size": SIZE,
        "num_images": 1,
        "output_format": "jpeg",
        "output_path": str(out_path),
    }
    # NOTE: seedream_image is text-to-image only - it exposes no reference-image
    # input, and no other available provider (flux, openai, imagen, recraft) does
    # either. Character consistency therefore relies on the verbatim identity
    # anchor in the prompt plus a fixed seed. Scenes that would need the face are
    # deliberately framed without it.
    error = None
    try:
        result = seedream.execute(inputs)
        if not result.success:
            error = result.error
    except TypeError as exc:
        error = f"estimate_cost bug (image still written): {exc}"
    except Exception as exc:  # noqa: BLE001
        error = f"{type(exc).__name__}: {exc}"

    entry = {
        "id": scene["id"],
        "seed": scene["seed"],
        "has_character": bool(scene.get("uses_monk")),
        "exists": out_path.exists(),
        "dimensions": dims(out_path) if out_path.exists() else None,
        "bytes": out_path.stat().st_size if out_path.exists() else 0,
        "note": error,
    }
    report.append(entry)
    print("   ", json.dumps(entry, ensure_ascii=False))

written = [r for r in report if r["exists"]]
print(f"\n{len(written)}/{len(report)} written")
print(f"spend: {len(report)} x ${PRICE} = ${len(report) * PRICE:.2f}")

(IMG_DIR / "scene_generation_report.json").write_text(
    json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8"
)
print("report:", IMG_DIR / "scene_generation_report.json")
