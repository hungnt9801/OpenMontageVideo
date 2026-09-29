"""Cut caption cues on punctuation, then snap the cuts onto real audio silences.

Long cues (a 60-character cue lasting 4.7s) violate the 2-4s on-screen rule in
skills/creative/short-form.md. Splitting on sentence punctuation is the obvious
fix, but the split time is only estimated from character timings.

To make the cut physically correct, ffmpeg's silencedetect finds the real silences
in each slowed block; any cue boundary that lands within a tolerance of a detected
silence is moved to that silence's midpoint. That is what makes a caption change
coincide with the voice actually pausing.

Reads:  final/slowed/<block>.words.json
Writes: final/slowed/<block>.cues.json
Usage:
    .venv\\Scripts\\python.exe scripts/build_cues.py
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
SLOWED = ROOT / "projects" / "nha-su-va-bat-rong" / "assets" / "audio" / "final" / "slowed"

BLOCKS = [
    "01_hook", "02_context", "03_development", "04_twist",
    "05_lesson", "06_reflection", "07_cta",
]

MAX_CHARS_PER_LINE = 30
MAX_LINES = 2
MAX_CUE_CHARS = MAX_CHARS_PER_LINE * MAX_LINES   # 60
MAX_CUE_SECONDS = 3.4
MIN_CUE_SECONDS = 0.6
SNAP_TOLERANCE = 0.45
SILENCE_NOISE_DB = -35
SILENCE_MIN_DURATION = 0.18

SENTENCE_END = re.compile(r"[.?!:]$")


def detect_silences(path: Path) -> list[tuple[float, float]]:
    """Return (start, end) silences detected in an audio file."""
    proc = subprocess.run(
        ["ffmpeg", "-hide_banner", "-nostats", "-i", str(path),
         "-af", f"silencedetect=noise={SILENCE_NOISE_DB}dB:d={SILENCE_MIN_DURATION}",
         "-f", "null", "-"],
        capture_output=True, text=True, errors="replace",
    )
    starts = [float(x) for x in re.findall(r"silence_start:\s*([-\d.]+)", proc.stderr)]
    ends = [float(x) for x in re.findall(r"silence_end:\s*([-\d.]+)", proc.stderr)]
    return list(zip(starts, ends))


def split_words_into_cues(words: list[dict]) -> list[dict]:
    """Group words into cues of at most MAX_LINES lines, then merge orphan cues.

    A sentence-ending word can leave a one-word fragment ("nam.", "mua.") that
    would flash on screen for a few tenths of a second. Any cue shorter than
    MIN_CUE_SECONDS is merged back into its predecessor even if that pushes the
    predecessor slightly over the line budget.
    """
    groups: list[list[dict]] = []
    current: list[dict] = []
    chars = 0

    def flush() -> None:
        nonlocal current, chars
        if current:
            groups.append(current)
        current, chars = [], 0

    for word in words:
        addition = len(word["word"]) + (1 if chars else 0)
        projected_seconds = (word["end"] - current[0]["start"]) if current else 0.0

        over_chars = chars + addition > MAX_CUE_CHARS
        over_time = projected_seconds > MAX_CUE_SECONDS
        sentence_done = bool(current) and SENTENCE_END.search(current[-1]["word"])

        if current and (over_chars or over_time or sentence_done):
            flush()

        current.append(word)
        chars += addition

    flush()

    # Merge fragments that would appear for less than MIN_CUE_SECONDS.
    merged: list[list[dict]] = []
    for group in groups:
        span = group[-1]["end"] - group[0]["start"]
        if merged and span < MIN_CUE_SECONDS:
            merged[-1].extend(group)
        else:
            merged.append(group)
    return [{"words": group} for group in merged]


def snap_to_silence(cue_boundary: float, silences: list[tuple[float, float]]) -> float:
    """Move a boundary onto a nearby detected silence midpoint."""
    for start, end in silences:
        midpoint = (start + end) / 2
        if abs(midpoint - cue_boundary) <= SNAP_TOLERANCE:
            return midpoint
    return cue_boundary


report = []
for block_id in BLOCKS:
    words_path = SLOWED / f"{block_id}.words.json"
    audio_path = SLOWED / f"{block_id}.mp3"
    if not words_path.exists():
        print(f"  MISSING {words_path}")
        continue

    payload = json.loads(words_path.read_text(encoding="utf-8"))
    words = payload["words"]
    silences = detect_silences(audio_path) if audio_path.exists() else []

    cues = split_words_into_cues(words)
    for index, cue in enumerate(cues):
        cue["start"] = cue["words"][0]["start"]
        cue["end"] = cue["words"][-1]["end"]
        cue["lines"] = []
        line: list[dict] = []
        line_chars = 0
        for word in cue["words"]:
            addition = len(word["word"]) + (1 if line_chars else 0)
            if line_chars + addition > MAX_CHARS_PER_LINE and line:
                cue["lines"].append(line)
                line, line_chars = [], 0
                addition = len(word["word"])
            line.append(word)
            line_chars += addition
        if line:
            cue["lines"].append(line)

    snapped = 0
    for index in range(len(cues) - 1):
        boundary = cues[index]["end"]
        target = snap_to_silence(boundary, silences)
        if target != boundary:
            cues[index]["end"] = round(target - 0.02, 4)
            cues[index + 1]["start"] = round(target + 0.02, 4)
            snapped += 1

    out = {
        "block": block_id,
        "audio_seconds": payload.get("audio_seconds"),
        "tempo": payload.get("tempo"),
        "silences": [[round(s, 3), round(e, 3)] for s, e in silences],
        "cue_count": len(cues),
        "snapped_boundaries": snapped,
        "cues": cues,
    }
    (SLOWED / f"{block_id}.cues.json").write_text(
        json.dumps(out, ensure_ascii=False, indent=2), encoding="utf-8"
    )

    durations = [round(c["end"] - c["start"], 2) for c in cues]
    entry = {
        "block": block_id,
        "cues": len(cues),
        "silences_found": len(silences),
        "snapped": snapped,
        "cue_seconds": durations,
    }
    report.append(entry)
    print(f"  {block_id:<16} {len(cues):>2} cues  {len(silences):>2} silences  snapped={snapped}  "
          f"durations={durations}")

print("\n--- every cue, all blocks ---")
for block_id in BLOCKS:
    path = SLOWED / f"{block_id}.cues.json"
    if not path.exists():
        continue
    data = json.loads(path.read_text(encoding="utf-8"))
    for cue in data["cues"]:
        text = " ".join(w["word"] for w in cue["words"])
        dur = cue["end"] - cue["start"]
        flag = "  <-- long" if dur > 4.0 else ""
        print(f"   {block_id}  {cue['start']:>6.2f}-{cue['end']:>6.2f} ({dur:>4.2f}s)  {text}{flag}")

total = sum(r["cues"] for r in report)
long_cues = sum(1 for r in report for d in r["cue_seconds"] if d > 4.0)
print(f"\ntotal cues: {total}   cues over 4s: {long_cues}")

(SLOWED / "cues_report.json").write_text(
    json.dumps({
        "max_chars_per_line": MAX_CHARS_PER_LINE,
        "max_lines": MAX_LINES,
        "max_cue_seconds": MAX_CUE_SECONDS,
        "snap_tolerance": SNAP_TOLERANCE,
        "total_cues": total,
        "cues_over_4s": long_cues,
        "blocks": report,
    }, ensure_ascii=False, indent=2),
    encoding="utf-8",
)
print("report:", SLOWED / "cues_report.json")
