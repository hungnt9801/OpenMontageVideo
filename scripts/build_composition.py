"""Generate the HyperFrames composition for nha-su-va-bat-rong.

Deterministic generator: rerunning it reproduces the composition exactly, with the
timeline derived from the measured narration durations rather than hand-typed.

Reads:
  assets/images/*.jpg                       14 scene stills at 1080x1920
  assets/audio/final/slowed/*.mp3           7 narration blocks (82.43s total)
  assets/music/bed_elevenlabs.mp3           105s music bed

Writes:
  hf/index.html                             the composition
  hf/assets/...                             copies of the media it references

Usage:
    .venv\\Scripts\\python.exe scripts/build_composition.py
"""

from __future__ import annotations

import io
import json
import shutil
import subprocess
import sys
from pathlib import Path

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")

ROOT = Path(__file__).resolve().parent.parent
PROJ = ROOT / "projects" / "nha-su-va-bat-rong"
HF = ROOT / "hf"
ASSETS = HF / "assets"

IMAGES = PROJ / "assets" / "images"
NARRATION = PROJ / "assets" / "audio" / "final" / "slowed"
MUSIC = PROJ / "assets" / "music" / "bed_elevenlabs.mp3"

TOTAL = 96.0
FPS = 30


def frame_snap(seconds: float) -> float:
    return round(round(seconds * FPS) / FPS, 4)


def duration_of(path: Path) -> float:
    out = subprocess.run(
        ["ffprobe", "-v", "error", "-show_entries", "format=duration",
         "-of", "csv=p=0", str(path)],
        capture_output=True, text=True, timeout=30,
    )
    return float(out.stdout.strip())

# ── narration blocks ──────────────────────────────────────────────────────
# Block durations are measured from the slowed audio rather than hard-coded, and
# the start times are packed automatically: a base gap between blocks, then any
# remaining slack spread evenly. That keeps the narration inside the 96s timeline
# when the pacing or the audio length changes, instead of silently overflowing.
NARRATION_BLOCKS = [
    "01_hook",
    "02_context",
    "03_development",
    "04_twist",
    "05_lesson",
    "06_reflection",
    "07_cta",
]
BASE_GAP = 0.7          # comfortable breath between blocks
BLOCK_START = 0.5       # small beat before the first line
END_PAD = 0.8           # silence reserved after the last line so it resolves
                        # instead of being cut by the end of the video


def audio_seconds(block_id: str) -> float:
    path = NARRATION / f"{block_id}.mp3"
    out = subprocess.run(
        ["ffprobe", "-v", "error", "-show_entries", "format=duration",
         "-of", "csv=p=0", str(path)],
        capture_output=True, text=True, timeout=30,
    )
    return float(out.stdout.strip())


_durations = [audio_seconds(b) for b in NARRATION_BLOCKS]
_speech_total = sum(_durations)
_slack = (TOTAL - BLOCK_START - END_PAD - _speech_total
          - BASE_GAP * (len(_durations) - 1))

if _slack < 0:
    raise SystemExit(
        f"narration does not fit: {_speech_total:.2f}s of speech plus gaps exceeds "
        f"the {TOTAL:.0f}s timeline by {-_slack:.2f}s. Shorten the script, speed the "
        f"tempo up, or raise the video duration."
    )

_gap = BASE_GAP + _slack / (len(_durations) - 1)
NARRATION_LAYOUT = []
_cursor = BLOCK_START
for _block_id, _seconds in zip(NARRATION_BLOCKS, _durations):
    NARRATION_LAYOUT.append((_block_id, round(_seconds, 3), frame_snap(_cursor)))
    _cursor += _seconds + _gap

print(f"narration: {_speech_total:.2f}s speech, gap {_gap:.2f}s, "
      f"last block ends at {NARRATION_LAYOUT[-1][2] + NARRATION_LAYOUT[-1][1]:.2f}s "
      f"of {TOTAL:.0f}s")

# Dump the schedule so the verification scripts can locate each block in the
# render without duplicating the packing maths.
(HF / "narration_layout.json").write_text(
    json.dumps(
        [{"block": b, "duration": s, "start": t} for b, s, t in NARRATION_LAYOUT],
        indent=2,
    ),
    encoding="utf-8",
)

# ── scenes: (id, start, duration, motion, motion_amount, overlays) ─────────
# motion drives the Ken Burns / parallax recipe; motion_amount is the scale delta.
SCENES = [
    # HOOK
    dict(id="s01_courtyard", start=0.0, dur=8.0, motion="push_in", amount=0.07,
         overlays=["title"]),
    dict(id="s02_step", start=8.0, dur=6.5, motion="truck_right", amount=0.05,
         overlays=[]),
    # CONTEXT
    dict(id="s03_beads", start=14.5, dur=10.0, motion="push_in", amount=0.05,
         overlays=[]),
    dict(id="s04_bowl", start=24.5, dur=8.0, motion="slow_zoom", amount=0.09,
         overlays=[]),
    dict(id="s05_folding", start=32.5, dur=10.0, motion="truck_right", amount=0.05,
         overlays=["season_spring"]),
    # DEVELOPMENT
    dict(id="s06_rain_stone", start=42.5, dur=7.0, motion="tilt_down", amount=0.05,
         overlays=["season_rain"]),
    dict(id="s07_gate", start=49.5, dur=7.5, motion="push_in", amount=0.06,
         overlays=["season_autumn"]),
    # TWIST
    dict(id="s08_monk_reference", start=57.0, dur=8.0, motion="tilt_up", amount=0.05,
         overlays=[]),
    dict(id="s09_700_bowls", start=65.0, dur=9.0, motion="pull_out", amount=0.10,
         overlays=["hero_700"]),
    # LESSON
    dict(id="s10_last_bowl", start=74.0, dur=5.5, motion="slow_zoom", amount=0.08,
         overlays=[]),
    dict(id="s11_open_hand", start=79.5, dur=6.0, motion="push_in", amount=0.05,
         overlays=["hero_lesson"]),
    # REFLECTION
    dict(id="s12_folded_robe", start=85.5, dur=5.0, motion="push_in", amount=0.05,
         overlays=[]),
    dict(id="s13_stone_buddha", start=90.5, dur=3.5, motion="tilt_up", amount=0.04,
         overlays=[]),
    # CTA + LOOP
    dict(id="s14_courtyard_dusk", start=94.0, dur=2.0, motion="pull_out", amount=0.06,
         overlays=["cta"]),
]


def frame_snap(seconds: float) -> float:
    return round(round(seconds * FPS) / FPS, 4)


def duration_of(path: Path) -> float:
    out = subprocess.run(
        ["ffprobe", "-v", "error", "-show_entries", "format=duration",
         "-of", "csv=p=0", str(path)],
        capture_output=True, text=True, timeout=30,
    )
    return float(out.stdout.strip())


# ── copy media into the hf project ────────────────────────────────────────
(ASSETS / "img").mkdir(parents=True, exist_ok=True)
(ASSETS / "audio").mkdir(parents=True, exist_ok=True)

for scene in SCENES:
    src = IMAGES / f"{scene['id']}.jpg"
    if not src.exists():
        raise SystemExit(f"missing image: {src}")
    shutil.copy2(src, ASSETS / "img" / src.name)

for block_id, _, _ in NARRATION_LAYOUT:
    src = NARRATION / f"{block_id}.mp3"
    if not src.exists():
        raise SystemExit(f"missing narration: {src}")
    shutil.copy2(src, ASSETS / "audio" / src.name)

shutil.copy2(MUSIC, ASSETS / "audio" / "bed.mp3")
print("media copied into hf/assets")

# ── verify the layout covers the timeline with no gaps ────────────────────
cursor = 0.0
for scene in SCENES:
    if scene["start"] > cursor + 0.01:
        raise SystemExit(
            f"gap in timeline before {scene['id']}: cursor={cursor} start={scene['start']}"
        )
    cursor = scene["start"] + scene["dur"]
    scene["start"] = frame_snap(scene["start"])
    scene["dur"] = frame_snap(scene["dur"])
print(f"timeline covered: 0.00 -> {cursor:.2f}s (target {TOTAL}s)")

# ── build the composition ─────────────────────────────────────────────────
def motion_vars(motion: str, amount: float) -> tuple[dict, dict]:
    """Return (from, to) as dicts of CSS custom properties.

    Two consumers need this: the inline style attribute (a CSS string) and the
    GSAP tween (a JS object). Keeping it as dicts and serialising per consumer
    avoids hand-built CSS strings leaking into JavaScript object literals.
    """
    if motion == "push_in":
        return (
            {"--sx": 1.0, "--sy": 1.0, "--px": "0%", "--py": "0%"},
            {"--sx": 1 + amount, "--sy": 1 + amount, "--px": "0%", "--py": "-1.2%"},
        )
    if motion == "pull_out":
        return (
            {"--sx": 1 + amount, "--sy": 1 + amount, "--px": "0%", "--py": "-1.2%"},
            {"--sx": 1.0, "--sy": 1.0, "--px": "0%", "--py": "0%"},
        )
    if motion == "slow_zoom":
        return (
            {"--sx": 1.0, "--sy": 1.0, "--px": "0%", "--py": "0%"},
            {"--sx": 1 + amount, "--sy": 1 + amount, "--px": "0%", "--py": "0%"},
        )
    if motion == "truck_right":
        return (
            {"--sx": 1 + amount, "--sy": 1 + amount, "--px": "-1.6%", "--py": "0%"},
            {"--sx": 1 + amount, "--sy": 1 + amount, "--px": "1.6%", "--py": "0%"},
        )
    if motion == "tilt_down":
        return (
            {"--sx": 1 + amount, "--sy": 1 + amount, "--px": "0%", "--py": "-1.8%"},
            {"--sx": 1 + amount, "--sy": 1 + amount, "--px": "0%", "--py": "1.8%"},
        )
    if motion == "tilt_up":
        return (
            {"--sx": 1 + amount, "--sy": 1 + amount, "--px": "0%", "--py": "1.8%"},
            {"--sx": 1 + amount, "--sy": 1 + amount, "--px": "0%", "--py": "-1.8%"},
        )
    return (
        {"--sx": 1.0, "--sy": 1.0, "--px": "0%", "--py": "0%"},
        {"--sx": 1.0, "--sy": 1.0, "--px": "0%", "--py": "0%"},
    )


def css_string(variables: dict) -> str:
    """Serialise variables for an inline style attribute."""
    return "".join(f"{key}:{value};" for key, value in variables.items())


def js_object(variables: dict) -> str:
    """Serialise variables for a JavaScript object literal."""
    parts = []
    for key, value in variables.items():
        rendered = f'"{value}"' if isinstance(value, str) else value
        parts.append(f'"{key}": {rendered}')
    return "{" + ", ".join(parts) + "}"


scene_divs = []
timeline_js = []
particle_divs = []

for index, scene in enumerate(SCENES):
    sid = scene["id"]
    start = scene["start"]
    dur = scene["dur"]
    motion = scene["motion"]
    amount = scene["amount"]

    from_vars, to_vars = motion_vars(motion, amount)

    particle_divs.append(
        f'      <div class="layer particle" data-start="{start}" data-duration="{dur}" '
        f'data-track-index="6" data-scene="{sid}">'
        f'<canvas class="pcanvas" width="1080" height="1920" data-pseed="{701 + index}"></canvas>'
        f"</div>"
    )

    scene_divs.append(f"""      <div class="layer plate" data-start="{start}" data-duration="{dur}" data-track-index="1" data-scene="{sid}">
        <img class="kb" id="{sid}-img" data-kb="{sid}" src="assets/img/{sid}.jpg" alt="" style="{css_string(from_vars)}" />
      </div>
      <div class="layer depth" data-start="{start}" data-duration="{dur}" data-track-index="2" data-scene="{sid}">
        <img class="kb-blur" src="assets/img/{sid}.jpg" alt="" />
      </div>
      <div class="layer vignette" data-start="{start}" data-duration="{dur}" data-track-index="4"></div>
      <div class="layer grain" data-start="{start}" data-duration="{dur}" data-track-index="5"></div>""")

    # camera tween on the image transform vars.
    # Select with an attribute selector, not "#<id>": ids here contain a hyphen and
    # GSAP's selector engine reads "#s01_courtyard-img" as "#s01_courtyard minus img",
    # which silently resolves to no target ("GSAP target not found").
    timeline_js.append(
        f'  tl.fromTo("[data-kb=\\"{sid}\\"]", {js_object(from_vars)}, '
        f'Object.assign({js_object(to_vars)}, {{duration: {dur}, ease: "none"}}), {start});'
    )
    timeline_js.append(
        f'  tl.fromTo("[data-kb=\\"{sid}\\"]", {{"--flicker": 0}}, '
        f'{{"--flicker": 1, duration: {dur}, ease: "sine.inOut"}}, {start});'
    )
    # a gentle light-breath so stills never read as frozen
    timeline_js.append(
        f'  tl.fromTo("[data-scene=\\"{sid}\\"] .depth", {{opacity: 0.30}}, '
        f'{{opacity: 0.46, duration: {dur / 2:.2f}, yoyo: true, repeat: 1, ease: "sine.inOut"}}, {start});'
    )

# ── overlays ──────────────────────────────────────────────────────────────
TITLE_LINES = ["NHÀ SƯ VÀ", "CHIẾC BÁT RỖNG"]
SUBTITLE = "Câu chuyện khiến ai cũng nhìn lại"
HOOK_TEXT = "Bạn đang chờ đến khi nào thì mới thấy mình đủ?"

overlay_divs = []
overlay_js = []

overlay_divs.append(f"""      <div class="layer overlay" data-start="0" data-duration="6.5" data-track-index="10">
        <div class="title-wrap">
          <div class="title-line t1" id="title-l1">{TITLE_LINES[0]}</div>
          <div class="title-line t2" id="title-l2">{TITLE_LINES[1]}</div>
          <div class="subtitle" id="subtitle">{SUBTITLE}</div>
        </div>
      </div>
      <div class="layer overlay" data-start="0.5" data-duration="6.0" data-track-index="11">
        <div class="hook" id="hook">{HOOK_TEXT}</div>
      </div>""")
overlay_js.append('  tl.fromTo("#title-l1", {scale: 0.82, opacity: 0}, {scale: 1, opacity: 1, duration: 0.25, ease: "back.out(2)"}, 0);')
overlay_js.append('  tl.fromTo("#title-l2", {scale: 0.82, opacity: 0}, {scale: 1, opacity: 1, duration: 0.25, ease: "back.out(2)"}, 0.15);')
overlay_js.append('  tl.fromTo("#subtitle", {opacity: 0, y: 18}, {opacity: 1, y: 0, duration: 0.35, ease: "power2.out"}, 0.35);')
overlay_js.append('  tl.to(["#title-l1", "#title-l2", "#subtitle"], {opacity: 0, scale: 0.96, duration: 0.4, ease: "power2.in"}, 5.6);')
overlay_js.append('  tl.fromTo("#hook", {opacity: 0}, {opacity: 1, duration: 0.35}, 0.5);')
overlay_js.append('  tl.to("#hook", {opacity: 0, duration: 0.4}, 5.8);')

SEASON_OVERLAYS = {
    "season_spring": ("MÙA XUÂN", 34.0),
    "season_rain": ("MÙA HẠ", 44.0),
    "season_autumn": ("MÙA THU", 51.0),
}
for key, (label, at) in SEASON_OVERLAYS.items():
    overlay_divs.append(
        f'      <div class="layer overlay" data-start="{at}" data-duration="3.2" data-track-index="12">'
        f'<div class="season" id="{key}">{label}</div></div>'
    )
    overlay_js.append(f'  tl.fromTo("#{key}", {{opacity: 0, scale: 0.9}}, {{opacity: 1, scale: 1, duration: 0.3, ease: "back.out(2)"}}, {at});')
    overlay_js.append(f'  tl.to("#{key}", {{opacity: 0, duration: 0.45}}, {at + 2.6});')

overlay_divs.append(
    '      <div class="layer overlay" data-start="66.0" data-duration="6.0" data-track-index="13">'
    '<div class="hero hero-700" id="hero700">700 CHIẾC BÁT<br />0 CHUYẾN ĐI</div></div>'
)
overlay_js.append('  tl.fromTo("#hero700", {opacity: 0, scale: 0.86}, {opacity: 1, scale: 1, duration: 0.3, ease: "back.out(2.2)"}, 66.0);')
overlay_js.append('  tl.to("#hero700", {opacity: 0, duration: 0.5}, 70.8);')

overlay_divs.append(
    '      <div class="layer overlay" data-start="80.2" data-duration="6.0" data-track-index="14">'
    '<div class="hero hero-lesson" id="heroLesson">ĐỦ LÀ MỘT QUYẾT ĐỊNH</div></div>'
)
overlay_js.append('  tl.fromTo("#heroLesson", {opacity: 0, scale: 0.86}, {opacity: 1, scale: 1, duration: 0.3, ease: "back.out(2.2)"}, 80.2);')
overlay_js.append('  tl.to("#heroLesson", {opacity: 0, duration: 0.5}, 84.5);')

overlay_divs.append(
    '      <div class="layer overlay" data-start="94.0" data-duration="2.0" data-track-index="15">'
    '<div class="cta" id="cta">HÀNH TRÌNH VẠN DẶM<br />BẮT ĐẦU TỪ MỘT BƯỚC CHÂN</div></div>'
)
overlay_js.append('  tl.fromTo("#cta", {opacity: 0, y: 22}, {opacity: 1, y: 0, duration: 0.5, ease: "power2.out"}, 94.1);')
overlay_js.append('  tl.to("#cta", {opacity: 1, duration: 1.0}, 95.0);')

# ── caption layer: one overlay per cue, with word-by-word amber highlight ──
CAPTION_CUES = []
for block_id, seconds, block_start in NARRATION_LAYOUT:
    cues_path = NARRATION / f"{block_id}.cues.json"
    if not cues_path.exists():
        print(f"  note: no cues for {block_id}")
        continue
    data = json.loads(cues_path.read_text(encoding="utf-8"))
    audio_seconds = data.get("audio_seconds") or seconds
    for cue in data["cues"]:
        cue_start = block_start + cue["start"]
        # Never let a cue run past the narration block and collide with the next one.
        cue_end = min(block_start + cue["end"], block_start + audio_seconds)
        if cue_end - cue_start < 0.2:
            continue
        CAPTION_CUES.append({
            "block": block_id,
            "start": frame_snap(max(cue_start, 0.0)),
            "end": frame_snap(cue_end),
            "lines": cue["lines"],
        })

caption_divs = []
caption_js = []
for cap_index, cue in enumerate(CAPTION_CUES):
    cue_id = f"cap{cap_index}"
    dur = round(cue["end"] - cue["start"], 4)
    if dur <= 0:
        continue
    lines_html = []
    word_index = 0
    for line in cue["lines"]:
        spans = []
        for word in line:
            wid = f"{cue_id}w{word_index}"
            spans.append(f'<span class="cw" id="{wid}">{word["word"]}</span>')
            word_index += 1
        lines_html.append('<div class="cline">' + " ".join(spans) + "</div>")

    caption_divs.append(
        f'      <div class="layer overlay caption-layer" data-start="{cue["start"]}" '
        f'data-duration="{dur}" data-track-index="16" data-caption="{cue_id}">'
        f'<div class="caption">{"".join(lines_html)}</div></div>'
    )
    caption_js.append(
        f'  tl.set("[data-caption=\\"{cue_id}\\"]", {{autoAlpha: 1}}, {cue["start"]});'
    )
    caption_js.append(
        f'  tl.set("[data-caption=\\"{cue_id}\\"]", {{autoAlpha: 0}}, {cue["end"]});'
    )
    # word-by-word highlight: each word turns amber for its own duration
    for i, word in enumerate(w for line in cue["lines"] for w in line):
        w_start = frame_snap(cue["start"] + word["start"] - cue["lines"][0][0]["start"])
        w_end = frame_snap(min(cue["start"] + word["end"] - cue["lines"][0][0]["start"], cue["end"]))
        if w_end <= w_start:
            continue
        caption_js.append(f'  tl.set("#{cue_id}w{i}", {{color: "#F5C518"}}, {w_start});')
        caption_js.append(f'  tl.set("#{cue_id}w{i}", {{color: "#FFFFFF"}}, {w_end});')

print(f"captions: {len(caption_divs)} cues")

# ── audio elements (direct children of root) ──────────────────────────────
audio_divs = []
audio_js = []
for block_id, seconds, start in NARRATION_LAYOUT:
    start = frame_snap(start)
    audio_divs.append(
        f'      <audio id="narr-{block_id}" src="assets/audio/{block_id}.mp3" '
        f'data-start="{start}" data-duration="{frame_snap(seconds)}" '
        f'data-track-index="20" preload="auto"></audio>'
    )
    # narration level: primary element
    audio_js.append(
        f'  tl.fromTo("#narr-{block_id}", {{volume: 0}}, {{volume: 1, duration: 0.12, ease: "none"}}, {start});'
    )
    audio_js.append(
        f'  tl.to("#narr-{block_id}", {{volume: 0, duration: 0.25, ease: "none"}}, {frame_snap(start + seconds - 0.2)});'
    )

# music: present throughout, ducked to -24 dB under narration by ducking the bed
audio_divs.append(
    f'      <audio id="music" src="assets/audio/bed.mp3" data-start="0" '
    f'data-duration="{TOTAL}" data-track-index="21" preload="auto"></audio>'
)
MUSIC_VOL = 0.10          # about -20 dB, sits under the narration
MUSIC_DUCK = 0.05         # about -26 dB while narration is speaking
audio_js.append(f'  tl.set("#music", {{volume: {MUSIC_VOL}}}, 0);')
for block_id, seconds, start in NARRATION_LAYOUT:
    s = frame_snap(start)
    e = frame_snap(start + seconds)
    audio_js.append(f'  tl.to("#music", {{volume: {MUSIC_DUCK}, duration: 0.3, ease: "none"}}, {s});')
    audio_js.append(f'  tl.to("#music", {{volume: {MUSIC_VOL}, duration: 0.6, ease: "none"}}, {e});')
# the deliberate silence after the lesson line: music drops out entirely
audio_js.append(f'  tl.to("#music", {{volume: 0, duration: 0.4, ease: "none"}}, {frame_snap(78.4)});')
audio_js.append(f'  tl.to("#music", {{volume: {MUSIC_VOL}, duration: 1.0, ease: "none"}}, {frame_snap(79.9)});')
# fade the bed out at the end
audio_js.append(f'  tl.to("#music", {{volume: 0, duration: 1.2, ease: "none"}}, {frame_snap(94.6)});')

# ── particle renderer: deterministic, seek-safe ──────────────────────────
PARTICLE_JS = """
  // Deterministic particle fields. All positions derive from the scene seed and
  // the frame number, so any seek reproduces the same frame.
  function mulberry32(a) {
    return function () {
      a |= 0; a = (a + 0x6d2b79f5) | 0;
      var t = Math.imul(a ^ (a >>> 15), 1 | a);
      t = (t + Math.imul(t ^ (t >>> 7), 61 | t)) ^ t;
      return ((t ^ (t >>> 14)) >>> 0) / 4294967296;
    };
  }

  function drawParticles(scene, t) {
    var canvas = scene.querySelector("canvas.pcanvas");
    if (!canvas) return;
    var ctx = canvas.getContext("2d");
    var seed = parseInt(canvas.dataset.pseed, 10) || 1;
    var W = canvas.width, H = canvas.height;
    ctx.clearRect(0, 0, W, H);

    // leaves
    ctx.globalCompositeOperation = "source-over";
    for (var i = 0; i < 34; i++) {
      var r = mulberry32(seed * 977 + i);
      var x0 = r() * W, speed = 26 + r() * 52, drift = (r() - 0.5) * 46;
      var phase = r() * Math.PI * 2, size = 7 + r() * 13, spin = (r() - 0.5) * 1.6;
      var y = ((r() * H + t * speed) % (H + 160)) - 80;
      var x = x0 + Math.sin(t * 0.45 + phase) * drift;
      var rot = t * spin + phase;
      ctx.save();
      ctx.translate(x, y);
      ctx.rotate(rot);
      ctx.globalAlpha = 0.30 + 0.28 * Math.abs(Math.sin(t * 0.6 + phase));
      ctx.fillStyle = i % 3 === 0 ? "#e8b64a" : "#c98b2e";
      ctx.beginPath();
      ctx.ellipse(0, 0, size, size * 0.42, 0, 0, Math.PI * 2);
      ctx.fill();
      ctx.restore();
    }

    // drifting dust motes in the light
    for (var j = 0; j < 46; j++) {
      var rd = mulberry32(seed * 613 + j);
      var dx = rd() * W, dy0 = rd() * H, ds = 8 + rd() * 20;
      var ddrift = (rd() - 0.5) * 26;
      var dy = (dy0 - t * ds + H * 4) % H;
      var dxn = dx + Math.sin(t * 0.3 + j) * ddrift;
      ctx.globalAlpha = 0.10 + 0.16 * Math.abs(Math.sin(t * 0.8 + j * 0.7));
      ctx.fillStyle = "#ffe9b0";
      ctx.beginPath();
      ctx.arc(dxn, dy, 1.1 + (j % 3) * 0.7, 0, Math.PI * 2);
      ctx.fill();
    }

    // incense smoke, bottom-anchored, slow upward curl
    ctx.globalAlpha = 1;
    for (var k = 0; k < 5; k++) {
      var rs = mulberry32(seed * 331 + k);
      var baseX = W * (0.34 + rs() * 0.34);
      var rise = 54 + rs() * 40;
      var sy = H - (((t * rise + rs() * H) % (H * 0.85)));
      var sx = baseX + Math.sin(t * 0.35 + k * 1.7) * (30 + k * 10);
      var rad = 90 + ((H - sy) / H) * 230;
      var grad = ctx.createRadialGradient(sx, sy, 0, sx, sy, rad);
      grad.addColorStop(0, "rgba(255,244,222," + (0.055 - k * 0.008) + ")");
      grad.addColorStop(1, "rgba(255,244,222,0)");
      ctx.fillStyle = grad;
      ctx.beginPath();
      ctx.arc(sx, sy, rad, 0, Math.PI * 2);
      ctx.fill();
    }
  }
"""

# ── assemble the file ─────────────────────────────────────────────────────
html = f"""<!doctype html>
<html lang="vi" data-resolution="portrait">
  <head>
    <meta charset="UTF-8" />
    <meta name="viewport" content="width=1080, height=1920" />
    <title>Nhà Sư Và Chiếc Bát Rỗng</title>
    <script src="https://cdn.jsdelivr.net/npm/gsap@3.14.2/dist/gsap.min.js"></script>
    <style>
      * {{ margin: 0; padding: 0; box-sizing: border-box; }}
      html, body {{
        margin: 0; width: 1080px; height: 1920px;
        overflow: hidden; background: #14100b;
      }}
      #root {{
        position: relative;
        width: 1080px; height: 1920px;
        overflow: hidden;
        background: #14100b;
        font-family: Inter, "Segoe UI", system-ui, sans-serif;
      }}
      .layer {{ position: absolute; inset: 0; }}
      .plate, .depth {{ overflow: hidden; }}
      .plate img, .depth img {{
        position: absolute; inset: 0;
        width: 100%; height: 100%;
        object-fit: cover;
        will-change: transform;
      }}
      .kb {{
        transform: translate(var(--px, 0), var(--py, 0))
                   scale(var(--sx, 1), var(--sy, 1));
        transform-origin: 50% 45%;
        filter: brightness(calc(0.94 + var(--flicker, 0) * 0.10))
                saturate(1.04);
      }}
      .kb-blur {{
        transform: scale(1.2);
        transform-origin: 50% 45%;
        filter: blur(26px) brightness(0.82) saturate(1.1);
      }}
      .depth {{ mix-blend-mode: soft-light; }}
      .vignette {{
        background:
          radial-gradient(115% 78% at 50% 42%,
            rgba(0,0,0,0) 44%, rgba(20,12,4,0.34) 76%, rgba(12,7,2,0.72) 100%);
        mix-blend-mode: multiply;
      }}
      .grain {{
        opacity: 0.16;
        mix-blend-mode: overlay;
        background-image:
          repeating-conic-gradient(rgba(255,255,255,0.055) 0% 25%, rgba(0,0,0,0.055) 0% 50%);
        background-size: 3px 3px;
        filter: blur(0.4px);
      }}
      .particle {{ pointer-events: none; }}
      .particle canvas {{ width: 100%; height: 100%; display: block; }}
      .overlay {{
        display: grid; place-items: center;
        pointer-events: none;
      }}
      /* Captions sit inside the 900x1400 safe zone, above platform UI. */
      .caption-layer {{
        align-items: end;
        justify-items: center;
        padding-bottom: 470px;
        visibility: hidden;
      }}
      .caption {{
        max-width: 900px;
        padding: 16px 26px;
        border-radius: 10px;
        background: rgba(8, 5, 2, 0.42);
        text-align: center;
      }}
      .cline {{
        font-size: 48px;
        font-weight: 700;
        line-height: 1.26;
        letter-spacing: 0.005em;
        white-space: nowrap;
        -webkit-text-stroke: 3px #140d04;
        paint-order: stroke fill;
        text-shadow: 0 3px 14px rgba(0,0,0,0.85);
      }}
      .cline + .cline {{ margin-top: 6px; }}
      .cw {{ color: #ffffff; }}
      .title-wrap {{
        position: absolute; top: 150px; left: 0; right: 0;
        display: grid; justify-items: center; gap: 6px;
      }}
      .title-line {{
        font-size: 78px; font-weight: 800; letter-spacing: 0.02em;
        line-height: 1.04; text-align: center; text-transform: uppercase;
        -webkit-text-stroke: 3px #140d04;
        paint-order: stroke fill;
        text-shadow: 0 6px 22px rgba(0,0,0,0.55);
      }}
      .t1 {{ color: #f5c518; }}
      .t2 {{ color: #e08a2b; }}
      .subtitle {{
        margin-top: 10px;
        font-size: 46px; font-weight: 600; color: #f2ead9;
        letter-spacing: 0.01em; text-align: center;
        -webkit-text-stroke: 3px #140d04; paint-order: stroke fill;
      }}
      .hook {{
        position: absolute; top: 430px; left: 70px; right: 70px;
        padding: 22px 8px;
        text-align: center;
        font-size: 58px; font-weight: 700; line-height: 1.28; color: #ffffff;
        -webkit-text-stroke: 3px #140d04; paint-order: stroke fill;
        text-shadow: 0 4px 18px rgba(0,0,0,0.85), 0 2px 6px rgba(0,0,0,0.95);
        background: radial-gradient(72% 58% at 50% 50%,
          rgba(10,6,2,0.34) 0%, rgba(10,6,2,0.16) 52%, rgba(10,6,2,0) 100%);
      }}
      .season {{
        font-size: 66px; font-weight: 800; letter-spacing: 0.14em;
        color: #e08a2b; text-transform: uppercase;
        -webkit-text-stroke: 3px #140d04; paint-order: stroke fill;
        text-shadow: 0 6px 22px rgba(0,0,0,0.55);
      }}
      .hero {{
        text-align: center;
        font-size: 68px; font-weight: 800; line-height: 1.16; color: #f5c518;
        text-transform: uppercase; letter-spacing: 0.02em;
        -webkit-text-stroke: 4px #140d04; paint-order: stroke fill;
        text-shadow: 0 8px 26px rgba(0,0,0,0.6);
      }}
      .hero-lesson {{ font-size: 64px; }}
      .cta {{
        position: absolute; top: 150px; left: 62px; right: 62px;
        padding: 26px 10px;
        text-align: center;
        font-size: 52px; font-weight: 700; line-height: 1.3; color: #ffffff;
        text-transform: uppercase; letter-spacing: 0.03em;
        -webkit-text-stroke: 3px #140d04; paint-order: stroke fill;
        text-shadow: 0 4px 18px rgba(0,0,0,0.85), 0 2px 6px rgba(0,0,0,0.95);
        background: radial-gradient(72% 58% at 50% 50%,
          rgba(10,6,2,0.34) 0%, rgba(10,6,2,0.16) 52%, rgba(10,6,2,0) 100%);
      }}
    </style>
  </head>
  <body>
    <div
      id="root"
      data-composition-id="main"
      data-start="0"
      data-duration="{TOTAL}"
      data-width="1080"
      data-height="1920"
    >
{chr(10).join(scene_divs)}
{chr(10).join(particle_divs)}
{chr(10).join(overlay_divs)}
{chr(10).join(caption_divs)}
{chr(10).join(audio_divs)}
    </div>
    <script>
{{
  window.__timelines = window.__timelines || {{}};
  const tl = gsap.timeline({{ paused: true }});
{PARTICLE_JS}
  // Scene visibility + particle drawing, driven by the timeline so every seek
  // reproduces the same frame.
  const scenes = Array.from(document.querySelectorAll(".particle"));
  const timelineSeconds = {TOTAL};
  const FPS = {FPS};

  function applyFrame(seconds) {{
    scenes.forEach(function (scene) {{
      const start = parseFloat(scene.dataset.start);
      const dur = parseFloat(scene.dataset.duration);
      const local = seconds - start;
      const active = local >= 0 && local < dur;
      scene.style.opacity = active ? "1" : "0";
      if (active) drawParticles(scene, local);
    }});
  }}

  tl.eventCallback("onUpdate", function () {{
    applyFrame(tl.time());
  }});

{chr(10).join(timeline_js)}
{chr(10).join(overlay_js)}
{chr(10).join(caption_js)}
{chr(10).join(audio_js)}
  window.__timelines["main"] = tl;
  tl.seek(0);
  applyFrame(0);
}}
    </script>
  </body>
</html>
"""

(HF / "index.html").write_text(html, encoding="utf-8")
print(f"wrote {HF / 'index.html'}  ({len(html)} bytes)")
print(f"scenes: {len(SCENES)}  overlays: {len(overlay_divs)}  audio: {len(audio_divs)}")
