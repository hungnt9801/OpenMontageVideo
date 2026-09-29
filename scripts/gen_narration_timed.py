"""Regenerate the 7 narration blocks with word-level timestamps.

The first pass had `timestamps: false`, so no caption timing existed and the
composition shipped without word-by-word captions. ElevenLabs returns word
timings when the flag is on; those drive the caption layer.

Timestamps are returned against the ORIGINAL audio. The pipeline later slows each
block with atempo=0.83, so every caption time is divided by that ratio when the
composition is built (see build_composition.py).

Usage:
    .venv\\Scripts\\python.exe scripts/gen_narration_timed.py
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
SETTINGS = {"stability": 0.75, "similarity_boost": 0.9, "style": 0.1, "speed": 0.92}


def duration_of(path: Path) -> float:
    out = subprocess.run(
        ["ffprobe", "-v", "error", "-show_entries", "format=duration",
         "-of", "csv=p=0", str(path)],
        capture_output=True, text=True, timeout=30,
    )
    return float(out.stdout.strip())


report = []
for block_id, text in BLOCKS:
    out_path = OUT / f"{block_id}.mp3"
    result = tool.execute({
        "text": text,
        "voice": VOICE,
        "model_id": MODEL,
        "language_code": "vi",
        "output_format": "mp3_44100_192",
        "timestamps": True,
        "output_path": str(out_path),
        **SETTINGS,
    })
    data = result.data or {}
    timestamps = data.get("timestamps")
    entry = {
        "block": block_id,
        "ok": result.success and out_path.exists(),
        "error": result.error,
        "seconds": round(duration_of(out_path), 3) if out_path.exists() else 0,
        "has_timestamps": bool(timestamps),
        "timestamp_keys": sorted(timestamps.keys()) if isinstance(timestamps, dict) else None,
    }
    report.append(entry)
    print(f"  {block_id:<16} ok={entry['ok']} {entry['seconds']:>6.2f}s "
          f"timestamps={entry['has_timestamps']} keys={entry['timestamp_keys']}")

    if timestamps:
        (OUT / f"{block_id}.timestamps.json").write_text(
            json.dumps(timestamps, ensure_ascii=False, indent=2), encoding="utf-8"
        )
        # show the shape once so the caption builder can rely on it
        if block_id == "01_hook":
            print("    sample:", json.dumps(timestamps, ensure_ascii=False)[:600])

(OUT / "timed_narration_report.json").write_text(
    json.dumps({"voice": VOICE, "model": MODEL, "blocks": report},
               ensure_ascii=False, indent=2),
    encoding="utf-8",
)
print("\nreport:", OUT / "timed_narration_report.json")
