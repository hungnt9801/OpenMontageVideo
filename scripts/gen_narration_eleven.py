"""Generate the final Vietnamese narration with ElevenLabs Adam via fal.

Chosen after the A/B test (see production-status.md): Adam/eleven-v3 measured
14.3% WER on the hook against Piper's 38.1%. multilingual-v2 returned HTTP 422
on the fal endpoint for every voice, so eleven-v3 is the working model.

Output: 7 per-block MP3 files at 192 kbps so pauses can be placed in post.

Usage:
    .venv\\Scripts\\python.exe scripts/gen_narration_eleven.py
"""

from __future__ import annotations

import io
import json
import subprocess
import sys
from pathlib import Path

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

try:
    from dotenv import load_dotenv

    load_dotenv(ROOT / ".env", override=False)
except Exception:  # noqa: BLE001
    pass

from tools.tool_registry import registry  # noqa: E402

registry.discover()
tool = registry.get("fal_elevenlabs_tts")

OUT = ROOT / "projects" / "nha-su-va-bat-rong" / "assets" / "audio" / "final"
OUT.mkdir(parents=True, exist_ok=True)

BLOCKS = [
    ("01_hook", "Bạn đang chờ đến khi nào thì mới thấy mình đủ? Một chiếc bát rỗng đã đi trước bạn ba năm."),
    ("02_context", "Ở một ngôi chùa cổ, có ba nhà sư cùng ấp ủ một giấc mơ: hành hương đến đất Phật. Sư cả nói: ta phải chuẩn bị cho thật đầy đủ. Sư nghèo chỉ có một chiếc bát."),
    ("03_development", "Mùa xuân, sư cả đóng gói. Mùa hạ, sư cả đợi thêm một người bạn đồng hành. Mùa thu, sư cả đợi con đường bớt mưa. Sư nghèo thì không đợi gì cả. Một buổi sáng, ông cầm chiếc bát, đi ra cổng chùa, và không quay lại."),
    ("04_twist", "Ba năm sau, sư nghèo trở về. Áo bạc màu, chân chai sạn, nhưng mắt sáng như người vừa nhìn thấy điều gì đó. Sư cả vẫn ở đó. Và trong kho, có bảy trăm chiếc bát, những thứ ông gom thêm, để dành cho chuyến đi."),
    ("05_lesson", "Đủ không phải là một con số. Đủ là một quyết định. Chiếc bát của sư nghèo rỗng không phải vì ông không có gì, mà vì ông đã chọn như vậy."),
    ("06_reflection", "Bạn cũng đang giữ một chiếc bát: một dự án, một lời xin lỗi, một chuyến đi. Nhưng cái bát không đưa bạn tới đâu cả. Chỉ có bước chân mới làm được điều đó."),
    ("07_cta", "Vậy, bạn còn chờ gì nữa? Bát rỗng rồi. Đi thôi."),
]

VOICE = "Adam"
MODEL = "eleven-v3"

# The first pass at speed 0.92 measured 203 wpm - far above the 135-150 wpm the
# brief asks for, and too fast for a meditative storyteller. ElevenLabs accepts
# speed down to 0.7, so drop close to the floor and re-measure.
VOICE_SETTINGS = {
    "stability": 0.75,        # calm, consistent narration
    "similarity_boost": 0.9,
    "style": 0.1,             # restrained; not a commercial announcer
    "speed": 0.72,
}


def duration_of(path: Path) -> float:
    try:
        out = subprocess.run(
            ["ffprobe", "-v", "error", "-show_entries", "format=duration",
             "-of", "csv=p=0", str(path)],
            capture_output=True, text=True, timeout=30,
        )
        return float(out.stdout.strip())
    except Exception:  # noqa: BLE001
        return 0.0


print(f"voice={VOICE} model={MODEL} settings={VOICE_SETTINGS}")
print()

report = []
total_words = 0
total_seconds = 0.0

for block_id, text in BLOCKS:
    out_path = OUT / f"{block_id}.mp3"
    result = tool.execute({
        "text": text,
        "voice": VOICE,
        "model_id": MODEL,
        "language_code": "vi",
        "output_format": "mp3_44100_192",
        "output_path": str(out_path),
        **VOICE_SETTINGS,
    })
    ok = result.success and out_path.exists()
    seconds = duration_of(out_path) if ok else 0.0
    words = len(text.split())
    wpm = (words / seconds) * 60 if seconds else 0.0
    total_words += words
    total_seconds += seconds
    entry = {
        "block": block_id,
        "ok": ok,
        "error": result.error,
        "words": words,
        "seconds": round(seconds, 2),
        "wpm": round(wpm, 1),
        "path": str(out_path),
    }
    report.append(entry)
    print(f"  {block_id:<16} ok={ok} {words:>3}w {seconds:>6.2f}s {wpm:>5.1f}wpm  {result.error or ''}")

overall = (total_words / total_seconds) * 60 if total_seconds else 0
print()
print(f"TOTAL: {total_words} words, {total_seconds:.2f}s, {overall:.1f} wpm")
print(f"headroom before pauses: {96 - total_seconds:.2f}s of the 96s target")

(OUT / "narration_final_report.json").write_text(
    json.dumps({
        "voice": VOICE,
        "model": MODEL,
        "voice_settings": VOICE_SETTINGS,
        "total_words": total_words,
        "total_seconds": round(total_seconds, 2),
        "overall_wpm": round(overall, 1),
        "blocks": report,
    }, ensure_ascii=False, indent=2),
    encoding="utf-8",
)
print("report:", OUT / "narration_final_report.json")
