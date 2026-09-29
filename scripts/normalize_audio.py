"""Normalise the rendered master to -14 LUFS / -1 dBTP without re-encoding video.

The render measured -15.6 LUFS integrated with a -2.0 dBTP true peak; the brief
asks for -14 LUFS and -1 dBTP. Only the audio is re-encoded (loudnorm), then
remuxed against the original H.264 stream so the 96s of video is untouched.

Usage:
    .venv\\Scripts\\python.exe scripts/normalize_audio.py
"""

from __future__ import annotations

import io
import json
import re
import shutil
import subprocess
import sys
from pathlib import Path

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")

ROOT = Path(__file__).resolve().parent.parent
RENDERS = ROOT / "projects" / "nha-su-va-bat-rong" / "renders"

# Input/output are overridable so this can normalise whatever render_only.py just
# produced, instead of assuming a fixed filename.
if "--input" in sys.argv:
    SRC = Path(sys.argv[sys.argv.index("--input") + 1])
else:
    SRC = RENDERS / "final_v2.mp4"
if "--out" in sys.argv:
    OUT = Path(sys.argv[sys.argv.index("--out") + 1])
else:
    OUT = RENDERS / "final_captioned.mp4"

AUDIO = RENDERS / "_audio_raw.wav"
AUDIO_NORM = RENDERS / "_audio_norm.wav"

TARGET_I = -14.0
TARGET_TP = -1.0
TARGET_LRA = 11.0


def measure(path: Path) -> dict:
    proc = subprocess.run(
        ["ffmpeg", "-hide_banner", "-nostats", "-i", str(path),
         "-filter_complex", "ebur128=peak=true", "-f", "null", "-"],
        capture_output=True, text=True, errors="replace",
    )
    text = proc.stderr
    integrated = re.findall(r"I:\s*(-?\d+\.\d+)\s*LUFS", text)
    peak = re.findall(r"Peak:\s*(-?\d+\.\d+)\s*dBFS", text)
    lra = re.findall(r"LRA:\s*(-?\d+\.\d+)\s*LU", text)
    return {
        "integrated_lufs": float(integrated[-1]) if integrated else None,
        "true_peak_dbfs": float(peak[-1]) if peak else None,
        "lra_lu": float(lra[-1]) if lra else None,
    }


print("=== BEFORE ===")
before = measure(SRC)
print(" ", json.dumps(before))

# 1) pull the audio out untouched
subprocess.run(
    ["ffmpeg", "-y", "-hide_banner", "-loglevel", "error", "-i", str(SRC),
     "-vn", "-acodec", "pcm_s16le", "-ar", "48000", str(AUDIO)],
    check=True,
)

# 2) normalise with loudnorm, both passes in one call (dynamic mode, then linear)
pass1 = subprocess.run(
    ["ffmpeg", "-hide_banner", "-nostats", "-i", str(AUDIO),
     "-af", f"loudnorm=I={TARGET_I}:TP={TARGET_TP}:LRA={TARGET_LRA}:print_format=json",
     "-f", "null", "-"],
    capture_output=True, text=True, errors="replace",
)
match = re.search(r"\{[^{}]*input_i[^{}]*\}", pass1.stderr, re.DOTALL)
if not match:
    print("could not parse loudnorm pass 1; falling back to a single dynamic pass")
    measured = None
else:
    measured = json.loads(match.group(0))
    print("\n=== loudnorm pass 1 measurement ===")
    print(" ", json.dumps({k: measured.get(k) for k in
                           ("input_i", "input_tp", "input_lra", "input_thresh",
                            "target_offset")}))

if measured:
    af = (
        f"loudnorm=I={TARGET_I}:TP={TARGET_TP}:LRA={TARGET_LRA}"
        f":measured_I={measured['input_i']}:measured_TP={measured['input_tp']}"
        f":measured_LRA={measured['input_lra']}:measured_thresh={measured['input_thresh']}"
        f":offset={measured['target_offset']}:linear=true:print_format=summary"
    )
else:
    af = f"loudnorm=I={TARGET_I}:TP={TARGET_TP}:LRA={TARGET_LRA}"

subprocess.run(
    ["ffmpeg", "-y", "-hide_banner", "-loglevel", "error", "-i", str(AUDIO),
     "-af", af, "-acodec", "pcm_s16le", "-ar", "48000", str(AUDIO_NORM)],
    check=True,
)

# 3) remux: copy the video stream, take the normalised audio
subprocess.run(
    ["ffmpeg", "-y", "-hide_banner", "-loglevel", "error",
     "-i", str(SRC), "-i", str(AUDIO_NORM),
     "-map", "0:v:0", "-map", "1:a:0",
     "-c:v", "copy", "-c:a", "aac", "-b:a", "192k",
     "-movflags", "+faststart", "-shortest", str(OUT)],
    check=True,
)

print("\n=== AFTER ===")
after = measure(OUT)
print(" ", json.dumps(after))

print("\n=== files ===")
for path in (SRC, OUT):
    size = path.stat().st_size / (1024 * 1024)
    print(f"  {path.name:<16} {size:>7.1f} MB")

report = {
    "source": str(SRC),
    "output": str(OUT),
    "target": {"integrated_lufs": TARGET_I, "true_peak_dbfs": TARGET_TP, "lra_lu": TARGET_LRA},
    "before": before,
    "after": after,
    "loudnorm_pass1": measured,
}
(RENDERS / "loudness_report.json").write_text(
    json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8"
)
print("\nreport:", RENDERS / "loudness_report.json")

for tmp in (AUDIO, AUDIO_NORM):
    if tmp.exists():
        tmp.unlink()
