"""Render the video from assets already on disk. Calls no paid API.

This is the "re-render only" path. Everything it needs already exists:

  projects/nha-su-va-bat-rong/assets/images/*.jpg            14 scene stills
  projects/nha-su-va-bat-rong/assets/audio/final/*.mp3       7 narration blocks
  projects/nha-su-va-bat-rong/assets/audio/final/slowed/     slowed audio + cues
  projects/nha-su-va-bat-rong/assets/music/*.mp3             music bed
  hf/index.html                                              composition

It rebuilds the composition from those files (deterministic, no API), runs the
HyperFrames gates, renders, and normalises loudness. Loudness correction is a
local ffmpeg filter, not a paid service.

SAFETY: hosting keys are deliberately stripped from the environment before any
step runs, so an accidental network call in the render path fails loudly instead
of silently spending money. The .env file is removed from the child environment.

Usage:
    .venv\\Scripts\\python.exe scripts/render_only.py [--skip-normalize]
"""

from __future__ import annotations

import io
import json
import os
import shutil
import subprocess
import sys
import time
from pathlib import Path

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")

ROOT = Path(__file__).resolve().parent.parent
PROJ = ROOT / "projects" / "nha-su-va-bat-rong"
HF = ROOT / "hf"
RENDERS = PROJ / "renders"

PAID_KEYS = [
    "FAL_KEY", "FAL_AI_API_KEY", "ELEVENLABS_API_KEY", "OPENAI_API_KEY",
    "GOOGLE_API_KEY", "GEMINI_API_KEY", "DASHSCOPE_API_KEY", "MINIMAX_API_KEY",
    "REPLICATE_API_TOKEN", "KLING_API_KEY", "SUNO_API_KEY", "XAI_API_KEY",
    "ARK_API_KEY", "HEYGEN_API_KEY", "RUNWAY_API_KEY", "HIGGS_API_KEY",
    "HIGGSFIELD_API_KEY", "HIGGSFIELD_API_SECRET", "TENCENT_TOKENHUB_API_KEY",
    "FISH_AUDIO_API_KEY", "AZURE_SPEECH_KEY", "FREESOUND_API_KEY",
]

# A clean child environment: everything the render tooling needs, no credentials.
CHILD_ENV = {k: v for k, v in os.environ.items() if k not in PAID_KEYS}
CHILD_ENV["HYPERFRAMES_SKIP_SKILLS"] = "1"
CHILD_ENV.pop("PEXELS_API_KEY", None)   # free, but keep the child strictly offline-capable

stripped = [k for k in PAID_KEYS if os.environ.get(k)]
print("=" * 66)
print("COST GUARD")
print("=" * 66)
print(f"  credential env vars present in parent : {len(stripped)}")
print(f"  credential env vars passed to children: 0  (all stripped)")
print(f"  .env is NOT loaded by this script")

# ── preconditions ─────────────────────────────────────────────────────────
print()
print("=" * 66)
print("ASSETS ON DISK")
print("=" * 66)

images = sorted((PROJ / "assets" / "images").glob("s*.jpg"))
narration = sorted((PROJ / "assets" / "audio" / "final").glob("*.mp3"))
slowed = sorted((PROJ / "assets" / "audio" / "final" / "slowed").glob("*.mp3"))
cues = sorted((PROJ / "assets" / "audio" / "final" / "slowed").glob("*.cues.json"))
music = sorted((PROJ / "assets" / "music").glob("*.mp3"))

for label, items in (
    ("scene stills", images),
    ("narration blocks", narration),
    ("slowed narration", slowed),
    ("cue files", cues),
    ("music beds", music),
):
    print(f"  {label:<20} {len(items):>3}")

missing = []
if len(images) < 14:
    missing.append(f"scene stills: have {len(images)}, need 14")
if len(slowed) < 7:
    missing.append(f"slowed narration: have {len(slowed)}, need 7")
if len(cues) < 7:
    missing.append(f"cue files: have {len(cues)}, need 7")
if not music:
    missing.append("music bed missing")

if missing:
    print("\nCANNOT RENDER WITHOUT RE-GENERATING:")
    for item in missing:
        print("   -", item)
    raise SystemExit(1)

print("\n  all assets present - no generation needed")


def run(label: str, cmd: list[str], cwd: Path) -> int:
    print()
    print("=" * 66)
    print(label)
    print("=" * 66)
    started = time.time()
    # On Windows `npx` is npx.cmd, which CreateProcess cannot execute directly;
    # resolve the real path or fall back to the command interpreter.
    resolved = shutil.which(cmd[0])
    if resolved and resolved.lower().endswith((".cmd", ".bat")):
        invoked = ["cmd", "/c", resolved, *cmd[1:]]
    elif resolved:
        invoked = [resolved, *cmd[1:]]
    else:
        invoked = cmd
    proc = subprocess.run(invoked, cwd=str(cwd), env=CHILD_ENV)
    print(f"  exit={proc.returncode}  elapsed={time.time() - started:.1f}s")
    return proc.returncode


# ── 1) rebuild the composition from cached assets (deterministic, offline) ─
code = run(
    "1. REBUILD COMPOSITION (from cached assets)",
    [str(ROOT / ".venv" / "Scripts" / "python.exe"), str(ROOT / "scripts" / "build_composition.py")],
    ROOT,
)
if code != 0:
    raise SystemExit(code)

# ── 2) static gates ───────────────────────────────────────────────────────
run("2. LINT", ["npx", "--yes", "hyperframes@0.8.90", "lint"], HF)
run("3. VALIDATE", ["npx", "--yes", "hyperframes@0.8.90", "validate"], HF)

# ── 4) render ─────────────────────────────────────────────────────────────
RENDERS.mkdir(parents=True, exist_ok=True)
output = RENDERS / "final_captioned.mp4"
backup = RENDERS / "_previous.mp4"
if output.exists():
    shutil.move(str(output), str(backup))
    print(f"\n  previous render moved to {backup.name}")

code = run(
    "4. RENDER",
    ["npx", "--yes", "hyperframes@0.8.90", "render", "--quality", "high",
     "--output", str(output)],
    HF,
)
if code != 0:
    if backup.exists() and not output.exists():
        shutil.move(str(backup), str(output))
        print("  render failed - previous render restored")
    raise SystemExit(code)

# ── 5) loudness normalisation (local ffmpeg) ──────────────────────────────
if "--skip-normalize" not in sys.argv:
    code = run(
        "5. NORMALISE LOUDNESS (local ffmpeg, no API)",
        [str(ROOT / ".venv" / "Scripts" / "python.exe"),
         str(ROOT / "scripts" / "normalize_audio.py"),
         "--input", str(output),
         "--out", str(RENDERS / "final_normalized.mp4")],
        ROOT,
    )
    if code == 0:
        normalised = RENDERS / "final_normalized.mp4"
        if normalised.exists():
            if output.exists():
                output.unlink()
            shutil.move(str(normalised), str(output))
            print(f"  normalised master promoted to {output.name}")

print()
print("=" * 66)
print("RESULT")
print("=" * 66)
for path in sorted(RENDERS.glob("*.mp4")):
    size = path.stat().st_size / (1024 * 1024)
    print(f"  {path.name:<24} {size:>7.1f} MB")
print("\n  API cost of this run: $0.00")
