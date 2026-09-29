"""Audit the final render's audio against the script, word by word.

Reported symptom: some sentences lose a few words at the end.

Method: pull the audio out of the rendered MP4, transcribe it with Whisper, and
diff the transcript against the intended script. Then do the same for the source
narration blocks to determine where the loss happens - at TTS generation, at the
atempo step, or in the composition.

Usage:
    .venv\\Scripts\\python.exe scripts/audit_audio.py
"""

from __future__ import annotations

import difflib
import io
import json
import re
import subprocess
import sys
import unicodedata
from pathlib import Path

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")

ROOT = Path(__file__).resolve().parent.parent
PROJ = ROOT / "projects" / "nha-su-va-bat-rong"
AUDIO = PROJ / "assets" / "audio"
SLOWED = AUDIO / "final" / "slowed"
RENDERS = PROJ / "renders"
WORK = RENDERS / "_audit"
WORK.mkdir(parents=True, exist_ok=True)

BLOCKS = [
    ("01_hook", "Bạn đang chờ đến khi nào thì mới thấy mình đủ? Một chiếc bát rỗng đã đi trước bạn ba năm."),
    ("02_context", "Ở một ngôi chùa cổ, có ba nhà sư cùng ấp ủ một giấc mơ: hành hương đến đất Phật. Sư cả nói: ta phải chuẩn bị cho thật đầy đủ. Sư nghèo chỉ có một chiếc bát."),
    ("03_development", "Mùa xuân, sư cả đóng gói. Mùa hạ, sư cả đợi thêm một người bạn đồng hành. Mùa thu, sư cả đợi con đường bớt mưa. Sư nghèo thì không đợi gì cả. Một buổi sáng, ông cầm chiếc bát, đi ra cổng chùa, và không quay lại."),
    ("04_twist", "Ba năm sau, sư nghèo trở về. Áo bạc màu, chân chai sạn, nhưng mắt sáng như người vừa nhìn thấy điều gì đó. Sư cả vẫn ở đó. Và trong kho, có bảy trăm chiếc bát, những thứ ông gom thêm, để dành cho chuyến đi."),
    ("05_lesson", "Đủ không phải là một con số. Đủ là một quyết định. Chiếc bát của sư nghèo rỗng không phải vì ông không có gì, mà vì ông đã chọn như vậy."),
    ("06_reflection", "Bạn cũng đang giữ một chiếc bát: một dự án, một lời xin lỗi, một chuyến đi. Nhưng cái bát không đưa bạn tới đâu cả. Chỉ có bước chân mới làm được điều đó."),
    ("07_cta", "Vậy, bạn còn chờ gì nữa? Bát rỗng rồi. Đi thôi."),
]


def norm(text: str) -> list[str]:
    text = unicodedata.normalize("NFC", text).lower()
    text = re.sub(r"[^\w\s]", " ", text, flags=re.UNICODE)
    return [w for w in text.split() if w]


def duration_of(path: Path) -> float:
    out = subprocess.run(
        ["ffprobe", "-v", "error", "-show_entries", "format=duration",
         "-of", "csv=p=0", str(path)],
        capture_output=True, text=True, timeout=30,
    )
    return float(out.stdout.strip())


print("=" * 70)
print("STEP 1 - per-block durations: original vs slowed vs cue coverage")
print("=" * 70)
print(f"  {'block':<16} {'orig':>7} {'slowed':>7} {'expect':>7} {'cue_end':>8} {'delta':>7}")
for block_id, text in BLOCKS:
    orig = duration_of(AUDIO / "final" / f"{block_id}.mp3")
    slow_path = SLOWED / f"{block_id}.mp3"
    slowed = duration_of(slow_path)
    expected = orig / 0.83
    cue_path = SLOWED / f"{block_id}.cues.json"
    cue_end = 0.0
    if cue_path.exists():
        cues = json.loads(cue_path.read_text(encoding="utf-8"))
        cue_end = max((c["end"] for c in cues["cues"]), default=0.0)
    print(f"  {block_id:<16} {orig:>7.2f} {slowed:>7.2f} {expected:>7.2f} "
          f"{cue_end:>8.2f} {cue_end - slowed:>7.2f}")

# Build one continuous audio track from the slowed blocks, in the same order and
# at the same spacing the composition uses.
print()
print("=" * 70)
print("STEP 2 - concatenate the slowed blocks and transcribe")
print("=" * 70)

concat = WORK / "_concat.txt"
lines = []
for block_id, _ in BLOCKS:
    lines.append(f"file '{(SLOWED / f'{block_id}.mp3').as_posix()}'")
concat.write_text("\n".join(lines), encoding="utf-8")

combined = WORK / "slowed_all.wav"
subprocess.run(
    ["ffmpeg", "-y", "-hide_banner", "-loglevel", "error",
     "-f", "concat", "-safe", "0", "-i", str(concat),
     "-ac", "1", "-ar", "16000", str(combined)],
    check=True,
)
print("  combined:", round(duration_of(combined), 2), "s")

from faster_whisper import WhisperModel  # noqa: E402

model = None
for size, compute in (("small", "int8"), ("base", "int8"), ("tiny", "int8")):
    try:
        model = WhisperModel(size, device="cpu", compute_type=compute, cpu_threads=4)
        print(f"  whisper: {size}/{compute}")
        break
    except Exception as exc:  # noqa: BLE001
        print(f"  whisper {size} failed: {type(exc).__name__}: {exc}")
if model is None:
    raise SystemExit("could not load a whisper model")

segments, info = model.transcribe(str(combined), language="vi", beam_size=5)
hypothesis = " ".join(s.text.strip() for s in segments)
print("  language:", info.language, round(info.language_probability, 3))

print()
print("=" * 70)
print("STEP 3 - word diff against the script")
print("=" * 70)

reference = " ".join(text for _, text in BLOCKS)
ref_words = norm(reference)
hyp_words = norm(hypothesis)

matcher = difflib.SequenceMatcher(None, ref_words, hyp_words)
matched = sum(b.size for b in matcher.get_matching_blocks())
print(f"  intended words : {len(ref_words)}")
print(f"  heard words    : {len(hyp_words)}")
print(f"  matched        : {matched}")
print(f"  approx WER     : {1 - matched / len(ref_words):.1%}")

print()
print("  --- every place the transcript diverges (script -> heard) ---")
problems = []
for tag, i1, i2, j1, j2 in matcher.get_opcodes():
    if tag == "equal":
        continue
    expected = " ".join(ref_words[i1:i2])
    heard = " ".join(hyp_words[j1:j2])
    context_before = " ".join(ref_words[max(0, i1 - 6):i1])
    problems.append({"tag": tag, "expected": expected, "heard": heard,
                     "before": context_before})
    print(f"    [{tag}] ...{context_before} <<{expected}>> -> heard: '{heard or '(nothing)'}'")

print()
print("  --- last words of each block, as heard ---")
cursor = 0
for block_id, text in BLOCKS:
    words = norm(text)
    block_ref = ref_words[cursor:cursor + len(words)]
    cursor += len(words)
    tail = block_ref[-5:]
    window = " ".join(hyp_words)
    tail_text = " ".join(tail)
    print(f"    {block_id:<16} script tail: '{tail_text}'  "
          f"present_in_audio={tail_text in window}")

report = {
    "combined_seconds": round(duration_of(combined), 2),
    "whisper_model": "small",
    "intended_words": len(ref_words),
    "heard_words": len(hyp_words),
    "matched_words": matched,
    "approx_wer": round(1 - matched / len(ref_words), 4),
    "transcript": hypothesis,
    "divergences": problems,
}
(WORK / "audio_audit.json").write_text(
    json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8"
)
print()
print("  report:", WORK / "audio_audit.json")
