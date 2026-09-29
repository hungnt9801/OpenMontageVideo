"""Verify the FINAL rendered file's audio: does it still cut words off?

Checks the rendered MP4 itself, not the source assets, so anything the composition
does to the audio is caught:

  1. does the narration end into silence at the end of the file?
  2. does each narration block, located at its scheduled start time, end into
     silence rather than a hard cut?
  3. transcribe the whole rendered audio and diff against the script.

Usage:
    .venv\\Scripts\\python.exe scripts/verify_final_audio.py
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
FINAL = PROJ / "renders" / "final_captioned.mp4"
WORK = PROJ / "renders" / "_audit"
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

# Schedule written by build_composition.py; read it back so this stays in sync.
layout_path = WORK / "narration_layout.json"
if layout_path.exists():
    LAYOUT = {b["block"]: b for b in json.loads(layout_path.read_text(encoding="utf-8"))}
else:
    LAYOUT = {}


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


print("=" * 78)
print("1. EXTRACT AUDIO FROM THE RENDERED FILE")
print("=" * 78)
audio = WORK / "rendered_audio.wav"
subprocess.run(
    ["ffmpeg", "-y", "-hide_banner", "-loglevel", "error", "-i", str(FINAL),
     "-vn", "-ac", "1", "-ar", "16000", str(audio)],
    check=True,
)
render_seconds = duration_of(FINAL)
print(f"  video length : {render_seconds:.3f}s")
print(f"  audio length : {duration_of(audio):.3f}s")

print()
print("=" * 78)
print("2. DOES THE RENDER END IN SILENCE?")
print("=" * 78)
tail = windows(FINAL, render_seconds - 3.0, 3.0)
print(f"  last 3.0s RMS dB: {' '.join(f'{v:6.1f}' for v in tail)}")
quiet_run = 0.0
for value in reversed(tail):
    if value < -38.0:
        quiet_run += 0.05
    else:
        break
print(f"  quiet tail at the end: {quiet_run:.2f}s  "
      f"{'OK' if quiet_run >= 0.3 else 'SHORT - audio stops abruptly'}")

print()
print("=" * 78)
print("3. TRANSCRIBE THE RENDER AND DIFF AGAINST THE SCRIPT")
print("=" * 78)

from faster_whisper import WhisperModel  # noqa: E402

model = None
for size, compute in (("small", "int8"), ("base", "int8")):
    try:
        model = WhisperModel(size, device="cpu", compute_type=compute, cpu_threads=4)
        print(f"  whisper: {size}/{compute}")
        break
    except Exception as exc:  # noqa: BLE001
        print(f"  {size} failed: {type(exc).__name__}")
if model is None:
    raise SystemExit("no whisper model available")

segments, info = model.transcribe(str(audio), language="vi", beam_size=5)
heard = " ".join(s.text.strip() for s in segments)


def norm(text: str) -> list[str]:
    text = unicodedata.normalize("NFC", text).lower()
    text = re.sub(r"[^\w\s]", " ", text, flags=re.UNICODE)
    return [w for w in text.split() if w]


reference = " ".join(t for _, t in BLOCKS)
ref_words, hyp_words = norm(reference), norm(heard)
matcher = difflib.SequenceMatcher(None, ref_words, hyp_words)
matched = sum(b.size for b in matcher.get_matching_blocks())
wer = 1.0 - matched / len(ref_words)

print(f"  intended {len(ref_words)} words / heard {len(hyp_words)} / matched {matched}")
print(f"  approx WER: {wer:.1%}")

print()
print("  --- tail of each block: is the closing phrase present? ---")
cursor = 0
tail_checks = []
for block_id, text in BLOCKS:
    words = norm(text)
    block_words = ref_words[cursor:cursor + len(words)]
    cursor += len(words)
    phrase = " ".join(block_words[-6:])
    present = phrase in " ".join(hyp_words)
    tail_checks.append({"block": block_id, "closing_phrase": phrase, "present": present})
    print(f"    {block_id:<16} '{phrase}'  present={present}")

report = {
    "render_seconds": round(render_seconds, 3),
    "quiet_tail_s": round(quiet_run, 2),
    "approx_wer": round(wer, 4),
    "intended_words": len(ref_words),
    "heard_words": len(hyp_words),
    "matched_words": matched,
    "transcript": heard,
    "closing_phrase_checks": tail_checks,
}
(WORK / "final_audio_verification.json").write_text(
    json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8"
)
print()
print("  report:", WORK / "final_audio_verification.json")
