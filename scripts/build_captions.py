"""Build word-level caption timings from the ElevenLabs character timestamps.

ElevenLabs returns per-character start/end times. Captions need per-word times,
and the audio is slowed by atempo afterwards, so every time must be divided by the
tempo ratio to land correctly on the slowed audio.

Pipeline position:
  gen_narration_timed.py   -> <block>.mp3 + <block>.timestamps.json  (original speed)
  process_narration.py     -> slowed/<block>.mp3                     (atempo applied)
  build_captions.py        -> slowed/<block>.words.json              (THIS SCRIPT)
  build_composition.py     -> caption overlays timed from words.json

Usage:
    .venv\\Scripts\\python.exe scripts/build_captions.py [--tempo 0.83]
"""

from __future__ import annotations

import io
import json
import subprocess
import sys
from pathlib import Path

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")

ROOT = Path(__file__).resolve().parent.parent
SRC = ROOT / "projects" / "nha-su-va-bat-rong" / "assets" / "audio" / "final"
SLOWED = SRC / "slowed"

TEMPO = 0.83
if "--tempo" in sys.argv:
    TEMPO = float(sys.argv[sys.argv.index("--tempo") + 1])

BLOCKS = [
    "01_hook", "02_context", "03_development", "04_twist",
    "05_lesson", "06_reflection", "07_cta",
]

MAX_CHARS_PER_LINE = 30
MAX_LINES = 2


def duration_of(path: Path) -> float:
    out = subprocess.run(
        ["ffprobe", "-v", "error", "-show_entries", "format=duration",
         "-of", "csv=p=0", str(path)],
        capture_output=True, text=True, timeout=30,
    )
    return float(out.stdout.strip())


def words_from_character_timestamps(entries: list[dict], tempo: float) -> list[dict]:
    """Group character-level timings into words and scale them to the slowed audio.

    A character list can hold a whole sentence; words break on whitespace
    regardless of how the char arrays are chunked, so the arrays are flattened
    first and then regrouped.
    """
    chars: list[str] = []
    starts: list[float] = []
    ends: list[float] = []

    for entry in entries:
        entry_chars = entry.get("characters") or []
        entry_starts = entry.get("character_start_times_seconds") or []
        entry_ends = entry.get("character_end_times_seconds") or []
        for index, char in enumerate(entry_chars):
            chars.append(char)
            starts.append(entry_starts[index] if index < len(entry_starts) else starts[-1] if starts else 0.0)
            ends.append(entry_ends[index] if index < len(entry_ends) else (starts[-1] if starts else 0.0))

    words: list[dict] = []
    current_chars: list[str] = []
    current_start: float | None = None
    current_end: float | None = None

    def flush() -> None:
        nonlocal current_chars, current_start, current_end
        text = "".join(current_chars).strip()
        if text and current_start is not None and current_end is not None:
            words.append({
                "word": text,
                "start": round(current_start / tempo, 4),
                "end": round(current_end / tempo, 4),
            })
        current_chars, current_start, current_end = [], None, None

    for char, start, end in zip(chars, starts, ends):
        if char.isspace():
            flush()
            continue
        if current_start is None:
            current_start = start
        current_chars.append(char)
        current_end = end

    flush()
    return words


def group_cues(words: list[dict], max_chars: int, max_lines: int) -> list[dict]:
    """Group words into caption cues of at most max_lines lines."""
    cues: list[dict] = []
    current: list[dict] = []
    line_chars = 0
    line_count = 1

    for word in words:
        addition = len(word["word"]) + (1 if line_chars else 0)
        if line_chars + addition > max_chars:
            if line_count >= max_lines:
                cues.append({"words": current})
                current, line_chars, line_count = [], 0, 1
            else:
                line_count += 1
                line_chars = 0
                addition = len(word["word"])
        current.append(word)
        line_chars += addition

    if current:
        cues.append({"words": current})

    for cue in cues:
        cue["start"] = cue["words"][0]["start"]
        cue["end"] = cue["words"][-1]["end"]
    return cues


report = []
for block_id in BLOCKS:
    ts_path = SRC / f"{block_id}.timestamps.json"
    slowed_path = SLOWED / f"{block_id}.mp3"
    if not ts_path.exists():
        print(f"  MISSING timestamps: {ts_path}")
        continue

    entries = json.loads(ts_path.read_text(encoding="utf-8"))
    words = words_from_character_timestamps(entries, TEMPO)
    cues = group_cues(words, MAX_CHARS_PER_LINE, MAX_LINES)

    audio_seconds = duration_of(slowed_path) if slowed_path.exists() else None
    last_word_end = words[-1]["end"] if words else 0.0
    drift = (audio_seconds - last_word_end) if audio_seconds else None

    payload = {
        "block": block_id,
        "tempo": TEMPO,
        "audio_seconds": round(audio_seconds, 3) if audio_seconds else None,
        "word_count": len(words),
        "cue_count": len(cues),
        "last_word_end": last_word_end,
        "drift_seconds": round(drift, 3) if drift is not None else None,
        "words": words,
        "cues": cues,
    }
    (SLOWED / f"{block_id}.words.json").write_text(
        json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8"
    )

    entry = {
        "block": block_id,
        "words": len(words),
        "cues": len(cues),
        "audio_seconds": payload["audio_seconds"],
        "last_word_end": last_word_end,
        "drift_seconds": payload["drift_seconds"],
    }
    report.append(entry)
    print(f"  {block_id:<16} {len(words):>3} words -> {len(cues):>2} cues   "
          f"audio={payload['audio_seconds']}s  last_word={last_word_end}s  drift={payload['drift_seconds']}s")

print()
sample = json.loads((SLOWED / "01_hook.words.json").read_text(encoding="utf-8"))
print("sample cues for 01_hook:")
for cue in sample["cues"][:4]:
    text = " ".join(w["word"] for w in cue["words"])
    print(f"   {cue['start']:>6.2f} -> {cue['end']:>6.2f}  \"{text}\"")

total_cues = sum(r["cues"] for r in report)
print(f"\ntotal cues: {total_cues}")

(SLOWED / "captions_report.json").write_text(
    json.dumps({
        "tempo": TEMPO,
        "max_chars_per_line": MAX_CHARS_PER_LINE,
        "max_lines": MAX_LINES,
        "total_cues": total_cues,
        "blocks": report,
    }, ensure_ascii=False, indent=2),
    encoding="utf-8",
)
print("report:", SLOWED / "captions_report.json")
