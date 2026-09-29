"""A/B the Vietnamese narration voice: Piper (free, local) vs ElevenLabs via fal.

The Piper voice vi_VN-vivos-x_low round-tripped through Whisper at 44.8% WER with
tone substitutions (nha su -> nha so, bat rong -> bat rong), and it is a 16 kHz
x_low model. Before committing 96 seconds of narration to it, produce the same
line from both engines so the choice can be made by ear.

Both outputs are also transcribed back and scored, so there is a measurement next
to the listening test.

Cost: about $0.02 of ElevenLabs audio through the already configured fal key.

Usage:
    .venv\\Scripts\\python.exe scripts/ab_voice.py
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

try:
    from dotenv import load_dotenv

    load_dotenv(ROOT / ".env", override=False)
except Exception:  # noqa: BLE001
    pass

from tools.tool_registry import registry  # noqa: E402

registry.discover()

OUT = ROOT / "projects" / "nha-su-va-bat-rong" / "assets" / "audio" / "ab"
OUT.mkdir(parents=True, exist_ok=True)

# The hook block - the most exposed line in the video.
TEXT = (
    "Bạn đang chờ đến khi nào thì mới thấy mình đủ? "
    "Một chiếc bát rỗng đã đi trước bạn ba năm."
)

print("TEXT:", TEXT)
print()

# ---------------------------------------------------------------- A) Piper
from piper import PiperVoice, SynthesisConfig  # noqa: E402
import wave  # noqa: E402

piper_out = OUT / "A_piper_vi_VN-vivos-x_low.wav"
voice = PiperVoice.load(str(ROOT / "piper_voices" / "vi_VN-vivos-x_low.onnx"))
with wave.open(str(piper_out), "wb") as wav_file:
    voice.synthesize_wav(TEXT, wav_file, syn_config=SynthesisConfig(length_scale=1.15))
print("A) piper      ->", piper_out.name, piper_out.stat().st_size, "bytes")

# ---------------------------------------------------------- B) ElevenLabs
tool = registry.get("fal_elevenlabs_tts")
print("B) fal_elevenlabs_tts status:", tool.get_info().get("status"))

VOICES = ["Adam", "George", "Daniel"]
MODELS = ["multilingual-v2", "eleven-v3"]
b_results = []

for v in VOICES:
    for m in MODELS:
        out_path = OUT / f"B_elevenlabs_{v}_{m}.mp3"
        try:
            result = tool.execute({
                "text": TEXT,
                "voice": v,
                "model_id": m,
                "language_code": "vi",
                "stability": 0.75,
                "similarity_boost": 0.9,
                "style": 0.1,
                "speed": 0.95,
                "output_format": "mp3_44100_192",
                "output_path": str(out_path),
            })
        except Exception as exc:  # noqa: BLE001
            print(f"   {v}/{m}: ERROR {type(exc).__name__}: {exc}")
            b_results.append({"voice": v, "model": m, "ok": False, "error": str(exc)})
            continue

        ok = result.success and out_path.exists()
        print(f"   {v}/{m}: ok={ok} error={result.error} "
              f"bytes={out_path.stat().st_size if out_path.exists() else 0}")
        b_results.append({
            "voice": v,
            "model": m,
            "ok": ok,
            "error": result.error,
            "path": str(out_path),
        })

# ------------------------------------------------ Round-trip verification
def normalise(text: str) -> list[str]:
    text = unicodedata.normalize("NFC", text).lower()
    text = re.sub(r"[^\w\s]", " ", text, flags=re.UNICODE)
    return [w for w in text.split() if w]


print("\n--- transcribing every candidate back ---")
try:
    from faster_whisper import WhisperModel

    model = WhisperModel("base", device="cpu", compute_type="int8", cpu_threads=4)
except Exception as exc:  # noqa: BLE001
    print("could not load whisper:", exc)
    model = None

ref = normalise(TEXT)
scores = []
if model:
    candidates = [piper_out] + [
        Path(r["path"]) for r in b_results if r.get("ok") and r.get("path")
    ]
    for path in candidates:
        wav_for_asr = path
        if path.suffix == ".mp3":
            wav_for_asr = path.with_suffix(".asr.wav")
            subprocess.run(
                ["ffmpeg", "-y", "-hide_banner", "-loglevel", "error",
                 "-i", str(path), "-ar", "16000", "-ac", "1", str(wav_for_asr)],
                check=True,
            )
        segments, info = model.transcribe(str(wav_for_asr), language="vi", beam_size=5)
        heard = " ".join(s.text.strip() for s in segments)
        hyp = normalise(heard)
        matcher = difflib.SequenceMatcher(None, ref, hyp)
        matched = sum(b.size for b in matcher.get_matching_blocks())
        wer = 1.0 - (matched / len(ref)) if ref else 1.0
        scores.append({
            "file": path.name,
            "heard": heard,
            "wer": round(wer, 4),
            "ratio": round(matcher.ratio(), 4),
        })
        print(f"\n  {path.name}")
        print(f"    heard: {heard}")
        print(f"    WER  : {wer:.1%}")

(OUT / "ab_report.json").write_text(
    json.dumps(
        {
            "text": TEXT,
            "piper": {"file": piper_out.name, "model": "vi_VN-vivos-x_low", "length_scale": 1.15},
            "elevenlabs_candidates": b_results,
            "round_trip": scores,
            "note": "Listen to the files in the ab/ folder and choose.",
        },
        ensure_ascii=False,
        indent=2,
    ),
    encoding="utf-8",
)
print("\nreport:", OUT / "ab_report.json")
print("\nFILES TO LISTEN TO:")
for entry in sorted(OUT.glob("*.*")):
    if entry.suffix in (".wav", ".mp3"):
        print("   ", entry)
