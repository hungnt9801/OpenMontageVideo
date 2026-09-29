"""Quality gate: assert no narration block ends on a hard cut.

Checks every slowed block for:
  - trailing silence: the audio must decay below a threshold at the very end, so
    the closing word resolves instead of being chopped;
  - enough room after the last caption word, so a cue never runs to the file edge.

Run before building the composition. Exit code 1 means the audio needs padding.

Usage:
    .venv\\Scripts\\python.exe scripts/check_audio_tails.py
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
SLOWED = (ROOT / "projects" / "nha-su-va-bat-rong" / "assets" / "audio"
          / "final" / "slowed")

BLOCKS = ["01_hook", "02_context", "03_development", "04_twist",
          "05_lesson", "06_reflection", "07_cta"]

MIN_TAIL_SILENCE = 0.20        # seconds that must fall below the threshold
TAIL_THRESHOLD_DB = -38.0      # dBFS considered "quiet enough"
MIN_ROOM_AFTER_CUE = 0.05      # seconds between last cue word and audio end


def duration_of(path: Path) -> float:
    out = subprocess.run(
        ["ffprobe", "-v", "error", "-show_entries", "format=duration",
         "-of", "csv=p=0", str(path)],
        capture_output=True, text=True, timeout=30,
    )
    return float(out.stdout.strip())


def tail_windows(path: Path, seconds: float = 0.6, window: float = 0.05) -> list[float]:
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
print("AUDIO TAIL GATE")
print("=" * 78)
print(f"  need >= {MIN_TAIL_SILENCE:.2f}s below {TAIL_THRESHOLD_DB:.0f} dBFS at the end")
print(f"  need >= {MIN_ROOM_AFTER_CUE:.2f}s between the last cue word and the file end")
print()

failures = []
rows = []

for block_id in BLOCKS:
    audio = SLOWED / f"{block_id}.mp3"
    if not audio.exists():
        failures.append(f"{block_id}: audio missing")
        continue

    total = duration_of(audio)
    profile = tail_windows(audio)

    quiet_run = 0.0
    for value in reversed(profile):
        if value < TAIL_THRESHOLD_DB:
            quiet_run += 0.05
        else:
            break

    cue_end = None
    cue_path = SLOWED / f"{block_id}.cues.json"
    if cue_path.exists():
        data = json.loads(cue_path.read_text(encoding="utf-8"))
        cue_end = max((c["end"] for c in data["cues"]), default=0.0)

    room = (total - cue_end) if cue_end is not None else None
    last_db = profile[-1] if profile else None

    ok_silence = quiet_run >= MIN_TAIL_SILENCE
    ok_room = room is None or room >= MIN_ROOM_AFTER_CUE
    ok = ok_silence and ok_room

    if not ok:
        reasons = []
        if not ok_silence:
            reasons.append(f"tail silence {quiet_run:.2f}s < {MIN_TAIL_SILENCE:.2f}s")
        if not ok_room:
            reasons.append(f"room after last cue {room:.3f}s < {MIN_ROOM_AFTER_CUE:.2f}s")
        failures.append(f"{block_id}: " + "; ".join(reasons))

    rows.append({
        "block": block_id,
        "seconds": round(total, 3),
        "tail_silence_s": round(quiet_run, 2),
        "last_window_db": round(last_db, 1) if last_db is not None else None,
        "cue_end": round(cue_end, 3) if cue_end is not None else None,
        "room_s": round(room, 3) if room is not None else None,
        "pass": ok,
    })

    status = "PASS" if ok else "FAIL"
    room_text = f"{room:>6.3f}" if room is not None else "   n/a"
    print(f"  {block_id:<16} tail_silence={quiet_run:>4.2f}s  last={last_db:>6.1f}dB  "
          f"room={room_text}s  {status}")

print()
print("=" * 78)
if failures:
    print(f"  GATE FAILED - {len(failures)} block(s) need attention:")
    for item in failures:
        print("    -", item)
    print()
    print("  fix: run scripts/pad_narration.py, then scripts/process_narration.py")
else:
    print(f"  GATE PASSED - all {len(rows)} blocks decay into silence with room to spare")

(SLOWED / "tail_gate.json").write_text(
    json.dumps({
        "min_tail_silence_s": MIN_TAIL_SILENCE,
        "tail_threshold_db": TAIL_THRESHOLD_DB,
        "min_room_after_cue_s": MIN_ROOM_AFTER_CUE,
        "passed": not failures,
        "failures": failures,
        "blocks": rows,
    }, ensure_ascii=False, indent=2),
    encoding="utf-8",
)
print()
print("  report:", SLOWED / "tail_gate.json")

raise SystemExit(1 if failures else 0)
