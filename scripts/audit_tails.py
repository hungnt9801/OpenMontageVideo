"""Check whether any narration block is truncated at the end.

If words are cut off, the file ends while the voice is still speaking: the final
few hundred milliseconds carry speech-level energy and then stop dead, instead of
decaying into silence.

Method: measure RMS in 100ms windows across the last 1.5s of every block, in both
the original TTS output and the slowed version. A natural ending decays to near
silence; a truncation holds energy right up to the last window.

Also measures the amount of trailing silence, which should exist if nothing is cut.

Usage:
    .venv\\Scripts\\python.exe scripts/audit_tails.py
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
AUDIO = PROJ / "assets" / "audio"
SLOWED = AUDIO / "final" / "slowed"

BLOCKS = ["01_hook", "02_context", "03_development", "04_twist",
          "05_lesson", "06_reflection", "07_cta"]

WINDOW = 0.10          # seconds per measurement window
TAIL = 1.5             # how far back to look


def duration_of(path: Path) -> float:
    out = subprocess.run(
        ["ffprobe", "-v", "error", "-show_entries", "format=duration",
         "-of", "csv=p=0", str(path)],
        capture_output=True, text=True, timeout=30,
    )
    return float(out.stdout.strip())


def rms_windows(path: Path, start: float, length: float) -> list[float]:
    """Return RMS dBFS per window over [start, start+length]."""
    proc = subprocess.run(
        ["ffmpeg", "-hide_banner", "-nostats", "-ss", f"{start:.3f}",
         "-t", f"{length:.3f}", "-i", str(path),
         "-af", f"astats=metadata=1:reset={int(WINDOW * 1000)},"
                "ametadata=print:key=lavfi.astats.Overall.RMS_level",
         "-f", "null", "-"],
        capture_output=True, text=True, errors="replace",
    )
    values = re.findall(r"RMS_level=(-?[\d.]+|inf)", proc.stderr)
    out = []
    for value in values:
        out.append(-120.0 if value == "inf" else float(value))
    return out


def trailing_silence(path: Path, threshold_db: float = -45.0) -> float:
    """Seconds of silence at the end of the file."""
    total = duration_of(path)
    window = 0.05
    scanned = 0.0
    while scanned < 2.0 and scanned < total:
        start = total - scanned - window
        if start < 0:
            break
        levels = rms_windows(path, start, window)
        if not levels or levels[0] > threshold_db:
            break
        scanned += window
    return round(scanned, 2)


print("=" * 78)
print("TAIL ANALYSIS - is any block cut short?")
print("=" * 78)

report = []
for block_id in BLOCKS:
    for label, path in (("original", AUDIO / "final" / f"{block_id}.mp3"),
                        ("slowed  ", SLOWED / f"{block_id}.mp3")):
        if not path.exists():
            print(f"  MISSING {path}")
            continue
        total = duration_of(path)
        start = max(0.0, total - TAIL)
        levels = rms_windows(path, start, TAIL)
        tail_silence = trailing_silence(path)

        shown = " ".join(f"{v:6.1f}" for v in levels[-12:])
        last = levels[-1] if levels else -120.0
        peak_in_tail = max(levels) if levels else -120.0

        entry = {
            "block": block_id,
            "variant": label.strip(),
            "seconds": round(total, 3),
            "last_window_db": round(last, 1),
            "peak_in_tail_db": round(peak_in_tail, 1),
            "trailing_silence_s": tail_silence,
            "windows": [round(v, 1) for v in levels],
        }
        report.append(entry)

        verdict = ""
        if last > -30:
            verdict = "  <-- ENDS LOUD: possible truncation"
        print(f"  {block_id:<16} {label}  len={total:>6.2f}s  "
              f"tail_silence={tail_silence:>4.1f}s  last={last:>6.1f}dB{verdict}")
        print(f"      last {len(levels[-12:]) * WINDOW:.1f}s RMS dB: {shown}")

print()
print("=" * 78)
print("SUMMING UP")
print("=" * 78)
suspicious = [e for e in report if e["last_window_db"] > -30]
print(f"  blocks whose audio ends above -30 dBFS: {len(suspicious)}")
for entry in suspicious:
    print(f"    - {entry['block']} ({entry['variant']}): "
          f"last={entry['last_window_db']} dB, trailing silence={entry['trailing_silence_s']}s")

no_silence = [e for e in report if e["trailing_silence_s"] < 0.05]
print(f"  blocks with essentially no trailing silence: {len(no_silence)}")
for entry in no_silence:
    print(f"    - {entry['block']} ({entry['variant']})")

(Path(PROJ / "renders" / "_audit")).mkdir(parents=True, exist_ok=True)
(Path(PROJ / "renders" / "_audit" / "tail_analysis.json")).write_text(
    json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8"
)
print()
print("  report: projects/nha-su-va-bat-rong/renders/_audit/tail_analysis.json")
