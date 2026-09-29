"""Generate the 7 Vietnamese narration blocks with Piper (local, free).

Voice: vi_VN-vivos-x_low (the only Vietnamese Piper voice published).
Pacing: the tool's length_scale is a duration multiplier on each phoneme.
  > 1.0 is slower. Target 135-150 wpm from a ~150 wpm baseline, so start at 1.15.
This script synthesises, measures the real duration of each block with ffprobe,
and reports the achieved words-per-minute so the pacing policy can be tuned.

Piper cannot express a silent pause, and punctuation pauses are unreliable, so
the scripted pauses are inserted later in post with ffmpeg (see the manifest).

Usage:
    .venv\\Scripts\\python.exe scripts/gen_narration.py [--length-scale 1.15]
"""

from __future__ import annotations

import io
import json
import subprocess
import sys
import wave
from pathlib import Path

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")

ROOT = Path(__file__).resolve().parent.parent
VOICE = ROOT / "piper_voices" / "vi_VN-vivos-x_low.onnx"
OUT_DIR = ROOT / "projects" / "nha-su-va-bat-rong" / "assets" / "audio"
OUT_DIR.mkdir(parents=True, exist_ok=True)

LENGTH_SCALE = 1.15
if "--length-scale" in sys.argv:
    LENGTH_SCALE = float(sys.argv[sys.argv.index("--length-scale") + 1])

# The 7 narrative blocks. No ellipsis (Piper may vocalise "..."), and no reliance
# on commas for the scripted pauses.
BLOCKS = [
    (
        "01_hook",
        "Bạn đang chờ đến khi nào thì mới thấy mình đủ? "
        "Một chiếc bát rỗng đã đi trước bạn ba năm.",
    ),
    (
        "02_context",
        "Ở một ngôi chùa cổ, có ba nhà sư cùng ấp ủ một giấc mơ: hành hương đến đất Phật. "
        "Sư cả nói: ta phải chuẩn bị cho thật đầy đủ. Sư nghèo chỉ có một chiếc bát.",
    ),
    (
        "03_development",
        "Mùa xuân, sư cả đóng gói. Mùa hạ, sư cả đợi thêm một người bạn đồng hành. "
        "Mùa thu, sư cả đợi con đường bớt mưa. Sư nghèo thì không đợi gì cả. "
        "Một buổi sáng, ông cầm chiếc bát, đi ra cổng chùa, và không quay lại.",
    ),
    (
        "04_twist",
        "Ba năm sau, sư nghèo trở về. Áo bạc màu, chân chai sạn, "
        "nhưng mắt sáng như người vừa nhìn thấy điều gì đó. Sư cả vẫn ở đó. "
        "Và trong kho, có bảy trăm chiếc bát, những thứ ông gom thêm, để dành cho chuyến đi.",
    ),
    (
        "05_lesson",
        "Đủ không phải là một con số. Đủ là một quyết định. "
        "Chiếc bát của sư nghèo rỗng không phải vì ông không có gì, "
        "mà vì ông đã chọn như vậy.",
    ),
    (
        "06_reflection",
        "Bạn cũng đang giữ một chiếc bát: một dự án, một lời xin lỗi, một chuyến đi. "
        "Nhưng cái bát không đưa bạn tới đâu cả. Chỉ có bước chân mới làm được điều đó.",
    ),
    (
        "07_cta",
        "Vậy, bạn còn chờ gì nữa? Bát rỗng rồi. Đi thôi.",
    ),
]


def duration_of(path: Path) -> float:
    try:
        out = subprocess.run(
            ["ffprobe", "-v", "error", "-show_entries", "format=duration",
             "-of", "csv=p=0", str(path)],
            capture_output=True, text=True, timeout=30,
        )
        return float(out.stdout.strip())
    except Exception:  # noqa: BLE001
        with wave.open(str(path)) as wav:
            return wav.getnframes() / float(wav.getframerate())


from piper import PiperVoice, SynthesisConfig  # noqa: E402

print("voice :", VOICE)
print("exists:", VOICE.exists(), f"({VOICE.stat().st_size if VOICE.exists() else 0} bytes)")
print("length_scale:", LENGTH_SCALE)
print()

voice = PiperVoice.load(str(VOICE))
config = SynthesisConfig(length_scale=LENGTH_SCALE)

report = []
total_words = 0
total_seconds = 0.0

for block_id, text in BLOCKS:
    out_path = OUT_DIR / f"{block_id}.wav"
    with wave.open(str(out_path), "wb") as wav_file:
        voice.synthesize_wav(text, wav_file, syn_config=config)

    seconds = duration_of(out_path)
    words = len(text.split())
    wpm = (words / seconds) * 60 if seconds else 0
    total_words += words
    total_seconds += seconds
    entry = {
        "block": block_id,
        "words": words,
        "seconds": round(seconds, 2),
        "wpm": round(wpm, 1),
        "path": str(out_path),
    }
    report.append(entry)
    print(f"  {block_id:<16} {words:>3} words  {seconds:>6.2f}s  {wpm:>5.1f} wpm")

overall = (total_words / total_seconds) * 60 if total_seconds else 0
print()
print(f"TOTAL narration: {total_words} words, {total_seconds:.2f}s, {overall:.1f} wpm")
print("script length before pauses (target 96s of video):", f"{total_seconds:.2f}s")
print("planned pauses + 1.5s silence will be inserted in post")

(OUT_DIR / "narration_report.json").write_text(
    json.dumps(
        {
            "voice": VOICE.name,
            "length_scale": LENGTH_SCALE,
            "total_words": total_words,
            "total_seconds": round(total_seconds, 2),
            "overall_wpm": round(overall, 1),
            "blocks": report,
        },
        ensure_ascii=False,
        indent=2,
    ),
    encoding="utf-8",
)
print("report:", OUT_DIR / "narration_report.json")
