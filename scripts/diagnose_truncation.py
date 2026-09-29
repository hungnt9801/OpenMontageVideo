"""Find out who truncates the narration: the TTS call, the download, or my pipeline.

Evidence so far: every block ends at -15 to -19 dBFS with 0.0-0.15s of trailing
silence, in the ORIGINAL fal output as well as the slowed copy. This script
separates the candidates by, for each block:

  1. comparing the last character end-time reported by ElevenLabs against the
     real duration of the file on disk (a shortfall means the file lost audio);
  2. checking the last word's end-time against the audio length;
  3. reporting the raw HTTP response size of a fresh request, so a truncated
     download is distinguishable from a truncated generation.

Usage:
    .venv\\Scripts\\python.exe scripts/diagnose_truncation.py
"""

from __future__ import annotations

import io
import json
import os
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

PROJ = ROOT / "projects" / "nha-su-va-bat-rong"
AUDIO = PROJ / "assets" / "audio"
SLOWED = AUDIO / "final" / "slowed"

BLOCKS = ["01_hook", "02_context", "03_development", "04_twist",
          "05_lesson", "06_reflection", "07_cta"]


def duration_of(path: Path) -> float:
    out = subprocess.run(
        ["ffprobe", "-v", "error", "-show_entries", "format=duration",
         "-of", "csv=p=0", str(path)],
        capture_output=True, text=True, timeout=30,
    )
    return float(out.stdout.strip())


print("=" * 78)
print("1. LAST CHARACTER TIMESTAMP vs REAL FILE DURATION")
print("=" * 78)
print("   If ElevenLabs says the last character ends at T but the file is shorter,")
print("   audio was lost. If they match, the generator itself stopped at T.")
print()
print(f"   {'block':<16} {'last_char_end':>13} {'file_len':>9} {'shortfall':>10}")
findings = []
for block_id in BLOCKS:
    ts_path = AUDIO / "final" / f"{block_id}.timestamps.json"
    mp3_path = AUDIO / "final" / f"{block_id}.mp3"
    if not ts_path.exists() or not mp3_path.exists():
        print(f"   {block_id:<16} (missing inputs)")
        continue
    entries = json.loads(ts_path.read_text(encoding="utf-8"))
    last_end = 0.0
    for entry in entries:
        ends = entry.get("character_end_times_seconds") or []
        if ends:
            last_end = max(last_end, max(ends))
    length = duration_of(mp3_path)
    shortfall = last_end - length
    findings.append({"block": block_id, "last_char_end": round(last_end, 3),
                     "file_len": round(length, 3), "shortfall": round(shortfall, 3)})
    flag = ""
    if shortfall > 0.05:
        flag = "  <-- AUDIO ENDS BEFORE THE LAST CHARACTER"
    elif length - last_end < 0.15:
        flag = "  <-- almost no room after the last character"
    print(f"   {block_id:<16} {last_end:>13.3f} {length:>9.3f} {shortfall:>10.3f}{flag}")

print()
print("=" * 78)
print("2. A FRESH REQUEST - is the GENERATED audio trimmed, or the DOWNLOAD?")
print("=" * 78)

import requests  # noqa: E402

fal_key = (os.environ.get("FAL_KEY") or "").strip()
if not fal_key:
    print("   FAL_KEY not available - skipping the live probe")
else:
    test_text = BLOCKS and "Bạn đang chờ đến khi nào thì mới thấy mình đủ?"
    payload = {
        "text": test_text,
        "voice": "Adam",
        "model_id": "eleven-v3",
        "language_code": "vi",
        "timestamps": True,
        "output_format": "mp3_44100_192",
        "stability": 0.75,
        "similarity_boost": 0.9,
        "style": 0.1,
        "speed": 0.92,
    }
    print(f"   text: {test_text!r}")
    submit = requests.post(
        "https://queue.fal.run/fal-ai/elevenlabs/tts",
        headers={"Authorization": f"Key {fal_key}", "Content-Type": "application/json"},
        json=payload,
        timeout=60,
    )
    print("   submit HTTP", submit.status_code)
    if submit.status_code < 300:
        status_url = submit.json().get("status_url")
        response_url = submit.json().get("response_url")
        import time

        for _ in range(60):
            state = requests.get(status_url, headers={"Authorization": f"Key {fal_key}"},
                                 timeout=30).json()
            if state.get("status") in ("COMPLETED", "OK", "completed"):
                break
            if state.get("status") in ("FAILED", "ERROR"):
                print("   generation failed:", state)
                break
            time.sleep(2)
        result = requests.get(response_url, headers={"Authorization": f"Key {fal_key}"},
                              timeout=30).json()

        audio_url = (result.get("audio") or {}).get("url")
        print("   audio url:", (audio_url or "")[:90])

        if audio_url:
            head = requests.head(audio_url, timeout=30)
            declared = head.headers.get("Content-Length")
            raw = requests.get(audio_url, timeout=120).content
            print(f"   Content-Length header : {declared}")
            print(f"   bytes actually fetched: {len(raw)}")
            print(f"   download complete     : {declared is None or int(declared) == len(raw)}")

            probe_path = Path(PROJ / "renders" / "_audit" / "probe_fresh.mp3")
            probe_path.parent.mkdir(parents=True, exist_ok=True)
            probe_path.write_bytes(raw)
            print(f"   probe duration        : {duration_of(probe_path):.3f}s")

            stamps = result.get("timestamps") or []
            last_end = 0.0
            for entry in stamps:
                ends = entry.get("character_end_times_seconds") or []
                if ends:
                    last_end = max(last_end, max(ends))
            print(f"   last char end (fresh) : {last_end:.3f}s")
            print(f"   => generation itself stops at {last_end:.3f}s? "
                  f"delta to file end = {duration_of(probe_path) - last_end:+.3f}s")

print()
print("=" * 78)
print("3. LOCAL CHAIN - did anything in my own pipeline shorten the audio?")
print("=" * 78)
print(f"   {'block':<16} {'tts_out':>9} {'slowed':>9} {'expected':>9} {'lost':>8}")
for block_id in BLOCKS:
    tts = AUDIO / "final" / f"{block_id}.mp3"
    slow = SLOWED / f"{block_id}.mp3"
    if not (tts.exists() and slow.exists()):
        continue
    a, b = duration_of(tts), duration_of(slow)
    expected = a / 0.83
    print(f"   {block_id:<16} {a:>9.3f} {b:>9.3f} {expected:>9.3f} {expected - b:>8.3f}")

(Path(PROJ / "renders" / "_audit")).mkdir(parents=True, exist_ok=True)
(Path(PROJ / "renders" / "_audit" / "truncation_diagnosis.json")).write_text(
    json.dumps({"timestamp_vs_duration": findings}, ensure_ascii=False, indent=2),
    encoding="utf-8",
)
print()
print("   report: projects/nha-su-va-bat-rong/renders/_audit/truncation_diagnosis.json")
