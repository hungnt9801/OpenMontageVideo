"""Verify narration tail silence directly in the rendered file. No Whisper needed.

Complements verify_block_tails.py (which also transcribes). This one only measures
level, so it runs comfortably on a machine with little free RAM, and it is the part
that actually answers "does the sentence get cut off".

For every narration block it checks that the ~0.5s window after the block falls
quiet, and separately that the very end of the file decays instead of stopping
dead.

Usage:
    .venv\\Scripts\\python.exe scripts/verify_render_tails.py
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
FINAL = PROJ / "renders" / "final_captioned.mp4"
LAYOUT = ROOT / "hf" / "narration_layout.json"
OUT_DIR = PROJ / "artifacts" / "verification"
OUT_DIR.mkdir(parents=True, exist_ok=True)

QUIET_DB = -32.0
MIN_QUIET = 0.15


def duration_of(path: Path) -> float:
    out = subprocess.run(
        ["ffprobe", "-v", "error", "-show_entries", "format=duration",
         "-of", "csv=p=0", str(path)],
        capture_output=True, text=True, timeout=30,
    )
    return float(out.stdout.strip())


def windows(path: Path, start: float, length: float, window: float = 0.05) -> list[float]:
    proc = subprocess.run(
        ["ffmpeg", "-hide_banner", "-nostats", "-ss", f"{max(start,0):.3f}",
         "-t", f"{length:.3f}", "-i", str(path),
         "-af", f"astats=metadata=1:reset={int(window * 1000)},"
                "ametadata=print:key=lavfi.astats.Overall.RMS_level",
         "-f", "null", "-"],
        capture_output=True, text=True, errors="replace",
    )
    values = re.findall(r"RMS_level=(-?[\d.]+|inf)", proc.stderr)
    return [-120.0 if v == "inf" else float(v) for v in values]


schedule = json.loads(LAYOUT.read_text(encoding="utf-8"))
total = duration_of(FINAL)

print("=" * 76)
print("RENDERED FILE - NARRATION TAIL SILENCE")
print("=" * 76)
print(f"  file: {FINAL.name}   {total:.3f}s")
print()
print(f"  {'block':<16} {'starts':>7} {'ends':>7} {'gap':>7} {'quiet':>7}  verdict")

results = []
for entry in schedule:
    block = entry["block"]
    start = entry["start"]
    end = start + entry["duration"]
    gap = min(0.6, max(0.0, total - end))
    levels = windows(FINAL, end, gap) if gap > 0.05 else []

    quiet = 0.0
    for value in levels:
        if value < QUIET_DB:
            quiet += 0.05
        else:
            break

    ok = quiet >= MIN_QUIET
    results.append({
        "block": block,
        "start": start,
        "end": round(end, 3),
        "gap_measured_s": round(gap, 2),
        "quiet_after_s": round(quiet, 2),
        "tail_db": [round(v, 1) for v in levels],
        "pass": ok,
    })
    print(f"  {block:<16} {start:>7.2f} {end:>7.2f} {gap:>7.2f} {quiet:>6.2f}s  "
          f"{'PASS' if ok else 'FAIL'}")

# The composition ends with a reserved pad, so the file should also decay.
end_levels = windows(FINAL, total - 1.5, 1.5)
end_quiet = 0.0
for value in reversed(end_levels):
    if value < QUIET_DB:
        end_quiet += 0.05
    else:
        break

print()
print(f"  end of file: last 1.5s RMS dB = {' '.join(f'{v:6.1f}' for v in end_levels)}")
print(f"  quiet run at the very end: {end_quiet:.2f}s  "
      f"{'PASS' if end_quiet >= 0.3 else 'FAIL'}")

failures = [r for r in results if not r["pass"]]
if end_quiet < 0.3:
    failures.append({"block": "file_end", "pass": False})

print()
print("=" * 76)
print(f"  blocks with a proper tail: {len(results) - len([r for r in results if not r['pass']])}/{len(results)}")
print(f"  file ends in silence     : {'yes' if end_quiet >= 0.3 else 'no'}")
print(f"  VERDICT                  : {'PASS' if not failures else 'FAIL'}")

report = {
    "file": str(FINAL),
    "duration": round(total, 3),
    "quiet_threshold_db": QUIET_DB,
    "min_quiet_s": MIN_QUIET,
    "file_end_quiet_s": round(end_quiet, 2),
    "blocks": results,
    "passed": not failures,
}
(OUT_DIR / "render_tail_verification.json").write_text(
    json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8"
)
print()
print("  report:", OUT_DIR / "render_tail_verification.json")
raise SystemExit(1 if failures else 0)
