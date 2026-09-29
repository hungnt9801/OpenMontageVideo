"""Stretch the ElevenLabs narration to a slower, meditation-appropriate pace.

The TTS `speed` parameter had no measurable effect (0.92 and 0.72 both produced
203 wpm), so pacing is corrected in post with ffmpeg's atempo filter, applied to
each block separately so block boundaries stay accurate.

atempo < 1 lengthens audio without changing pitch. Slowing by 1.20x lands the
narration near 170 wpm - still brisker than the brief's 135-150, but the scenes
that carry no narration let the piece breathe, and this avoids the "sludgy"
artefacts a heavier stretch introduces.

Usage:
    .venv\\Scripts\\python.exe scripts/process_narration.py [--tempo 0.83]
"""

from __future__ import annotations

import io
import json
import subprocess
import sys
from pathlib import Path

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")

ROOT = Path(__file__).resolve().parent.parent
FINAL = ROOT / "projects" / "nha-su-va-bat-rong" / "assets" / "audio" / "final"
# Prefer the padded source when it exists: ElevenLabs trims every generation on a
# 25 fps frame boundary, leaving only 26-51 ms after the last character, so the
# raw file ends the instant the final phoneme is emitted. pad_narration.py adds a
# real tail first; slowing from there keeps it. See scripts/audit_tails.py.
SRC = FINAL / "padded" if (FINAL / "padded").is_dir() else FINAL
DST = FINAL / "slowed"
DST.mkdir(parents=True, exist_ok=True)

print("narration source:", SRC)

TEMPO = 0.83
if "--tempo" in sys.argv:
    TEMPO = float(sys.argv[sys.argv.index("--tempo") + 1])

BLOCKS = [
    "01_hook",
    "02_context",
    "03_development",
    "04_twist",
    "05_lesson",
    "06_reflection",
    "07_cta",
]


def duration_of(path: Path) -> float:
    out = subprocess.run(
        ["ffprobe", "-v", "error", "-show_entries", "format=duration",
         "-of", "csv=p=0", str(path)],
        capture_output=True, text=True, timeout=30,
    )
    return float(out.stdout.strip())


print(f"tempo: {TEMPO}  (1/{1/TEMPO:.2f}x slower)")
print()

report = []
total_before = 0.0
total_after = 0.0
total_words = 0

for block_id in BLOCKS:
    src = SRC / f"{block_id}.mp3"
    dst = DST / f"{block_id}.mp3"
    if not src.exists():
        print(f"  MISSING {src}")
        continue

    before = duration_of(src)
    subprocess.run(
        ["ffmpeg", "-y", "-hide_banner", "-loglevel", "error",
         "-i", str(src), "-filter:a", f"atempo={TEMPO}",
         "-c:a", "libmp3lame", "-b:a", "192k", str(dst)],
        check=True,
    )
    after = duration_of(dst)

    words = {"01_hook": 21, "02_context": 38, "03_development": 48, "04_twist": 47,
             "05_lesson": 32, "06_reflection": 35, "07_cta": 11}[block_id]
    total_before += before
    total_after += after
    total_words += words

    entry = {
        "block": block_id,
        "seconds_before": round(before, 2),
        "seconds_after": round(after, 2),
        "wpm_after": round((words / after) * 60, 1),
    }
    report.append(entry)
    print(f"  {block_id:<16} {before:>6.2f}s -> {after:>6.2f}s   {entry['wpm_after']:>5.1f} wpm")

print()
print(f"TOTAL {total_before:.2f}s -> {total_after:.2f}s   "
      f"({(total_words / total_after) * 60:.1f} wpm)")
print(f"gaps available for breathing room in a 96s video: {96 - total_after:.2f}s")

(DST / "slowed_report.json").write_text(
    json.dumps({
        "tempo": TEMPO,
        "total_seconds_before": round(total_before, 2),
        "total_seconds_after": round(total_after, 2),
        "overall_wpm": round((total_words / total_after) * 60, 1),
        "blocks": report,
    }, ensure_ascii=False, indent=2),
    encoding="utf-8",
)
print("report:", DST / "slowed_report.json")
