"""Add trailing silence to narration blocks so the final word is not clipped.

Diagnosis (scripts/audit_tails.py + scripts/diagnose_truncation.py):
every block ends 26-51 ms after the last character's end-time, with 0.0-0.15 s of
trailing silence and a final window still at -15 to -19 dBFS. The generator is not
losing audio - the file simply stops the instant the last phoneme is emitted, so
the closing consonant and tone of the final word have no room to resolve and sound
cut off.

Fix: pad each block with real silence in the original TTS file, BEFORE the atempo
step, so the slowed copy inherits the same tail.

  final/<block>.mp3            ->  final/padded/<block>.mp3   (+PAD seconds)
  then process_narration.py re-slows from padded/

Usage:
    .venv\\Scripts\\python.exe scripts/pad_narration.py [--pad 0.5]
"""

from __future__ import annotations

import io
import json
import re
import subprocess
import sys
from pathlib import Path

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")

ROOT = Path(__file__).resolve().parent.parent
PROJ = ROOT / "projects" / "nha-su-va-bat-rong"
SRC = PROJ / "assets" / "audio" / "final"
PADDED = SRC / "padded"
PADDED.mkdir(parents=True, exist_ok=True)

PAD = 0.5
if "--pad" in sys.argv:
    PAD = float(sys.argv[sys.argv.index("--pad") + 1])

BLOCKS = ["01_hook", "02_context", "03_development", "04_twist",
          "05_lesson", "06_reflection", "07_cta"]


def duration_of(path: Path) -> float:
    out = subprocess.run(
        ["ffprobe", "-v", "error", "-show_entries", "format=duration",
         "-of", "csv=p=0", str(path)],
        capture_output=True, text=True, timeout=30,
    )
    return float(out.stdout.strip())


def tail_profile(path: Path, seconds: float = 0.8, window: float = 0.10) -> list[float]:
    """RMS dBFS per window across the last `seconds`, most recent last."""
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


print("=" * 74)
print(f"ADDING {PAD:.2f}s OF TRAILING SILENCE (before the atempo step)")
print("=" * 74)

report = []
for block_id in BLOCKS:
    src = SRC / f"{block_id}.mp3"
    dst = PADDED / f"{block_id}.mp3"
    if not src.exists():
        print(f"  MISSING {src}")
        continue

    before = duration_of(src)
    # apad appends silence; -t pins the exact output length so ffmpeg stops cleanly.
    subprocess.run(
        ["ffmpeg", "-y", "-hide_banner", "-loglevel", "error", "-i", str(src),
         "-af", f"apad=pad_dur={PAD}",
         "-c:a", "libmp3lame", "-b:a", "192k", str(dst)],
        check=True,
    )
    after = duration_of(dst)
    profile = tail_profile(dst)
    last = profile[-1] if profile else -120.0

    entry = {
        "block": block_id,
        "before_s": round(before, 3),
        "after_s": round(after, 3),
        "added_s": round(after - before, 3),
        "tail_rms_db": [round(v, 1) for v in profile],
        "last_window_db": round(last, 1),
        "ends_in_silence": last < -45.0,
    }
    report.append(entry)

    status = "OK" if entry["ends_in_silence"] else "STILL LOUD"
    print(f"  {block_id:<16} {before:>6.2f}s -> {after:>6.2f}s (+{after-before:>4.2f})  "
          f"last={last:>6.1f}dB  {status}")

print()
print("  tail RMS dB (last 0.8s, oldest -> newest):")
for entry in report:
    print(f"    {entry['block']:<16} {' '.join(f'{v:6.1f}' for v in entry['tail_rms_db'])}")

bad = [e for e in report if not e["ends_in_silence"]]
print()
print("=" * 74)
print(f"  blocks now ending in silence: {len(report) - len(bad)}/{len(report)}")
if bad:
    print("  STILL ENDING LOUD:", ", ".join(e["block"] for e in bad))
else:
    print("  every block now resolves into real silence")

(SRC / "pad_report.json").write_text(
    json.dumps({"pad_seconds": PAD, "blocks": report}, ensure_ascii=False, indent=2),
    encoding="utf-8",
)
print()
print("  report:", SRC / "pad_report.json")
print()
print("  NEXT: point process_narration.py at padded/, re-slow, then rebuild captions")
