"""Generate the meditation ambient music bed with ElevenLabs Music via fal.

pixabay_music (the only zero-cost route) returns HTTP 403, so the bed is
generated instead. The prompt is written to the brief in
proposal_packet.music_source.mood_direction: sparse piano, bamboo flute,
singing bowl, 60-75 BPM, no percussion, and no melodic "advertising" shape.

ElevenLabs Music exposes force_instrumental and a target length, so the track is
generated at the full video length.

Usage:
    .venv\\Scripts\\python.exe scripts/gen_music.py
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
tool = registry.get("fal_elevenlabs_music")
info = tool.get_info()
print("tool:", tool.name, "status:", info.get("status"))
print("inputs:", list(((info.get("input_schema") or {}).get("properties") or {}).keys()))

OUT = ROOT / "projects" / "nha-su-va-bat-rong" / "assets" / "music"
OUT.mkdir(parents=True, exist_ok=True)

PROMPT = (
    "Meditation ambient for a slow Buddhist story video. Sparse solo piano playing "
    "single notes with long silences between them, a distant bamboo flute, and a "
    "singing bowl struck occasionally. A warm low drone underneath. Very slow, "
    "around 65 BPM, no percussion, no drums, no beat. Calm, spacious, contemplative, "
    "restrained. Instrumental only, no vocals. It should feel like an empty temple "
    "courtyard in late autumn, not like advertising music."
)

out_path = OUT / "bed_elevenlabs.mp3"

inputs = {
    "prompt": PROMPT,
    "duration_seconds": 105,   # 105s so the edit has headroom past 96s
    "force_instrumental": True,
    "output_path": str(out_path),
}

print("\ngenerating...")
result = tool.execute(inputs)
print("success:", result.success)
print("error  :", result.error)
if result.data:
    print("data   :", json.dumps(result.data, ensure_ascii=False)[:900])
print("file   :", out_path.exists(), out_path.stat().st_size if out_path.exists() else 0, "bytes")

if out_path.exists():
    probe = subprocess.run(
        ["ffprobe", "-v", "error", "-show_entries", "format=duration,bit_rate",
         "-of", "json", str(out_path)],
        capture_output=True, text=True, timeout=30,
    )
    print("probe  :", probe.stdout.strip())

(OUT / "music_report.json").write_text(
    json.dumps({
        "provider": "fal_elevenlabs_music",
        "prompt": PROMPT,
        "music_length_ms": inputs["duration_seconds"],
        "success": result.success,
        "error": result.error,
        "path": str(out_path),
        "bytes": out_path.stat().st_size if out_path.exists() else 0,
    }, ensure_ascii=False, indent=2),
    encoding="utf-8",
)
print("report:", OUT / "music_report.json")
