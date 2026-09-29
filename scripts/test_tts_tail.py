"""Test the real cause: is ElevenLabs trimming the tail on a frame grid?

Observation: every block's last character end-time is an exact multiple of 0.04s
(6.080, 11.120, 16.640, 14.640, 9.040, 9.360, 3.280) and the file is that value
plus about 0.035s. 0.04s is the frame period at 25 fps. That pattern is what a
server-side trim to the last frame boundary looks like, which would clip the decay
of the final phoneme and make the closing word sound cut off.

This script tests three candidate fixes on the SAME line, all cheap:

  A. baseline - exactly what the pipeline sends today
  B. text + trailing period - gives the generator a beat to cut on
  C. text + a short trailing neutral token, so the trimmed audio is not the word
     we care about

It reports, for each: the last character end-time, the file duration, the room
after the last character, and whether the tail decays into silence.

Usage:
    .venv\\Scripts\\python.exe scripts/test_tts_tail.py
"""

from __future__ import annotations

import io
import json
import os
import re
import subprocess
import sys
import time
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
tool = registry.get("fal_elevenlabs_tts")

WORK = ROOT / "projects" / "nha-su-va-bat-rong" / "renders" / "_audit" / "tails"
WORK.mkdir(parents=True, exist_ok=True)

BASE_TEXT = "Bạn đang chờ đến khi nào thì mới thấy mình đủ?"

VARIANTS = [
    ("A_baseline", BASE_TEXT),
    ("B_period", BASE_TEXT + "."),
    ("C_padded_phrase", BASE_TEXT + " Hãy nghĩ về điều đó."),
]

SETTINGS = {"stability": 0.75, "similarity_boost": 0.9, "style": 0.1, "speed": 0.92}


def duration_of(path: Path) -> float:
    out = subprocess.run(
        ["ffprobe", "-v", "error", "-show_entries", "format=duration",
         "-of", "csv=p=0", str(path)],
        capture_output=True, text=True, timeout=30,
    )
    return float(out.stdout.strip())


def tail_profile(path: Path, seconds: float = 0.6, window: float = 0.05) -> list[float]:
    total = duration_of(path)
    start = max(0.0, total - seconds)
    proc = subprocess.run(
        ["ffmpeg", "-hide_banner", "-nostats", "-ss", f"{start:.3f}",
         "-t", f"{seconds:.3f}", "-i", str(path),
         "-af", f"astats=metadata=1:reset={int(window * 1000)},"
                "ametadata=print:key=lavfi.astats.Overall.RMS_level",
         "-f", "null", "-"],
        capture_output=True, text=True, errors="replace",
    )
    values = re.findall(r"RMS_level=(-?[\d.]+|inf)", proc.stderr)
    return [-120.0 if v == "inf" else float(v) for v in values]


print("=" * 78)
print("FRAME-GRID CHECK on existing files")
print("=" * 78)
print("  last-character end times from the current pipeline:")
for block_id in ["01_hook", "02_context", "03_development", "04_twist",
                 "05_lesson", "06_reflection", "07_cta"]:
    path = ROOT / "projects" / "nha-su-va-bat-rong" / "assets" / "audio" / "final" / f"{block_id}.timestamps.json"
    if not path.exists():
        continue
    entries = json.loads(path.read_text(encoding="utf-8"))
    last = 0.0
    for entry in entries:
        ends = entry.get("character_end_times_seconds") or []
        if ends:
            last = max(last, max(ends))
    frames25 = round(last / 0.04, 4)
    print(f"    {block_id:<16} {last:>8.3f}s   /0.04 = {frames25:>9.4f}   "
          f"{'EXACT frame multiple' if abs(frames25 - round(frames25)) < 1e-6 else 'not on grid'}")

print()
print("=" * 78)
print("LIVE TEST - three variants of the same line")
print("=" * 78)

results = []
for name, text in VARIANTS:
    out_path = WORK / f"{name}.mp3"
    print(f"\n--- {name}: {text!r}")
    result = tool.execute({
        "text": text,
        "voice": "Adam",
        "model_id": "eleven-v3",
        "language_code": "vi",
        "output_format": "mp3_44100_192",
        "timestamps": True,
        "output_path": str(out_path),
        **SETTINGS,
    })
    if not (result.success and out_path.exists()):
        print("    failed:", result.error)
        continue

    stamps = (result.data or {}).get("timestamps") or []
    last = 0.0
    for entry in stamps:
        ends = entry.get("character_end_times_seconds") or []
        if ends:
            last = max(last, max(ends))

    duration = duration_of(out_path)
    room = duration - last
    profile = tail_profile(out_path)
    frames = round(last / 0.04, 4)

    entry = {
        "variant": name,
        "text": text,
        "last_char_end": round(last, 4),
        "duration": round(duration, 4),
        "room_after_last_char": round(room, 4),
        "last_char_on_frame_grid": abs(frames - round(frames)) < 1e-6,
        "tail_rms_db": [round(v, 1) for v in profile],
        "tail_last_db": round(profile[-1], 1) if profile else None,
    }
    results.append(entry)
    print(f"    last char end : {last:.4f}s  (frame multiple: {entry['last_char_on_frame_grid']})")
    print(f"    file duration : {duration:.4f}s")
    print(f"    room after    : {room:.4f}s")
    print(f"    tail RMS dB   : {' '.join(f'{v:6.1f}' for v in profile)}")

print()
print("=" * 78)
print("CONCLUSION")
print("=" * 78)
for entry in results:
    print(f"  {entry['variant']:<18} room_after={entry['room_after_last_char']:>6.4f}s  "
          f"on_grid={entry['last_char_on_frame_grid']}  tail_end={entry['tail_last_db']}dB")

(WORK / "tail_test.json").write_text(
    json.dumps(results, ensure_ascii=False, indent=2), encoding="utf-8"
)
print()
print("  report:", WORK / "tail_test.json")
