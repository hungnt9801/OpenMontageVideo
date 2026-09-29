"""Verify the credentials in .env are found and actually work.

Usage:
    .venv\\Scripts\\python.exe scripts/check_keys.py

What it does:
  1. Confirms .env is located and loaded (secrets are masked, never printed).
  2. Re-runs the OpenMontage registry preflight for the capabilities the
     image-led plan needs.
  3. If a fal.ai key is present, makes ONE authenticated request to prove the
     key is valid. No billable generation is performed.
"""

from __future__ import annotations

import io
import os
import sys
from pathlib import Path

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")

ROOT = Path(__file__).resolve().parent.parent
ENV_PATH = ROOT / ".env"

# Make `tools` / `lib` importable no matter where the script is invoked from.
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

WATCHED_KEYS = [
    ("FAL_KEY", "bat buoc cho Muc 1 (anh)"),
    ("FAL_AI_API_KEY", "alias cua FAL_KEY"),
    ("PEXELS_API_KEY", "mien phi - anh stock $0"),
    ("PIXABAY_API_KEY", "mien phi - anh stock $0 + nhac $0"),
    ("ELEVENLABS_API_KEY", "tuy chon - giong doc xin hon"),
    ("DASHSCOPE_API_KEY", "tuy chon - Qwen Image"),
]

RELEVANT_CAPABILITIES = (
    "image_generation",
    "tts",
    "music_search",
    "video_post",
    "analysis",
    "enhancement",
)

print("=" * 68)
print("1) .env")
print("=" * 68)
print("path  :", ENV_PATH)
print("exists:", ENV_PATH.exists())

try:
    from dotenv import load_dotenv

    print("loaded:", load_dotenv(ENV_PATH, override=False))
except Exception as exc:  # noqa: BLE001
    print("dotenv import failed:", exc)

print()
for name, note in WATCHED_KEYS:
    value = (os.environ.get(name) or "").strip()
    if not value:
        print(f"  [    ] {name:<22} chua set        ({note})")
    else:
        masked = f"{value[:4]}...{value[-4:]}" if len(value) > 12 else "(qua ngan)"
        print(f"  [ OK ] {name:<22} len={len(value):<5} {masked}   ({note})")

print()
print("=" * 68)
print("2) Registry preflight")
print("=" * 68)

from tools.tool_registry import registry  # noqa: E402

registry.discover()

for cap in RELEVANT_CAPABILITIES:
    tools = registry.get_by_capability(cap)
    available = [t.name for t in tools if t.get_info().get("status") == "available"]
    print(f"  {cap:<20} {len(available)}/{len(tools):<3} {', '.join(available) if available else '(none)'}")

engine_info = registry.get("video_compose").get_info()
print()
print("  render engines:", engine_info.get("render_engines"))

print()
print("=" * 68)
print("3) Live fal.ai key test (chi chay khi co key)")
print("=" * 68)

fal_key = (os.environ.get("FAL_KEY") or os.environ.get("FAL_AI_API_KEY") or "").strip()
if not fal_key:
    print("  BO QUA - FAL_KEY chua duoc dien.")
    print("  Mo .env, dat key vao sau dau '=' o dong 'FAL_KEY=', luu file, chay lai lenh nay.")
else:
    try:
        import requests

        response = requests.get(
            "https://rest.alpha.fal.ai/tokens/",
            headers={"Authorization": f"Key {fal_key}"},
            timeout=25,
        )
        print("  fal.ai auth check -> HTTP", response.status_code)
        if response.status_code in (200, 201):
            print("  KET LUAN: FAL_KEY HOP LE - san sang gen anh.")
        elif response.status_code in (401, 403):
            print("  KET LUAN: FAL_KEY BI TU CHOI (sai key / thieu quyen / chua nap credit).")
            print("  body:", response.text[:220])
        else:
            print("  KET LUAN: khong ket luan duoc.")
            print("  body:", response.text[:220])
    except Exception as exc:  # noqa: BLE001
        print("  Loi khi goi fal.ai:", exc)
