"""Verify narration block tails INSIDE the render, using the expected phrase.

The previous check was too crude: it measured the last 3s of the whole file, which
at that point contains the music bed, not the narration. This one locates each
narration block by its scheduled start time and checks that the audio immediately
after that block falls quiet - which is what "the sentence ends properly" means.

For every block it also transcribes the block's own window with an initial_prompt
set to the expected text, so ASR misses due to tone confusion do not masquerade as
missing words.

Usage:
    .venv\\Scripts\\python.exe scripts/verify_block_tails.py
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
SLOWED = PROJ / "assets" / "audio" / "final" / "slowed"

BLOCKS = [
    ("01_hook", "Bạn đang chờ đến khi nào thì mới thấy mình đủ? Một chiếc bát rỗng đã đi trước bạn ba năm."),
    ("02_context", "Ở một ngôi chùa cổ, có ba nhà sư cùng ấp ủ một giấc mơ: hành hương đến đất Phật. Sư cả nói: ta phải chuẩn bị cho thật đầy đủ. Sư nghèo chỉ có một chiếc bát."),
    ("03_development", "Mùa xuân, sư cả đóng gói. Mùa hạ, sư cả đợi thêm một người bạn đồng hành. Mùa thu, sư cả đợi con đường bớt mưa. Sư nghèo thì không đợi gì cả. Một buổi sáng, ông cầm chiếc bát, đi ra cổng chùa, và không quay lại."),
    ("04_twist", "Ba năm sau, sư nghèo trở về. Áo bạc màu, chân chai sạn, nhưng mắt sáng như người vừa nhìn thấy điều gì đó. Sư cả vẫn ở đó. Và trong kho, có bảy trăm chiếc bát, những thứ ông gom thêm, để dành cho chuyến đi."),
    ("05_lesson", "Đủ không phải là một con số. Đủ là một quyết định. Chiếc bát của sư nghèo rỗng không phải vì ông không có gì, mà vì ông đã chọn như vậy."),
    ("06_reflection", "Bạn cũng đang giữ một chiếc bát: một dự án, một lời xin lỗi, một chuyến đi. Nhưng cái bát không đưa bạn tới đâu cả. Chỉ có bước chân mới làm được điều đó."),
    ("07_cta", "Vậy, bạn còn chờ gì nữa? Bát rỗng rồi. Đi thôi."),
]

# Recreate the exact schedule build_composition.py used.
import importlib.util  # noqa: E402

spec = importlib.util.spec_from_file_location("bc", ROOT / "scripts" / "build_composition.py")


def schedule() -> dict[str, dict]:
    """Read the schedule the builder printed, saved alongside the composition."""
    path = ROOT / "hf" / "narration_layout.json"
    if path.exists():
        return {b["block"]: b for b in json.loads(path.read_text(encoding="utf-8"))}
    return {}


LAYOUT = schedule()
if not LAYOUT:
    raise SystemExit("hf/narration_layout.json not found - rebuild the composition first")

print("=" * 80)
print("BLOCK-LEVEL TAIL CHECK INSIDE THE RENDER")
print("=" * 80)
print(f"  {'block':<16} {'starts':>7} {'len':>6} {'tail after':>11} {'quiet':>7}  verdict")


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


def norm(text: str) -> list[str]:
    text = unicodedata.normalize("NFC", text).lower()
    text = re.sub(r"[^\w\s]", " ", text, flags=re.UNICODE)
    return [w for w in text.split() if w]


from faster_whisper import WhisperModel  # noqa: E402

model = None
for size, compute in (("small", "int8"), ("base", "int8")):
    try:
        model = WhisperModel(size, device="cpu", compute_type=compute, cpu_threads=4)
        print(f"  whisper: {size}/{compute}")
        break
    except Exception:  # noqa: BLE001
        continue
if model is None:
    raise SystemExit("no whisper model")

results = []
for block_id, text in BLOCKS:
    entry = LAYOUT.get(block_id)
    if not entry:
        print(f"  {block_id}: not in schedule")
        continue
    start = entry["start"]
    length = entry["duration"]

    # The gap after this block should be quiet.
    gap = 0.5
    tail = windows(FINAL, start + length - 0.05, gap, 0.05)
    quiet = 0.0
    for value in tail:
        if value < -32.0:
            quiet += 0.05
        else:
            break

    # Transcribe just this block, biased with the expected text.
    clip = WORK / f"_{block_id}.wav"
    subprocess.run(
        ["ffmpeg", "-y", "-hide_banner", "-loglevel", "error",
         "-ss", f"{start:.3f}", "-t", f"{length:.3f}", "-i", str(FINAL),
         "-vn", "-ac", "1", "-ar", "16000", str(clip)],
        check=True,
    )
    segments, _ = model.transcribe(
        str(clip), language="vi", beam_size=5, initial_prompt=text
    )
    heard = " ".join(s.text.strip() for s in segments)
    ref, hyp = norm(text), norm(heard)
    matcher = difflib.SequenceMatcher(None, ref, hyp)
    matched = sum(b.size for b in matcher.get_matching_blocks())
    wer = 1 - matched / len(ref)
    closing = " ".join(ref[-6:])
    present = closing in " ".join(hyp)

    verdict = "OK"
    if not present:
        verdict = "closing phrase not recognised"
    if quiet < 0.15:
        verdict = "no quiet gap after block"

    results.append({
        "block": block_id,
        "start": start,
        "duration": length,
        "quiet_after_s": round(quiet, 2),
        "wer": round(wer, 4),
        "closing_phrase": closing,
        "closing_present": present,
        "heard_tail": " ".join(hyp[-8:]),
        "verdict": verdict,
    })
    print(f"  {block_id:<16} {start:>7.2f} {length:>6.2f} {quiet:>10.2f}s "
          f"{'yes' if quiet >= 0.15 else 'NO':>7}  {verdict}")
    print(f"      closing: '{closing}'   heard: '{' '.join(hyp[-8:])}'  WER={wer:.0%}")

print()
print("=" * 80)
bad = [r for r in results if r["verdict"] != "OK"]
print(f"  blocks checked: {len(results)}   problems: {len(bad)}")
for entry in bad:
    print(f"    - {entry['block']}: {entry['verdict']}")

(WORK / "block_tail_verification.json").write_text(
    json.dumps(results, ensure_ascii=False, indent=2), encoding="utf-8"
)
for clip in WORK.glob("_*.wav"):
    clip.unlink()
print()
print("  report:", WORK / "block_tail_verification.json")
