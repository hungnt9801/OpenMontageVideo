"""Verify the Piper Vietnamese narration by transcribing it back to text.

We cannot listen to the audio, so we round-trip it: Whisper transcribes the
generated narration, and we compare that against the script the TTS was given.
Piper emitted "Missing phoneme from id map" warnings, so this is the check that
decides whether vi_VN-vivos-x_low is usable or whether the voice must change.

Usage:
    .venv\\Scripts\\python.exe scripts/verify_narration.py
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
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

AUDIO_DIR = ROOT / "projects" / "nha-su-va-bat-rong" / "assets" / "audio"
COMBINED = AUDIO_DIR / "narration_full.wav"

BLOCKS = [
    ("01_hook", "Bạn đang chờ đến khi nào thì mới thấy mình đủ? Một chiếc bát rỗng đã đi trước bạn ba năm."),
    ("02_context", "Ở một ngôi chùa cổ, có ba nhà sư cùng ấp ủ một giấc mơ: hành hương đến đất Phật. Sư cả nói: ta phải chuẩn bị cho thật đầy đủ. Sư nghèo chỉ có một chiếc bát."),
    ("03_development", "Mùa xuân, sư cả đóng gói. Mùa hạ, sư cả đợi thêm một người bạn đồng hành. Mùa thu, sư cả đợi con đường bớt mưa. Sư nghèo thì không đợi gì cả. Một buổi sáng, ông cầm chiếc bát, đi ra cổng chùa, và không quay lại."),
    ("04_twist", "Ba năm sau, sư nghèo trở về. Áo bạc màu, chân chai sạn, nhưng mắt sáng như người vừa nhìn thấy điều gì đó. Sư cả vẫn ở đó. Và trong kho, có bảy trăm chiếc bát, những thứ ông gom thêm, để dành cho chuyến đi."),
    ("05_lesson", "Đủ không phải là một con số. Đủ là một quyết định. Chiếc bát của sư nghèo rỗng không phải vì ông không có gì, mà vì ông đã chọn như vậy."),
    ("06_reflection", "Bạn cũng đang giữ một chiếc bát: một dự án, một lời xin lỗi, một chuyến đi. Nhưng cái bát không đưa bạn tới đâu cả. Chỉ có bước chân mới làm được điều đó."),
    ("07_cta", "Vậy, bạn còn chờ gì nữa? Bát rỗng rồi. Đi thôi."),
]


def normalise(text: str) -> list[str]:
    """Lowercase, strip punctuation, collapse whitespace, split to words."""
    text = unicodedata.normalize("NFC", text).lower()
    text = re.sub(r"[^\w\s]", " ", text, flags=re.UNICODE)
    return [w for w in text.split() if w]


# 1) Concatenate the 7 blocks into one file for a single transcription pass.
concat_list = AUDIO_DIR / "_concat.txt"
lines = []
for block_id, _ in BLOCKS:
    path = AUDIO_DIR / f"{block_id}.wav"
    if not path.exists():
        print("MISSING:", path)
        raise SystemExit(1)
    lines.append(f"file '{path.as_posix()}'")
concat_list.write_text("\n".join(lines), encoding="utf-8")

subprocess.run(
    ["ffmpeg", "-y", "-hide_banner", "-loglevel", "error",
     "-f", "concat", "-safe", "0", "-i", str(concat_list),
     "-c", "copy", str(COMBINED)],
    check=True,
)
print("combined:", COMBINED, f"{COMBINED.stat().st_size} bytes")

# 2) Transcribe it back.
from faster_whisper import WhisperModel  # noqa: E402

MODEL_SIZE = "base"
if "--model" in sys.argv:
    MODEL_SIZE = sys.argv[sys.argv.index("--model") + 1]

print(f"\nloading whisper {MODEL_SIZE} (Vietnamese) with int8 on CPU")

model = None
last_error = None
for candidate, compute in ((MODEL_SIZE, "int8"), (MODEL_SIZE, "int8_float32"), ("tiny", "int8")):
    try:
        model = WhisperModel(candidate, device="cpu", compute_type=compute, cpu_threads=4)
        print(f"  loaded: {candidate} / {compute}")
        MODEL_SIZE = candidate
        break
    except Exception as exc:  # noqa: BLE001
        last_error = exc
        print(f"  failed: {candidate} / {compute} -> {type(exc).__name__}: {exc}")

if model is None:
    print("\nCould not load any whisper model (low free RAM). Last error:", last_error)
    raise SystemExit(2)

segments, info = model.transcribe(
    str(COMBINED),
    language="vi",
    beam_size=5,
    word_timestamps=False,
)
hypothesis = " ".join(seg.text.strip() for seg in segments)
print("detected language:", info.language, "prob:", round(info.language_probability, 3))
print("\n--- TRANSCRIPT BACK ---")
print(hypothesis)

# 3) Compare against the intended script.
reference = " ".join(text for _, text in BLOCKS)
ref_words = normalise(reference)
hyp_words = normalise(hypothesis)

matcher = difflib.SequenceMatcher(None, ref_words, hyp_words)
ratio = matcher.ratio()
matched = sum(block.size for block in matcher.get_matching_blocks())
wer = 1.0 - (matched / len(ref_words)) if ref_words else 1.0

print("\n--- SCORES ---")
print(f"intended words : {len(ref_words)}")
print(f"heard words    : {len(hyp_words)}")
print(f"matched words  : {matched}")
print(f"sequence ratio : {ratio:.3f}")
print(f"approx WER     : {wer:.1%}")

print("\n--- MISSING / WRONG WORDS (in script, not heard) ---")
misses = []
for tag, i1, i2, j1, j2 in matcher.get_opcodes():
    if tag in ("replace", "delete"):
        misses.append(" ".join(ref_words[i1:i2]))
print(" | ".join(misses[:25]) if misses else "(none)")

# 4) Check the phrases that matter most.
print("\n--- KEY PHRASE CHECK ---")
for phrase in ["chiếc bát", "nhà sư", "hành hương", "bảy trăm", "quyết định", "bát rỗng"]:
    print(f"  {phrase:<14} intended={phrase in reference.lower()}  heard={phrase in hypothesis.lower()}")

report = {
    "voice": "vi_VN-vivos-x_low",
    "transcript": hypothesis,
    "intended_words": len(ref_words),
    "heard_words": len(hyp_words),
    "matched_words": matched,
    "sequence_ratio": round(ratio, 4),
    "approx_wer": round(wer, 4),
    "missing_segments": misses,
}
(AUDIO_DIR / "narration_verification.json").write_text(
    json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8"
)
print("\nreport:", AUDIO_DIR / "narration_verification.json")
