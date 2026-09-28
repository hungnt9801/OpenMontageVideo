# Hướng dẫn cài đặt & tạo video đầu tiên — OpenMontage

> **Tài liệu này viết cho ai?** Người mới clone repo về máy và muốn (1) cài đặt cho chạy được, (2) tạo ra một video thật càng nhanh càng tốt.
>
> **Nguồn của tài liệu:** đọc trực tiếp source code trong repo này (`Makefile`, `render_demo.py`, `lib/`, `tools/`, `pipeline_defs/`, `tests/qa/`, `.github/workflows/ci.yml`). Mỗi mục quan trọng đều kèm con trỏ `file:dòng` để bạn tự tra cứu.
>
> **Mức độ kiểm chứng:** các lệnh dưới đây lấy nguyên văn từ source. **Kịch bản 1 đã được chạy thật trên đúng máy này và xác nhận** (ra file MP4 4,09 MB). Kịch bản 2 thì chưa — xem mục [12.3](#123-giới-hạn-kiểm-chứng-của-tài-liệu-này).

---

## 1. Tóm tắt nhanh (TL;DR)

Có **3 đường đi** để tạo video, xếp theo độ khó tăng dần:

| # | Kịch bản | Cần gì | Ra cái gì | Thời gian | Chi phí |
|---|----------|--------|-----------|-----------|---------|
| **1** | Render demo dựng sẵn (Remotion) | Node.js + npm | `projects/demos/renders/*.mp4` | ~2 phút cài + vài phút render | **$0** ✅ *đã chạy thật* |
| **2** | Smoke test toàn pipeline 8 stage | Python + FFmpeg | `tests/qa/output/e2e_final_output.mp4` | 1–2 phút | **$0** ✅ *đã chạy thật: 38 passed, 0 failed* |
| **3** | Nhờ AI agent sản xuất video thật | Python + FFmpeg + Node + một AI coding assistant | `projects/<tên>/renders/final.mp4` | 10–20 phút | **$0** (zero-key) → $1–3 (có API key) ✅ *đã chạy thật: xem [9.6](#96-ví-dụ-đã-chạy-thật-đầu-cuối-zero-key)* |

**Yêu cầu tối thiểu để bắt đầu ngay:** Python 3.10+, FFmpeg, Node.js 18+ (Node ≥ 22 nếu muốn dùng HyperFrames).

Nếu chỉ muốn thấy một video MP4 xuất hiện càng sớm càng tốt → nhảy tới [mục 7](#7-kịch-bản-1--video-đầu-tiên-không-cần-api-key).
Nếu muốn hiểu mình đang cài cái gì → đọc [mục 2](#2-openmontage-hoạt-động-thế-nào-review-kiến-trúc).

---

## 2. OpenMontage hoạt động thế nào (review kiến trúc)

### 2.1 Nguyên tắc cốt lõi: agent-first, không có orchestrator Python

Đây là điểm khác biệt lớn nhất so với các "AI video tool" khác. Trong OpenMontage:

```
Agent đọc pipeline manifest (YAML)   → biết TIẾN TRÌNH gồm những stage nào
Agent đọc stage director skill (MD)  → biết CÁCH làm từng stage
Agent gọi tool (Python BaseTool)     → tay chân: gọi API, render, mix audio
Agent tự review (meta skill)         → chấm chất lượng theo review_focus
Agent ghi checkpoint (JSON)          → lưu trạng thái, resumable
Agent trình bày cho người duyệt       → bạn giữ quyền quyết định
```

**Python chỉ làm 2 việc: cung cấp tool + lưu trạng thái.** Không có Python orchestrator, không có Python reviewer, không có Python handler cho từng stage. Xem `PROJECT_CONTEXT.md:19`.

Hệ quả thực tế khi bạn dùng repo:

- Muốn đổi hành vi của pipeline → sửa file YAML/Markdown, **không phải sửa logic Python**.
- Muốn biết hệ thống có tool gì → **hỏi registry**, đừng đọc doc cũ (xem [mục 6](#6-preflight--xem-bạn-thực-sự-có-gì)).
- Chất lượng video phụ thuộc vào việc agent có đọc skill hay không. Nếu bạn tự viết script gọi tool trực tiếp, bạn đang bỏ qua toàn bộ "chất xám" của hệ thống.

### 2.2 Ba lớp tri thức

| Lớp | Nằm ở đâu | Trả lời câu hỏi |
|-----|-----------|-----------------|
| **1** | `tools/`, `pipeline_defs/` | "Có những gì?" — tool khả dụng, runtime, chi phí, pipeline |
| **2** | `skills/` | "OpenMontage muốn dùng nó thế nào?" — quy ước, chất lượng, quy trình |
| **3** | `.agents/skills/` | "Công nghệ đó hoạt động ra sao?" — kiến thức vendor/API gốc |

Mỗi tool khai báo `agent_skills[]` để trỏ từ lớp 1 → lớp 3. Trích `PROJECT_CONTEXT.md:35-41`.

### 2.3 Vòng đời pipeline (8 stage)

Pipeline `animated-explainer` (`pipeline_defs/animated-explainer.yaml`) chạy tuần tự:

```
research → proposal → script → scene_plan → assets → edit → compose → publish
   │          │          │         │           │        │        │        │
   │          │          │         │           │        │        │        └─ publish_log
   │          │          │         │           │        │        └─ render_report + final_review
   │          │          │         │           │        └─ edit_decisions
   │          │          │         │           └─ asset_manifest
   │          │          │         └─ scene_plan
   │          │          └─ script
   │          └─ proposal_packet + decision_log
   └─ research_brief
```

Mỗi stage:
1. **Sinh đúng một artifact chuẩn** (cột phải ở sơ đồ trên), validate bằng JSON Schema trong `schemas/artifacts/`.
2. **Ghi checkpoint** `projects/<id>/checkpoint_<stage>.json`.
3. **Có thể là "cổng" (gate)** — stage gated bắt buộc `human_approved=True` mới được ghi `completed`, nếu không `lib/checkpoint.py` ném lỗi GATE VIOLATION (`lib/checkpoint.py:251`).

Các cổng duyệt mặc định của `animated-explainer`: `proposal`, `script`, `scene_plan`, `assets`, `publish` (`human_approval_default: true`). Riêng `research`, `edit`, `compose` chạy tự động.

Ngoài ra còn **một cổng thứ hai ít được biết**: `_enforce_stage_prerequisites` (`lib/checkpoint.py:284-346`). Khi ghi `completed`/`awaiting_human`, **mọi stage trước đó** trong manifest phải tồn tại, hợp lệ, đúng `project_id`/`pipeline_type`, có `status == "completed"`, và nếu là stage gated thì phải có `human_approved`. Vi phạm → lỗi `PREREQUISITE VIOLATION`. Cổng này **không được mô tả** trong `AGENT_GUIDE.md` lẫn `PROJECT_CONTEXT.md` — nếu bạn tự viết script ghi checkpoint, đây là lỗi rất dễ gặp.

Giá trị `status` hợp lệ **chỉ có 4**: `completed`, `failed`, `awaiting_human`, `in_progress` (`schemas/checkpoints/checkpoint.schema.json:17`). Không có `pending`.

> **Điều này nghĩa là gì với bạn?** Ở kịch bản 3, agent sẽ **dừng lại và chờ bạn duyệt** ở các stage trên. Đây là thiết kế có chủ đích, không phải lỗi. Đừng tắt nó nếu bạn chưa quen.

### 2.4 Cây thư mục

```
OpenMontageVideo/
├── AGENT_GUIDE.md          # HỢP ĐỒNG vận hành cho AI agent — đọc trước tiên
├── PROJECT_CONTEXT.md      # Kiến trúc + quy ước
├── README.md               # Giới thiệu, quickstart gốc
├── config.yaml             # Cấu hình toàn cục (llm, budget, output, paths)
├── .env.example            # Mẫu biến môi trường → copy thành .env
├── Makefile                # Lệnh setup/test/demo (bash)
├── render_demo.py          # Render 3 demo Remotion zero-key
├── requirements*.txt       # Phụ thuộc Python (core / dev / gpu / local)
│
├── tools/                  # 167 file — "tay chân" của agent
│   ├── base_tool.py        #   BaseTool / ToolContract
│   ├── tool_registry.py    #   Khám phá & báo cáo năng lực
│   ├── cost_tracker.py     #   Quản trị ngân sách
│   ├── video/              #   video_compose, video_stitch, 20+ provider sinh video
│   ├── audio/              #   piper_tts, tts_selector, audio_mixer, music_gen, ...
│   ├── graphics/           #   image_selector, diagram_gen, threejs_world, ...
│   ├── analysis/           #   transcriber, scene_detect, frame_sampler, ...
│   └── subtitle/           #   subtitle_gen
│
├── pipeline_defs/          # 13 manifest YAML khai báo từng pipeline
├── skills/                 # Lớp 2 — director skill cho từng stage
│   ├── pipelines/          #   explainer/, cinematic/, character-animation/, ...
│   ├── meta/               #   reviewer, checkpoint-protocol, onboarding, ...
│   └── core/, creative/
├── .agents/skills/         # Lớp 3 — kiến thức công nghệ gốc (GSAP, Remotion, ...)
├── schemas/                # JSON Schema cho artifact / checkpoint / pipeline / playbook
├── styles/                 # 5 style playbook YAML (clean-professional, ...)
├── remotion-composer/      # Engine dựng video bằng React/Remotion
├── backlot/                # Bảng theo dõi tiến trình sản xuất (local server)
├── lib/                    # Hạ tầng: checkpoint, config, pipeline_loader, env_loader
├── scripts/                # Script tiện ích (simulate run, scaffold, smoke test)
├── tests/                  # Contract test + QA test + eval harness
│   └── qa/                 #   test_01..test_09 — chạy được, nhiều test $0
└── docs/                   # Tài liệu (bạn đang đọc)
```

### 2.5 Trạng thái được lưu ở đâu

Mọi thứ về một lần sản xuất nằm trong `projects/<project-id>/`:

```
projects/<project-id>/
├── project.json            # Marker: id, title, pipeline_type, style_playbook
├── checkpoint_<stage>.json # Trạng thái từng stage (+ cost_snapshot, artifacts)
├── history/                # Checkpoint cũ khi stage bị chạy lại (không mất lịch sử)
├── events.jsonl            # Log hoạt động (do BaseTool ghi) → Backlot đọc
├── decision_log.json       # Nhật ký quyết định (merge từ artifact decision_log)
├── artifacts/              # JSON artifact từng stage
├── assets/
│   ├── images/  video/  audio/  music/
│   └── subtitles.srt
└── renders/final.mp4       # SẢN PHẨM CUỐI
```

> **Đừng nhầm thứ tự xuất hiện.** `init_project()` chỉ tạo **6 thư mục con** (`artifacts/`, `assets/images|video|audio|music`, `renders/`) và `project.json` (`lib/checkpoint.py:216-248`). Các file `checkpoint_*.json`, `history/`, `events.jsonl`, `decision_log.json`, `assets/subtitles.srt` **xuất hiện dần trong quá trình chạy** — sau khi cài đặt, `projects/` thậm chí chưa tồn tại.

Thư mục `projects/` được gitignore (`.gitignore:29`) — mọi asset đều tái tạo được.

---

## 3. Yêu cầu hệ thống

| Thành phần | Bắt buộc? | Phiên bản | Dùng để làm gì | Ghi chú |
|------------|-----------|-----------|----------------|---------|
| **Python** | ✅ Bắt buộc | **3.10+** | Chạy toàn bộ tool + registry + checkpoint | Repo pin `3.10` (`.python-version`), CI dùng `3.11` (`.github/workflows/ci.yml:30`) |
| **FFmpeg** (+ `ffprobe`) | ✅ Bắt buộc | Bản mới bất kỳ | Cắt/ghép/encode/mix/nghiệm thu video | `video_compose` khai báo `dependencies = ["cmd:ffmpeg"]` (`tools/video/video_compose.py:68`) |
| **Node.js** | ✅ Cho kịch bản 1 & 3 | **≥ 18** (Remotion)<br>**≥ 22** (HyperFrames) | Dựng video bằng React (Remotion) hoặc HTML/GSAP (HyperFrames) | README ghi "18+", nhưng HyperFrames cần ≥ 22 — xem [12.2](#122-các-điểm-chưa-nhất-quán-phát-hiện-khi-review) |
| **npm / npx** | ✅ Đi kèm Node | — | Cài & gọi Remotion/HyperFrames | |
| **Git** | Khuyến nghị | — | Clone repo | |
| **GNU Make** | ⬜ Tùy chọn | — | Chạy `make setup`, `make demo`, `make test` | **Windows không có sẵn.** Makefile dùng cú pháp bash → xem [4.1](#41-windows-powershell--khuyến-nghị) |
| **GPU NVIDIA** | ⬜ Tùy chọn | ≥ 6 GB VRAM | Sinh video local miễn phí (Wan, Hunyuan, LTX…) | `requirements-gpu.txt` |
| **API key** | ⬜ Tùy chọn | — | Chất lượng cao hơn (ảnh AI, giọng cloud, nhạc) | **Không cần key vẫn ra video** |

### 3.1 "Zero-key" thực tế cần những gì

Nói "không cần API key" là đúng, nhưng **không có nghĩa là không cần cài gì**. Danh sách trung thực để sản xuất video zero-key trên một máy Windows sạch:

1. **FFmpeg + ffprobe** — không có thì gần như toàn bộ `video_post`, `audio_processing`, `analysis` đều UNAVAILABLE.
2. **Python 3.10+** — để chạy registry, checkpoint, và mọi tool.
3. **Node ≥ 22 + `npm install` trong `remotion-composer`** — **đây là chỗ dễ bị bỏ sót nhất.** Không có `node_modules` thì Remotion không khả dụng, và vì `_compose` từ chối ảnh tĩnh, bạn **mất hoàn toàn** khả năng dựng video từ ảnh.
4. **Binary `piper` trên PATH** — nếu không, không có thuyết minh offline (vẫn có thể dùng TTS cloud nếu có key).

Chỉ riêng Python + `subtitle_gen` là đã chạy được (**tool duy nhất trong repo không có phụ thuộc nào** — pure Python, không FFmpeg, không key). Đó là bài kiểm tra "Python đã cài đúng chưa" rẻ nhất.

---

## 4. Cài đặt

### 4.1 Windows (PowerShell) — khuyến nghị

> **Vì sao không dùng `make setup`?** `Makefile:3-4` dùng `command -v`, `$(shell ...)`, `for dir in ...; do` — đây là cú pháp bash. Trên PowerShell mặc định sẽ báo `make : The term 'make' is not recognized`. Bạn có 2 lựa chọn: chạy `make setup` trong **Git Bash / WSL**, hoặc dùng chuỗi lệnh PowerShell tương đương dưới đây (khuyến nghị, vì kiểm soát được từng bước).

```powershell
# ── Bước 0: lấy source ────────────────────────────────────────────
git clone https://github.com/hungnt9801/OpenMontageVideo.git
cd OpenMontageVideo

# ── Bước 1: môi trường ảo Python ─────────────────────────────────
py -3.10 -m venv .venv
.\.venv\Scripts\Activate.ps1
# Nếu PowerShell chặn script, chạy 1 lần cho phiên hiện tại:
#   Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass

# ── Bước 2: thư viện Python lõi ──────────────────────────────────
python -m pip install --upgrade pip
python -m pip install -r requirements.txt

# ── Bước 3: engine dựng video Remotion ───────────────────────────
cd remotion-composer
npm install
cd ..

# ── Bước 4: TTS offline miễn phí (Piper) ─────────────────────────
python -m pip install piper-tts

# ── Bước 5: file cấu hình ────────────────────────────────────────
Copy-Item .env.example .env
```

Nếu `npm install` báo `ERR_INVALID_ARG_TYPE` (lỗi đã biết trên Windows):

```powershell
cd remotion-composer
npx --yes npm install
cd ..
```

Kiểm tra Piper đã sẵn sàng chưa (tool cần **lệnh** `piper`, không chỉ gói Python):

```powershell
piper --help        # nếu "not recognized" thì binary chưa vào PATH — xem ghi chú ở mục 5
```

**Làm nóng cache HyperFrames** (tùy chọn — tránh chờ 30–60s ở lần render đầu):

```powershell
npx --yes hyperframes --version
```

### 4.2 macOS / Linux

```bash
git clone https://github.com/hungnt9801/OpenMontageVideo.git
cd OpenMontageVideo
make setup          # venv + pip + npm install + piper-tts + warm cache + tạo .env
```

`make setup` thực hiện lần lượt (`Makefile:54-76`):

1. Tạo `.venv` (ưu tiên dùng venv/conda đang active, hoặc `uv` nếu có).
2. `pip install -r requirements.txt`.
3. `cd remotion-composer && npm install`.
4. `pip install piper-tts` (nếu lỗi thì bỏ qua, dùng TTS cloud).
5. Warm cache HyperFrames qua `npx --yes hyperframes --version`.
6. Copy `.env.example` → `.env` nếu chưa có.
7. In ra `HyperFrames runtime_available=...` để bạn biết runtime đã sẵn sàng chưa.

Không có `make`:

```bash
python3 -m venv .venv && source .venv/bin/activate
python -m pip install -r requirements.txt
(cd remotion-composer && npm install)
python -m pip install piper-tts
cp .env.example .env
```

### 4.3 Cài FFmpeg

**Windows:**

```powershell
winget install --id Gyan.FFmpeg -e
# hoặc nếu bạn dùng Chocolatey:
# choco install ffmpeg -y
```

**macOS:** `brew install ffmpeg`
**Ubuntu/Debian:** `sudo apt update && sudo apt install -y ffmpeg`

Mở **terminal mới** rồi kiểm tra:

```powershell
ffmpeg -version
ffprobe -version
```

> ⚠️ **Quan trọng:** `ffprobe` phải có cùng chỗ với `ffmpeg`. Hệ thống dùng `ffprobe` để nghiệm thu video sau khi render (kiểm tra độ phân giải, fps, codec, sự tồn tại của track audio).
>
> Đáng chú ý: `video_compose` chỉ khai báo `cmd:ffmpeg`, **không** khai báo `ffprobe` (`tools/video/video_compose.py:68`). Nếu thiếu `ffprobe`, nó **không báo lỗi** — nó lặng lẽ cho rằng video không có audio và tự ghép một track im lặng, đồng thời ghi vào bước nghiệm thu `"ffprobe not found — cannot validate output"`. Đây là kiểu hỏng im lặng dễ bị bỏ qua, nên hãy kiểm tra `ffprobe -version` trước khi sản xuất thật.

### 4.4 Cài thêm gói "cục bộ" (`requirements-local.txt`)

Repo này có một file **bổ sung cục bộ** mà `make setup` **không** cài:

```powershell
python -m pip install -r requirements-local.txt
```

File này (`requirements-local.txt:1-13`) giải thích rõ nó bù 2 phụ thuộc mà repo upstream thiếu:

| Gói | Cần cho | Hậu quả nếu thiếu |
|-----|---------|-------------------|
| `faster-whisper` | `tools/analysis/transcriber.py` — đường STT mặc định | Không sinh được subtitle / không soát được nội dung audio |
| `playwright` | `tools/character/character_animation.py`, các script `scripts/backlot_*.py`, `tests/backlot/test_ui_bug_bash.py` | Pipeline `character-animation` và các script chụp ảnh Backlot không chạy |

Nếu cài `playwright`, **luôn cài kèm browser**:

```powershell
python -m playwright install chromium
```

### 4.5 GPU (tùy chọn)

```powershell
python -m pip install -r requirements-gpu.txt
python -m pip install diffusers transformers accelerate
```

Rồi thêm vào `.env`:

```env
VIDEO_GEN_LOCAL_ENABLED=true
VIDEO_GEN_LOCAL_MODEL=wan2.2-ti2v-5b
```

Các model local và VRAM tương ứng (`docs/PROVIDERS.md:1264-1270`): `wan2.1-1.3b` (6 GB), `ltx2-local` (8 GB), `cogvideo-5b` (10 GB), `hunyuan-1.5` (12 GB), `wan2.2-ti2v-5b` (12 GB), `wan2.1-14b` (24 GB).

### 4.6 Kiểm tra sau khi cài

```powershell
python --version                 # 3.10+
ffmpeg -version                  # có phiên bản
node --version                   # >= 18 (>= 22 nếu dùng HyperFrames)
npm --version

# Registry nhận diện được tool?
python -c "from tools.tool_registry import registry; import json; registry.discover(); print(json.dumps(registry.provider_menu_summary(), indent=2))"
```

Lệnh cuối là **preflight** — chi tiết ở mục sau.

---

## 5. Cấu hình (`.env`)

**`.env` là tùy chọn, không bắt buộc.** `lib/env_loader.py:15-21` chỉ nạp file nếu nó tồn tại và **im lặng bỏ qua** nếu không có. Nghĩa là bạn có thể chạy kịch bản 1 và 2 ngay mà không cần tạo `.env`.

Cấu trúc `.env`:

```powershell
Copy-Item .env.example .env
notepad .env
```

**Đường zero-key (mặc định):** để trống hết. Bạn vẫn có:

| Năng lực | Tool miễn phí | Ghi chú |
|----------|---------------|---------|
| Thuyết minh | `piper_tts` | Offline. Cần **binary `piper`** trên PATH, không chỉ gói pip — xem cảnh báo bên dưới |
| Footage thật | `direct_clip_search` + các nguồn trong `tools/video/stock_sources/` | Archive.org, NASA, Wikimedia, LoC, NARA, Pond5 PD, Coverr, Mixkit, Dareful, JAXA, ESA, NOAA — **không cần key** |
| Nhạc nền | `music_library` | Quét thư mục, không phụ thuộc gì. Thả file `.mp3` vào `music_library/` (được gitignore) |
| Dựng video | `video_compose`, `video_stitch`, `video_trimmer`, `silence_cutter`, `auto_reframe`, `showcase_card`, `hyperframes_compose` | Cần FFmpeg / Node |
| Xử lý audio | `audio_mixer`, `audio_enhance` | Chỉ cần FFmpeg |
| Phụ đề | `subtitle_gen` | **Không cần gì cả** — pure Python, không FFmpeg, không key. Đây là tool duy nhất trong repo không có phụ thuộc nào |
| Đồ hoạ / sơ đồ | `diagram_gen`, `code_snippet`, `math_animate` | Cần `mmdc` hoặc PIL, `pygments`, `manim` |
| Nhân vật hoạt động | `character_spec_generator`, `svg_rig_builder`, `pose_library_builder`, `action_timeline_compiler`, `character_rig_renderer`, `character_animation_reviewer` | Không khai báo phụ thuộc nào |
| Phân tích | `scene_detect`, `frame_sampler`, `audio_probe`, `audio_energy`, `visual_qa`, `composition_validator`, `video_analyzer` | Chỉ cần FFmpeg/ffprobe |
| Đóng gói | `export_bundle` | Pure filesystem, không upload |

> ⚠️ **Piper không "pip install là xong" — và tài liệu cũ của Piper sai.** `piper_tts` khai `dependencies = ["cmd:piper"]` (`tools/audio/piper_tts.py:36`), tức cần **lệnh `piper` trên PATH**; `import` được gói Python là không đủ.
>
> ⚠️ **`piper-tts` 1.8.0 KHÔNG tự tải voice model.** `docs/PROVIDERS.md` viết *"first run downloads automatically"* — **điều này không còn đúng** với bản 1.8.0. Thực tế tool báo lỗi:
> `ValueError: Unable to find voice: en_US-lessac-medium (use piper.download_voices)`
>
> **Quy trình đúng đã kiểm chứng:**
>
> ```powershell
> $dest = "$env:LOCALAPPDATA\piper-voices"
> python -m piper.download_voices en_US-lessac-medium --download-dir $dest
> ```
>
> Sau đó gọi tool với `model` là **đường dẫn tuyệt đối tới file `.onnx`**, không phải tên ngắn:
>
> ```python
> PiperTTS().execute({
>     "text": "...",
>     "output_path": "out.wav",
>     "model": r"C:\Users\<bạn>\AppData\Local\piper-voices\en_US-lessac-medium.onnx",
> })
> ```
>
> **Vì sao phải dùng đường dẫn tuyệt đối:** `piper --data-dir` mặc định là **thư mục làm việc hiện tại** (`piper/__main__.py:95`), và nó chỉ tra `<tên>.onnx` trong thư mục đó (`:131-145`). Tool `piper_tts` gọi `piper --model <tên>` mà **không** truyền `--data-dir` và không set `cwd`, nên tên ngắn chỉ hoạt động nếu bạn tình cờ chạy pipeline từ đúng thư mục chứa model. Truyền đường dẫn tuyệt đối là cách duy nhất luôn đúng.
>
> 📏 **Số đo thực tế:** 76 ký tự → **4,69 giây** audio (pcm_s16le, 22050 Hz, mono). Tức khoảng **166 từ/phút**, nhanh hơn mức 150 WPM mà các skill giả định — nên khi viết script cho video 45 giây, nhắm khoảng **120–125 từ**, không phải 112.
>
> ⚠️ **`transcriber` cũng tải weight lần đầu.** `tools/analysis/transcriber.py` gọi Whisper **không** có `local_files_only`, nên lần chạy đầu sẽ tải weight từ HuggingFace rồi cache.

**Các nguồn stock CẦN key** (vẫn miễn phí, chỉ cần đăng ký): `pexels` (`PEXELS_API_KEY`), `unsplash` (`UNSPLASH_ACCESS_KEY`), `pixabay_video` (`PIXABAY_API_KEY`), `videvo` (`VIDEVO_API_KEY`).

**Đường có key (chất lượng cao hơn):** mở `.env` và điền key bạn có. Một vài nhóm đáng chú ý:

| Biến | Mở khóa |
|------|---------|
| `FAL_KEY` | FLUX (ảnh) + Veo/Kling/MiniMax (video) + Recraft — *một key mở nhiều provider* |
| `GOOGLE_API_KEY` | Imagen (ảnh) + Google TTS (700+ giọng) + Gemini Omni (video) |
| `ELEVENLABS_API_KEY` | TTS cao cấp + nhạc + sound effect |
| `ARK_API_KEY` | Seedance 2.0/2.5 trực tiếp (Volcengine Ark) |
| `PEXELS_API_KEY` / `PIXABAY_API_KEY` / `UNSPLASH_ACCESS_KEY` | Stock footage/ảnh miễn phí (key miễn phí) |
| `SUNO_API_KEY` | Sinh nhạc |
| `HEYGEN_API_KEY` | VEO, Sora, Runway, Kling qua một gateway |

Xem toàn bộ danh sách trong `.env.example` (134 dòng, có chú thích và link lấy key cho từng nhóm).

> 💡 **Đừng hardcode tên key vào ghi chú của bạn.** Danh sách key hợp lệ nằm ở `dependencies = ["env:..."]` trong từng tool — xem [mục 6](#6-preflight--xem-bạn-thực-sự-có-gì).

---

## 6. Preflight — xem bạn thực sự có gì

Trước khi sản xuất, hãy để registry tự khai báo năng lực. **Đừng tin doc cũ, kể cả tài liệu này.**

```powershell
# Bản tóm tắt dành cho người đọc (khuyến nghị — gọn, dễ hiểu)
python -c "from tools.tool_registry import registry; import json; registry.discover(); print(json.dumps(registry.provider_menu_summary(), indent=2))"
```

Kết quả trả về 4 nhóm thông tin:

| Trường | Ý nghĩa |
|--------|---------|
| `composition_runtimes` | Bật/tắt của `ffmpeg`, `remotion`, `hyperframes` |
| `capabilities[]` | Từng họ năng lực, dạng `đã cấu hình / tổng`, kèm danh sách provider |
| `setup_offers[]` | Tool chưa dùng được nhưng chỉ cần thêm 1 biến môi trường |
| `runtime_warnings[]` | Cảnh báo cụ thể, ví dụ `hyperframes: npm package not resolvable` |

Đọc xong, hãy tự dịch thành câu: *"Tôi đang có X/Y provider cho sinh video, có thể làm được gì ngay, và mở thêm được gì nếu bỏ 1 phút điền key."*

Các lệnh đào sâu hơn (chỉ dùng khi bản tóm tắt chưa đủ):

```powershell
# Menu đầy đủ, nhóm theo năng lực
python -c "from tools.tool_registry import registry; import json; registry.discover(); print(json.dumps(registry.provider_menu(), indent=2))"

# Catalog theo năng lực / theo nhà cung cấp
python -c "from tools.tool_registry import registry; import json; registry.discover(); print(json.dumps(registry.capability_catalog(), indent=2))"
python -c "from tools.tool_registry import registry; import json; registry.discover(); print(json.dumps(registry.provider_catalog(), indent=2))"

# Hỏi thẳng 3 engine dựng video có sẵn không
python -c "from tools.tool_registry import registry; registry.discover(); i=registry._tools['video_compose'].get_info(); print('Render engines:', i.get('render_engines')); print('HyperFrames:', i.get('hyperframes_note')); print('Remotion:', i.get('remotion_note'))"

# Kiểm tra sức khỏe HyperFrames
python -c "from tools.video.hyperframes_compose import HyperFramesCompose; r=HyperFramesCompose().execute({'operation':'doctor'}); import json; print(json.dumps(r.data, indent=2)); print('OK' if r.success else f'FAIL: {r.error}')"
```

> `support_envelope()` là bản dump **khổng lồ** (có thể vài MB). Chỉ dùng khi debug — đừng dán vào chat.

### 6.1 Hai runtime dựng video

`video_compose` có **3 engine**, và lựa chọn được **khoá ở stage proposal** rồi mang nguyên xuống compose:

| Engine | Hợp với | Cần |
|--------|---------|-----|
| **FFmpeg** | Cắt/ghép clip video, burn phụ đề, encode | `ffmpeg` binary (luôn có) |
| **Remotion** | Ảnh tĩnh → video động, text card, stat card, biểu đồ, chuyển cảnh lò xo, caption từng chữ | Node + `remotion-composer/node_modules` |
| **HyperFrames** | Kinetic typography, promo sản phẩm, launch reel, website-to-video, SVG character rig | Node ≥ 22 + FFmpeg + `npx` |

`edit_decisions.render_runtime` **bắt buộc** phải có, nếu thiếu `video_compose` báo lỗi và **không** tự chọn hộ (`tools/video/video_compose.py:1546-1557`). Hệ thống còn kiểm tra chéo `proposal_packet.production_plan.render_runtime` với `edit_decisions.render_runtime` để phát hiện đổi runtime ngầm (`` :2546-2554 ``).

**Còn một trường bắt buộc thứ hai ít được nhắc:** với `operation="render"`, `edit_decisions.renderer_family` cũng **bắt buộc** (`tools/video/video_compose.py:1493-1498`). Nó ánh xạ sang composition Remotion qua `RENDERER_FAMILY_MAP` (`:738-747`):

| `renderer_family` | Composition Remotion |
|-------------------|----------------------|
| `explainer-data`, `explainer-teacher`, `product-reveal`, `screen-demo`, `animation-first` | `Explainer` |
| `cinematic-trailer`, `documentary-montage` | `CinematicRenderer` |
| `presenter` | `TalkingHead` |

Giá trị hợp lệ có thể xem bằng Python; giá trị lạ sẽ báo `Unknown renderer_family ... Valid families: [...]`. Nếu bỏ trống, code mặc định `explainer-data` (`:1995`) nhưng validation vẫn có thể chặn — vì vậy hãy khai báo tường minh.

> ⚠️ **`operation="compose"` KHÔNG nhận ảnh tĩnh.** `_compose` từ chối thẳng (`tools/video/video_compose.py:523-532`): *"Still image '...' in cuts. Use operation='render' (auto-routes to Remotion) or operation='remotion_render' for compositions with images, animations, or component scenes."* Nghĩa là **không có đường Ken Burns bằng FFmpeg** — muốn dựng video từ ảnh thì **buộc phải có Remotion đã `npm install`**. Xem thêm [12.2](#122-các-điểm-chưa-nhất-quán-phát-hiện-khi-review) mục #11.

### 6.2 Preflight không hoàn toàn "offline và tức thì"

Chạy `provider_menu_summary()` **không cần API key**, nhưng không phải lệnh rẻ:

| Việc xảy ra ngầm | Thời gian | Ghi chú |
|------------------|-----------|---------|
| `npm view hyperframes version` | tối đa 5s | Kiểm tra gói npm có resolve được không. Offline → `timeout (5s) — offline or slow registry` |
| `npx --yes hyperframes doctor --json` | tối đa 20s | **`--yes` có thể tải/cài gói `hyperframes` từ npm** nếu cache chưa có |
| Probe ComfyUI (`localhost:8188/system_stats`) | tối đa 5s × 3 tool | Chỉ khi bạn dùng nhóm ComfyUI |
| `env:` lookup | ~0s | Chỉ đọc `os.environ` |

Kết quả được cache theo tiến trình. Lần đầu chạy preflight trên máy có Node nhưng mạng chậm có thể mất **5–25 giây** — hãy kiên nhẫn, đây không phải treo.

---

## 7. Kịch bản 1 — Video đầu tiên, không cần API key

**Mục tiêu:** có file `.mp4` trong vài phút, chi phí $0, không cần key, không cần AI agent.

Đây là 3 demo dựng sẵn bằng component Remotion thuần (`remotion-composer/public/demo-props/*.json`):

| Demo | Thời lượng | Nội dung |
|------|-----------|----------|
| `world-in-numbers` | ~45s | KPI grid, bar chart, pie chart, line chart, comparison card, stat reveal |
| `code-to-screen` | ~50s | Giáo dục dev: vòng đời HTTP request với progress bar, chart, callout |
| `focusflow-pitch` | ~40s | Pitch deck startup: chỉ số traction, donut chart doanh thu, testimonial |

### Cách A — có Python (khuyến nghị)

```powershell
# Xem danh sách demo
python render_demo.py --list

# Render một demo
python render_demo.py world-in-numbers

# Render tất cả
python render_demo.py
```

Kết quả: `projects/demos/renders/<tên-demo>.mp4`

Script `render_demo.py` tự động:
1. Kiểm tra `node`, `npm`, `npx` có trên PATH (`render_demo.py:49-59`).
2. Chạy `npm install` trong `remotion-composer/` nếu chưa có `node_modules` (`:61-63`).
3. Validate file props có ít nhất 1 `cut` (`:68-73`).
4. Gọi `npx remotion render src/index.tsx Explainer <output> --props <props> --codec h264` (`:87-102`).

### Cách B — chỉ cần Node, không cần Python

Hữu ích khi máy bạn chưa cài Python. Lệnh dưới đây là nguyên văn thao tác mà `render_demo.py` thực hiện:

```powershell
cd remotion-composer
npm install

npx remotion render src/index.tsx Explainer `
  ..\projects\demos\renders\world-in-numbers.mp4 `
  --props public/demo-props/world-in-numbers.json `
  --codec h264
```

Muốn xem trước và chỉnh sửa trực quan (Remotion Studio):

```powershell
cd remotion-composer
npx remotion studio
```

### Lần render đầu tiên sẽ chậm

Số đo thực tế trên máy Windows này (Node v24.16.0, npm 11.13.0):

| Bước | Thời gian | Ghi chú |
|------|-----------|---------|
| `npm install` trong `remotion-composer` | **~2 phút** | 199 package, 136 thư mục trong `node_modules` |
| Render `world-in-numbers` (690 frame) | vài phút | Bao gồm tải **Chrome Headless Shell** ở lần render đầu |
| Kết quả | `world-in-numbers.mp4` — **4,09 MB** | |

Remotion dùng bản FFmpeg **riêng của nó**, nên bước này **không cần FFmpeg hệ thống** — nhưng bạn vẫn cần FFmpeg hệ thống cho các pipeline đầy đủ (mục 8, 9).

---

## 8. Kịch bản 2 — Chạy thử toàn pipeline 8 stage (ra MP4 thật)

**Mục tiêu:** kiểm tra rằng Python + FFmpeg + schema + checkpoint + cost tracker + tool compose đều hoạt động, mà **không tốn một đồng nào**.

`tests/qa/test_08_end_to_end.py` mô phỏng đúng pipeline `animated-explainer`: nó tạo fixture bằng FFmpeg, validate artifact qua JSON Schema ở từng stage, ghi checkpoint, rồi **chạy tool thật** (`audio_mixer` + `video_compose`) để dựng ra video cuối.

```powershell
python tests/qa/test_08_end_to_end.py
```

Đầu ra:

| Đường dẫn | Nội dung |
|-----------|----------|
| `tests/qa/output/e2e_final_output.mp4` | **Video ~60s thật** (1280x720, h264 + audio) |
| `tests/qa/output/e2e_pipeline/qa_e2e_test/` | Checkpoint của cả 8 stage |
| `tests/qa/output/e2e_assets/` | Fixture audio/video/ảnh |

Script in ra `PASS`/`FAIL` cho từng kiểm tra, và kết thúc bằng `END-TO-END TEST COMPLETE: N passed, M failed`.

Kiểm tra riêng engine dựng video (cắt, burn phụ đề, overlay, encode profile):

```powershell
python tests/qa/test_05_video_compose.py
python tests/qa/test_04_audio_mix.py
python tests/qa/test_06_video_stitch.py
```

`tests/qa/QA_PLAN.md` liệt kê đủ 8 script QA, script nào cần key và chi phí ước tính:

| Script | Tool | Cần key? | Chi phí |
|--------|------|----------|---------|
| `test_04_audio_mix.py` | `audio_mixer` | Không | $0 |
| `test_05_video_compose.py` | `video_compose` | Không | $0 |
| `test_06_video_stitch.py` | `video_stitch` | Không | $0 |
| `test_07_playbook_intelligence.py` | `playbook_loader` | Không | $0 |
| `test_08_end_to_end.py` | Toàn pipeline | Không | $0 |
| `test_01_tts.py` | `elevenlabs_tts` | `ELEVENLABS_API_KEY` | ~$0.02 |
| `test_02_image_gen.py` | GPT Image 2 / FLUX | `OPENAI_API_KEY`, `FAL_API_KEY` | ~$0.15 |
| `test_03_music.py` | `music_gen` | `ELEVENLABS_API_KEY` | ~$0.10 |

Chạy bộ contract test (không cần key, dùng để xác nhận bản cài đặt lành mạnh):

```powershell
python -m pytest tests/contracts/ -q          # tương đương: make test-contracts
python -m pytest tests/ -q                    # toàn bộ
```

> Nếu chưa cài `pytest`: `python -m pip install -r requirements-dev.txt`.

---

## 9. Kịch bản 3 — Tạo video thật bằng AI agent

Đây là cách OpenMontage được thiết kế để dùng. **Bạn không gõ lệnh pipeline — bạn ra đề bài, agent vận hành pipeline.**

### 9.1 Chuẩn bị

1. Cài đặt xong [mục 4](#4-cài-đặt), đã có `.env` (có thể trống key).
2. Mở **thư mục repo** này bằng một AI coding assistant: Claude Code, Cursor, Copilot, Windsurf hoặc Codex.
   Repo đã có sẵn file điều hướng cho từng loại: `CLAUDE.md`, `CODEX.md`, `CURSOR.md`, `COPILOT.md` — tất cả đều trỏ về `AGENT_GUIDE.md`.
3. Đảm bảo assistant đọc được `AGENT_GUIDE.md` (file này là hợp đồng vận hành bắt buộc).

### 9.2 Đề bài mẫu (zero-key, $0)

Chọn một trong các prompt sau và dán vào assistant:

```
Làm cho tôi một video explainer 45 giây về vì sao bầu trời có màu xanh.
Dùng biểu đồ và chữ động, không cần ảnh — chỉ chart, stat card và typography.
```

```
Tạo video 60 giây về mức tiêu thụ cà phê trên thế giới.
Có bar chart so sánh các nước và pie chart các loại cà phê.
```

```
Làm video explainer 90 giây giải thích cách git rebase hoạt động.
Dùng sơ đồ động và comparison card để so rebase với merge.
Đối tượng: lập trình viên junior.
```

Các prompt này lấy từ `PROMPT_GALLERY.md:27-57` — đã được kiểm nghiệm cho đường zero-key (Piper TTS + stock/free media + Remotion).

### 9.3 Agent sẽ làm gì

| Thứ tự | Stage | Agent làm | Bạn phải làm gì |
|--------|-------|-----------|-----------------|
| 0 | Preflight | Quét registry, trình bày menu năng lực thật | Đọc, biết mình có gì |
| 1 | `research` | Nghiên cứu chủ đề, tìm dữ liệu có nguồn | — |
| 2 | `proposal` | Đề xuất 3–5 concept khác nhau + pipeline + tool path + **dự phí** + **phương án runtime (Remotion vs HyperFrames)** + **kế hoạch nhạc** | 🔴 **DUYỆT** |
| 3 | `script` | Viết kịch bản, word count khớp thời lượng, có chỉ dẫn giọng đọc | 🔴 **DUYỆT** |
| 4 | `scene_plan` | Chia cảnh, thời lượng, asset cần cho từng cảnh | 🔴 **DUYỆT** |
| 5 | `assets` | Sinh narration (TTS), ảnh, nhạc; ghi `asset_manifest` | 🔴 **DUYỆT** (xem filmstrip từng cảnh) |
| 6 | `edit` | Quyết định cắt, overlay, phụ đề, ducking nhạc | — |
| 7 | `compose` | Render ra `renders/final.mp4`, tự nghiệm thu bằng ffprobe + trích frame + phân tích audio | — |
| 8 | `publish` | Metadata SEO, chapter, gói export | 🔴 **DUYỆT** |

🔴 = cổng duyệt bắt buộc (`human_approval_default: true` trong `pipeline_defs/animated-explainer.yaml`).

**Khi agent dừng ở cổng duyệt, việc của bạn là đọc và trả lời.** Bạn có thể: duyệt, yêu cầu sửa (tối đa 3 lần/stage), hoặc huỷ.

### 9.4 Sản phẩm cuối

```
projects/<tên-project>/renders/final.mp4
```

Kèm theo toàn bộ artifact JSON có thể kiểm tra lại (`artifacts/`, `checkpoint_*.json`) — đây là "dấu vết kiểm toán" của lần sản xuất: chọn provider nào, model nào, tốn bao nhiêu, phương án nào bị loại và vì sao.

### 9.5 Chọn pipeline khác

`animated-explainer` chỉ là một trong **13 pipeline** có trong `pipeline_defs/`:

| Pipeline | Hợp với | Độ ổn định |
|----------|---------|-----------|
| `animated-explainer` | Từ chủ đề → explainer hoàn chỉnh | production |
| `documentary-montage` | Montage tư liệu thật (Archive.org, NASA, Wikimedia…), dựng corpus + CLIP retrieval | beta |
| `cinematic` | Trailer, teaser, mood-led | production |
| `animation` | Motion graphics / animation-first | production |
| `character-animation` | Nhân vật hoạt hình rig cục bộ | beta |
| `talking-head` | Video người nói từ footage có sẵn | beta |
| `screen-demo` | Quay màn hình, walkthrough | production |
| `clip-factory` | Nhiều clip ngắn từ 1 nguồn dài | beta |
| `podcast-repurpose` | Highlight từ podcast | beta |
| `hybrid` | Footage gốc + visual hỗ trợ | production |
| `avatar-spokesperson` | Avatar dẫn chương trình / lip-sync | production |
| `localization-dub` | Phụ đề, lồng tiếng, bản dịch | beta |
| `framework-smoke` | Smoke test 2 stage tối thiểu | test |

> Pipeline gắn nhãn **beta** chưa được audit đầy đủ — vẫn chạy nhưng có thể gặp trục trặc.
> ⚠️ `documentary-montage` **có** manifest trên đĩa nhưng **không** xuất hiện trong bảng "Available Pipelines" của `AGENT_GUIDE.md` — xem [12.2](#122-các-điểm-chưa-nhất-quán-phát-hiện-khi-review).

### 9.6 Ví dụ đã chạy thật, đầu-cuối, zero-key

Đây là kết quả của một lần sản xuất hoàn chỉnh đã thực sự chạy trên máy Windows (không API key, $0), để bạn biết "thành công" trông như thế nào:

| | |
|---|---|
| **Project** | `projects/why-the-sky-is-blue/` |
| **Chủ đề** | Vì sao bầu trời không phải màu tím (nghịch lý violet) |
| **Sản phẩm** | `renders/final.mp4` — h264 **1920×1080** 30fps + aac, **43,5 s**, 2,73 MB |
| **Nghiệm thu** | `final_review.status = pass`, `issues_found: []` — **sạch hoàn toàn**; drift thời lượng **3,3%** (ngưỡng 5%); `runtime_swap_detected = false`; không frame đen; `clipping_detected = false` |
| **Phụ đề** | **124 cue từng từ** burn trực tiếp trong video (highlight theo từ đang đọc), chữ lấy từ `script`, timing lấy từ `transcriber`; `subtitle_check.coverage_ratio = 1.0`; `transcript_comparison.word_accuracy = 90,3%` |
| **Narration** | Piper `en_US-lessac-medium`, 124 từ → **42,49 s** thực đo, chuẩn hoá `loudnorm -16 LUFS` bằng `audio_mixer` |
| **Visual** | 6 component scene Remotion: `text_card` → `stat_card` → `bar_chart` → `callout` → `comparison` → `text_card` |
| **Chi phí** | **$0,00** (image_generation 0/16, video_generation 0/26, tts 1/10, music 0/5) |
| **Thời gian render** | ~5 phút cho 43,5 s video (Node + Chrome Headless) |
| **Nhạc** | Không có — không nguồn nào khả dụng, đã nêu rõ từ stage proposal |

Cấu trúc đầu ra đầy đủ:

```
projects/why-the-sky-is-blue/
├── checkpoint_{research,proposal,script,scene_plan,assets,edit,compose,publish}.json   # 8/8 completed
├── decision_log.json                 # 10 quyết định, mỗi cái ghi rõ phương án bị loại
├── artifacts/
│   ├── research_brief.json           # 5 landscape / 9 data points / 5 angles / 7 nguồn
│   ├── proposal_packet.json          # 4 concept, cost $0, delivery_promise
│   ├── script.json                   # 124 từ, 6 section, 7 enhancement cue
│   ├── scene_plan.json               # 6 cảnh, 3 loại
│   ├── asset_manifest.json           # 7 asset (narration), $0
│   ├── edit_decisions.json           # 6 cut canh theo narration thật
│   ├── render_report.json
│   ├── final_review.json             # status: pass
│   └── publish_log.json
├── assets/audio/narration_*.wav      # narration từng section + track ghép
├── assets/subtitles.srt
├── renders/final.mp4                 # SẢN PHẨM
└── exports/                          # video, phụ đề, metadata, thumbnail concept
```

**Ba điều rút ra từ lần chạy thật này:**

1. **Canh cuts theo narration thật, không theo kế hoạch.** Narration từng section lệch so với dự kiến (7,26s thay vì 7s…). `edit-director.md` yêu cầu rõ điều này, và nếu bỏ qua thì hình và tiếng trôi khỏi nhau.
2. **Nhớ đuôi +1s của Remotion.** Cuts kết thúc ở 42,49s → render 43,5s. Nếu tôi đặt 45s thì render thành 46s.
3. **Chạy `audio_mixer` để chuẩn hoá loudness.** Lần render đầu bị cảnh báo `Max volume -0.0 dB — possible clipping`; sau khi cho qua `audio_mixer` (`loudnorm -16 LUFS`) thì `clipping_detected: false`. Đây là required tool của stage compose trong manifest — đừng bỏ qua.

---

## 10. Backlot — xem tiến trình sản xuất

Backlot là server local, **chỉ đọc**, hiển thị quá trình sản xuất: stage nào đang sáng, kịch bản dạng trang screenplay, scene plan dạng filmstrip tự đầy lên khi asset sinh ra, quyết định, chi phí, hoạt động. Toàn bộ dữ liệu **dẫn xuất từ đĩa** (`projects/<id>/`) — Backlot không can thiệp vào pipeline.

```powershell
python -m backlot open <project-id>   # mở board của dự án (tự start server nếu cần)
python -m backlot open                # thư viện: tất cả dự án
python -m backlot serve --port 4750   # chạy server ở foreground
```

| Thông số | Giá trị |
|----------|---------|
| Cổng mặc định | **4750** (`backlot/__init__.py:16`), đổi bằng biến `BACKLOT_PORT` |
| Địa chỉ bind | **chỉ 127.0.0.1** (`backlot/__main__.py:85`) — không lộ ra mạng ngoài |
| URL của dự án | `http://127.0.0.1:4750/p/<project-id>` |
| Phụ thuộc | `fastapi`, `uvicorn`, `watchfiles` (đã có trong `requirements.txt`) + `Pillow` + binary `ffmpeg` để tạo thumbnail |

Muốn thử ngay mà chưa cần sản xuất thật:

```powershell
python scripts/backlot_simulate_run.py     # chạy demo ~1 phút
python -m backlot open backlot-demo-run
```

`scripts/backlot_simulate_run.py` không phải mock rẻ tiền — nó chạy một sản xuất giả **qua đúng hợp đồng thật**: `init_project`, heartbeat `in_progress`, trạng thái `awaiting_human` có gate, event của tool, và artifact được ghi dần, dùng pipeline `cinematic` với project id `backlot-demo-run`. Đây là cách tốt nhất để "xem trước" Backlot trước khi bạn sản xuất thật.

Nguồn dữ liệu của từng thành phần trên board (`backlot/README.md:18-28`):

| Thành phần | Đọc từ |
|------------|--------|
| Danh tính / thứ tự rail | `project.json` + `pipeline_defs/<type>.yaml` |
| Trạng thái stage, gate, version | `checkpoint_<stage>.json` + `history/` |
| Card kịch bản | `artifacts/script.json` |
| Filmstrip | join `scene_plan × script × asset_manifest` |
| Hiệu ứng "đang sinh", activity | `events.jsonl` |
| Đồng hồ chi phí | `checkpoint.cost_snapshot` |
| Render | `renders/*.mp4` |

Có cả chế độ **REPLAY**: tua lại một lần chạy đã xong từ checkpoint history + timestamp event.

> **Backlot hỏng thì cứ tiếp tục sản xuất.** Board là bên quan sát, **không bao giờ** là blocker.
>
> Lệnh `open` được thiết kế để suy giảm "êm": module chỉ import thư viện chuẩn nên chạy được **kể cả khi chưa cài `fastapi`/`uvicorn`**. Nếu server không khởi động hoặc không trả lời `/api/health` trong 15 giây, nó in `backlot: could not start server (...) — continuing without the board` rồi thoát với mã 1 — pipeline vẫn chạy bình thường.
>
> Ngược lại, lệnh `serve` **không** êm như vậy: thiếu `uvicorn` sẽ ra traceback `ImportError` thẳng.

---

## 11. Xử lý sự cố

| Triệu chứng | Nguyên nhân | Cách sửa |
|-------------|-------------|----------|
| `python --version` không in gì, hoặc báo "Python was not found; run without arguments to install from the Microsoft Store" | Bạn đang gọi **stub alias** của Microsoft Store (`C:\Users\<bạn>\AppData\Local\Microsoft\WindowsApps\python.exe`), không phải Python thật | Cài Python từ python.org, rồi **tắt** alias: Settings → Apps → Advanced app settings → App execution aliases → tắt `python.exe` / `python3.exe`. Mở terminal mới |
| `make : The term 'make' is not recognized` | Windows không có GNU Make | Dùng lệnh PowerShell tương đương ở [4.1](#41-windows-powershell--khuyến-nghị), hoặc chạy `make` trong Git Bash / WSL |
| `make` chạy nhưng lỗi cú pháp `command -v: not found` | Makefile viết cho bash, đang bị PowerShell/cmd thực thi | Dùng Git Bash hoặc WSL |
| `ffmpeg : The term 'ffmpeg' is not recognized` | FFmpeg chưa cài hoặc chưa vào PATH | Cài theo [4.3](#43-cài-ffmpeg), **mở terminal mới** |
| `npm install` báo `ERR_INVALID_ARG_TYPE` | Lỗi đã biết trên Windows | `npx --yes npm install` |
| `Set-ExecutionPolicy` / "running scripts is disabled on this system" | PowerShell chặn `Activate.ps1` | `Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass` |
| Render đầu tiên rất chậm | Remotion đang tải bundle FFmpeg riêng | Chờ; các lần sau nhanh hơn |
| `hyperframes ... not resolvable`, hoặc HyperFrames báo thiếu runtime | Node < 22, thiếu `ffmpeg`/`npx`, hoặc cache npx chưa có | `node --version` phải ≥ 22; chạy `npx --yes hyperframes --version`; kiểm tra sức khỏe bằng lệnh ở [mục 6](#6-preflight--xem-bạn-thực-sự-có-gì) |
| `Still image 'x.png' in cuts. Use operation='render' ...` | Bạn gọi `operation="compose"` nhưng `cuts` có ảnh tĩnh. `_compose` **cố ý** từ chối ảnh | Đổi sang `operation="render"` (tự route sang Remotion), và đảm bảo `cd remotion-composer && npm install` đã chạy. **Không có đường FFmpeg Ken Burns** |
| `No renderer_family in edit_decisions` | Thiếu `renderer_family` — trường bắt buộc thứ hai của `operation="render"` | Thêm `"renderer_family": "explainer-data"` (hoặc `cinematic-trailer`, `presenter`, …). Xem [6.1](#61-hai-runtime-dựng-video) |
| `Remotion project exists but node_modules are NOT installed` | `remotion-composer/` có nhưng chưa `npm install` | `cd remotion-composer; npm install` |
| Preflight treo 5–25 giây | Bình thường — đang probe npm registry + `npx hyperframes doctor` + ComfyUI localhost | Chờ. Kết quả được cache theo tiến trình. Xem [6.2](#62-preflight-không-hoàn-toàn-offline-và-tức-thì) |
| `UnicodeEncodeError: 'charmap' codec can't encode characters in position ...` khi chạy preflight | Console Windows mặc định dùng cp1252, JSON của registry chứa ký tự ngoài bảng mã đó. **Đã gặp thật.** | Đặt biến môi trường trước khi chạy:<br>`$env:PYTHONIOENCODING='utf-8'; $env:PYTHONUTF8='1'` |
| Warning `get_pipeline_stages called without pipeline_type - using canonical fallback order` | Có nơi gọi `get_pipeline_stages()`/`get_next_stage()` thiếu `pipeline_type` (xem [12.2](#122-các-điểm-chưa-nhất-quán-phát-hiện-khi-review) #10). **Đã gặp thật** khi chạy kịch bản 2 | Không phải lỗi chặn. Luôn truyền `pipeline_type` khi bạn tự gọi |
| `pip install` xong nhưng lệnh `python`/`ffmpeg` vẫn "not recognized" | PATH của tiến trình đang chạy được chụp lúc khởi động, không tự cập nhật sau khi cài | Mở terminal mới, hoặc nạp PATH thủ công:<br>`$env:PATH = "$env:LOCALAPPDATA\Microsoft\WinGet\Links;$env:LOCALAPPDATA\Programs\Python\Python312;$env:LOCALAPPDATA\Programs\Python\Python312\Scripts;$env:PATH"` |
| `SyntaxError` khi chạy `python -c "..."` nhiều dòng trong PowerShell | PowerShell làm hỏng dấu nháy khi truyền vào native command | Truyền script qua stdin: `$code \| python -` thay vì `python -c $code` |
| `pip install piper-tts` thất bại, hoặc `piper` not recognized sau khi cài | Tool cần **lệnh** `piper` trên PATH, không chỉ gói Python | Kiểm tra `piper --help`; nếu thiếu, tải binary standalone từ repo rhasspy/piper |
| `ValueError: Unable to find voice: en_US-lessac-medium (use piper.download_voices)` | `piper-tts` 1.8.0 **không** tự tải voice model (tài liệu cũ của Piper nói ngược lại). **Đã gặp thật** | `python -m piper.download_voices en_US-lessac-medium --download-dir $env:LOCALAPPDATA\piper-voices`, rồi gọi tool với `model` = **đường dẫn tuyệt đối** tới file `.onnx`. Xem mục 5 |
| Render Remotion chết với `TypeError: Cannot read properties of undefined (reading 'icon')` | `cut.type = "callout"` nhưng `callout_type` không nằm trong danh sách hợp lệ. `CalloutBox.tsx:51` index thẳng vào `TYPE_DEFAULTS[type]` mà không kiểm tra. **Đã gặp thật** | Chỉ dùng `callout_type` ∈ `info` \| `warning` \| `tip` \| `quote` (`CalloutBox.tsx:9`). Thông báo lỗi không hề nhắc tới `callout_type` nên rất dễ mất thời gian |
| Video render ra **dài hơn** tổng `out_seconds` của `cuts` đúng ~1 giây | `remotion-composer/src/Root.tsx:132` cố ý cộng đuôi: `durationInFrames = ceil((lastEnd + 1) * 30)`. **Đã đo thật:** 15,0s → 16,0s | Đây là hành vi cố định, không phải lỗi. **Quy tắc lập kế hoạch:** đặt `max(cut.out_seconds) = mục_tiêu − 1.0`. Ví dụ video 45s → `out_seconds` cuối = 44,0 → render 45,0s. Đừng quên vì `animated-explainer` nghiệm thu `±5%` |
| `[pre-compose] No delivery_promise in edit_decisions — skipping promise validation` | `edit_decisions` thiếu `delivery_promise` nên cổng kiểm tra "giữ đúng lời hứa" bị bỏ qua | Thêm `delivery_promise` vào `edit_decisions` (hoặc `metadata.delivery_promise`) để cổng này thực sự chạy |
| Transcript/subtitle trống, hoặc `character-animation` báo thiếu package | Chưa cài `requirements-local.txt` | `python -m pip install -r requirements-local.txt` rồi `python -m playwright install chromium` |
| `GATE VIOLATION` khi ghi checkpoint | Stage có `human_approval_default: true` bị ghi `completed` mà thiếu `human_approved=True` | Đây là hành vi đúng theo thiết kế. Chỉ ghi `completed` sau khi người duyệt đồng ý, hoặc ghi `awaiting_human` |
| `PREREQUISITE VIOLATION: stage 'X' cannot advance; incomplete or missing: [...]` | Bạn nhảy cóc stage, hoặc stage trước chưa `completed`, hoặc stage trước là gated mà chưa được duyệt | Chạy đúng thứ tự stage trong manifest. **Lưu ý:** cổng này không được mô tả trong `AGENT_GUIDE.md` — xem [12.2](#122-các-điểm-chưa-nhất-quán-phát-hiện-khi-review) |
| `Unknown pipeline_type 'X' — cannot resolve gate policy...` | Gõ sai tên pipeline (kiểm tra `pipeline_defs/*.yaml`). Lỗi này bắn cả khi ghi `in_progress` | Đây là fail-closed có chủ đích: gõ sai tên pipeline **không thể** vô hiệu hoá việc kiểm soát cổng. Sửa tên cho đúng |
| `ImportError: uvicorn` khi chạy `python -m backlot serve` | Chưa cài phụ thuộc Backlot | `python -m pip install -r requirements.txt`. Hoặc dùng `python -m backlot open` (chạy được kể cả khi thiếu) |
| `render_runtime is not set in edit_decisions` | `edit_decisions` thiếu khoá `render_runtime` — trường này là **bắt buộc** ở tầng schema (`schemas/artifacts/edit_decisions.schema.json`) | Thêm `"render_runtime": "remotion"` (hoặc `hyperframes` / `ffmpeg`). Hệ thống cố ý **không** tự đoán |
| Muốn dự án ghi ra chỗ khác | — | Đặt biến `OPENMONTAGE_PROJECTS_DIR` (`lib/paths.py:17`) |

---

## 12. Nhận xét khi review source code

### 12.1 Điểm mạnh của thiết kế

1. **Tách bạch tri thức khỏi code.** Logic sản xuất nằm ở YAML/Markdown — người không biết Python vẫn sửa được quy trình, chất lượng, tiêu chí review. Đây là lựa chọn kiến trúc hiếm và đúng cho một hệ thống "agent-first".
2. **Hợp đồng được ép bằng schema, không bằng niềm tin.** Artifact validate qua `schemas/artifacts/`, checkpoint qua `schemas/checkpoints/`, manifest qua `schemas/pipelines/`. Sai hợp đồng → fail fast.
3. **Fail-closed ở những chỗ quan trọng.** Ví dụ `_stage_requires_approval` (`lib/checkpoint.py:259`): `pipeline_type` được truyền nhưng **không** khớp manifest nào thì **raise**, chứ không im lặng bỏ qua gate. Gõ sai tên pipeline không thể vô hiệu hoá việc kiểm soát cổng.
4. **Chống đổi runtime ngầm.** `video_compose` so `proposal.production_plan.render_runtime` với `edit_decisions.render_runtime` và gắn cờ `runtime_swap_detected` (`tools/video/video_compose.py:2300-2303`, `:2546-2554`). Đây là loại lỗi rất khó phát hiện nếu chỉ nhìn kết quả cuối.
5. **Zero-key thực sự, không phải marketing.** `piper_tts` offline + 15 nguồn stock/archive công cộng (`tools/video/stock_sources/`) + Remotion + FFmpeg cho phép ra video hoàn chỉnh mà không cần key. `lib/env_loader.py` bỏ qua `.env` thiếu một cách lặng lẽ, nên không có "chết vì thiếu config".
6. **Mọi lần chạy đều resumable.** Checkpoint + `history/` + `get_next_stage()` cho phép dừng/tiếp tục mà không mất lịch sử stage cũ.
7. **Backlot là observer thuần.** Không có đường nào để board chặn pipeline (`backlot/README.md`), nên hỏng UI không làm hỏng sản xuất.
8. **Ghi checkpoint an toàn với crash.** Ghi ra `.tmp` → lưu bản cũ vào `history/` → `os.replace()` (`lib/checkpoint.py:551-562`), nên không bao giờ để lại file checkpoint cụt.
9. **Chi tiết "có ăn học" cho Windows.** `history/` dùng `shutil.copyfile` chứ không `rename` (`lib/checkpoint.py:380`) — vì Windows từ chối rename file đang bị tiến trình khác giữ (Backlot watcher). Đây là loại chi tiết chỉ có được khi tác giả thật sự chạy thử trên Windows.
10. **Marker backfill.** Nếu người gọi `write_checkpoint()` quên truyền `pipeline_type`, hệ thống đọc lại từ `project.json` (`lib/checkpoint.py:442-455`) — nên quên tham số **không** làm mất hiệu lực của cổng duyệt.

### 12.2 Các điểm chưa nhất quán phát hiện khi review

| # | Phát hiện | Bằng chứng | Ảnh hưởng | Đề xuất |
|---|-----------|-----------|-----------|---------|
| 1 | `ATLASCLOUD_API_KEY` được **README** hướng dẫn và **3 tool** yêu cầu, nhưng **không có** trong `.env.example` | README nêu key này; `tools/graphics/atlas_image.py:44`, `tools/video/atlas_video.py:60`, `tools/graphics/atlas_3d.py:61` đều khai `dependencies = ["env:ATLASCLOUD_API_KEY"]`; `.env.example` không có dòng nào chứa `ATLAS` | Người dùng copy `.env.example` → không biết phải điền key nào để bật Atlas Cloud; phải đọc source mới biết | Thêm `ATLASCLOUD_API_KEY=` (kèm 2 alias `ATLAS_CLOUD_API_KEY`, `ATLAS_API_KEY` mà `tools/atlas_client.py:37` chấp nhận) vào `.env.example` |
| 2 | README ghi yêu cầu **Node.js 18+**, nhưng **HyperFrames cần Node ≥ 22** | README "Prerequisites"; bảng engine trong `AGENT_GUIDE.md` ghi HyperFrames cần "Node.js ≥ 22" | Người dùng Node 18/20 làm theo README sẽ thấy HyperFrames "không giải thích được vì sao không chạy" | Ghi rõ trong README: Node ≥ 18 cho Remotion, **≥ 22 cho HyperFrames** |
| 3 | `documentary-montage` có manifest và director skill đầy đủ nhưng **thiếu** trong bảng "Available Pipelines" của `AGENT_GUIDE.md` (bảng liệt kê 12, đĩa có 13) | `pipeline_defs/documentary-montage.yaml` tồn tại; `Get-ChildItem pipeline_defs/*.yaml` = 13 file; `AGENT_GUIDE.md` bảng 12 dòng | Pipeline tốt bị "ẩn" khỏi cả người dùng lẫn agent — agent có thể không bao giờ đề xuất đường documentary | Thêm dòng `documentary-montage` vào bảng (đã có sẵn phần mô tả ở đoạn checkpoint-protocol) |
| 4 | `make setup` **không** cài `requirements-local.txt`, tức là mặc định thiếu `faster-whisper` (STT mặc định) và `playwright` | `requirements-local.txt:1-13` tự ghi rõ "dependency mà repo còn thiếu… `make setup` không cài"; `Makefile:54-76` chỉ cài `requirements.txt` + `piper-tts` | Sau `make setup` "thành công", người dùng vẫn hỏng chức năng transcript và character-animation | Gộp 2 dòng này vào `requirements.txt`, hoặc thêm bước cài trong `make setup` |
| 5 | `Makefile` không dùng được trên Windows mặc định, trong khi README có nhánh hướng dẫn Windows | `Makefile:3-4` dùng `command -v` / `$(shell ...)` / vòng `for` bash; README lại đưa lệnh Windows riêng | Người dùng Windows bối rối giữa 2 luồng tài liệu | Thêm `make.ps1` hoặc script setup PowerShell chính thức |
| 6 | `AGENT_GUIDE.md` và `PROJECT_CONTEXT.md` viết tay bảng pipeline, dễ lệch khỏi `pipeline_defs/` | Xem #3 | Tài liệu lệch dần theo thời gian | Sinh bảng pipeline từ `pipeline_defs/` trong CI (`tests/contracts/test_pipeline_catalog.py` đã có sẵn nền tảng) |
| 7 | **Cổng thứ hai `PREREQUISITE VIOLATION` không được mô tả ở bất kỳ tài liệu nào** | `lib/checkpoint.py:284-346` (`_enforce_stage_prerequisites`) tồn tại và bắn lỗi khi stage trước chưa `completed` hoặc là gated chưa duyệt; `AGENT_GUIDE.md` chỉ nói về `GATE VIOLATION` | Agent (và người viết script) đâm vào lỗi này mà không hiểu vì sao, vì tài liệu không nhắc tới | Bổ sung mục `PREREQUISITE VIOLATION` vào `AGENT_GUIDE.md` + `skills/meta/checkpoint-protocol.md` |
| 8 | `config.yaml` gần như **"trơ"** ở runtime: sửa nó không đổi hành vi hệ thống | `OpenMontageConfig.load()` không có call site nào ngoài test (`tests/contracts/test_phase0_contracts.py:263`); `CostTracker` nhận `mode` qua tham số constructor (`tools/cost_tracker.py:49,56`), không đọc config | Người dùng sửa `budget.total_usd` / `output.default_resolution` trong `config.yaml` rồi tưởng đã cấu hình — thực tế không có tác dụng | Nối `CostTracker` và profile output vào `OpenMontageConfig.load()`, hoặc ghi rõ trong `config.yaml` rằng hiện chưa được dùng |
| 9 | `docs/ARCHITECTURE.md` mô tả sai hợp đồng checkpoint | `:245` nói checkpoint nằm trong `pipeline/` (thực tế `projects/<id>/`); `:263` liệt kê status `pending` (**không tồn tại** trong schema, ghi vào sẽ fail validate); ví dụ JSON ở `:247-260` thiếu `pipeline_type` là trường **bắt buộc** | Người đọc theo ví dụ sẽ tạo checkpoint không hợp lệ và bị `validate_checkpoint` từ chối | Cập nhật `docs/ARCHITECTURE.md` theo `schemas/checkpoints/checkpoint.schema.json` |
| 10 | `skills/meta/checkpoint-protocol.md` gọi `get_next_stage(pipeline_dir, project_name)` — thiếu `pipeline_type` | `:174,184`; chữ ký thật là `get_next_stage(pipeline_dir, project_id, pipeline_type=None)` (`lib/checkpoint.py:620`). Khi thiếu `pipeline_type`, hàm rơi về thứ tự `STAGES` chuẩn | Trả **sai stage kế tiếp trên 6+ / 13 pipeline**: với `animated-explainer`/`animation`/`cinematic` nó trả `idea` ngay sau `proposal` (các pipeline này không có stage `idea`); với `screen-demo` trả `research` thay vì `real_capture` | Sửa 2 chỗ gọi trong skill cho đủ 3 tham số |
| 11 | **Đường "FFmpeg Ken Burns cho ảnh tĩnh" mà tài liệu hứa hẹn KHÔNG tồn tại trong code** | `_compose` từ chối ảnh tĩnh (`tools/video/video_compose.py:523-532`); `_needs_remotion()` trả `True` cho mọi trường hợp trừ khi Remotion không có (`:1375-1413`). Trong khi đó `docs/PROVIDERS.md:1141` viết *"If Remotion is not installed, compositions fall back to FFmpeg Ken Burns pan-and-zoom"* | Máy chưa `npm install` **không thể** dựng video từ ảnh — nhưng tài liệu khiến người dùng tưởng vẫn có đường lui. Đây là loại "silent unavailable path" nguy hiểm nhất | Sửa `docs/PROVIDERS.md:1141` cho khớp code, hoặc thật sự cài đặt đường Ken Burns |
| 12 | `renderer_family` là **trường bắt buộc thứ hai** của `operation="render"` nhưng không được nêu trong tài liệu vận hành | `_pre_compose_validation` chặn khi thiếu (`tools/video/video_compose.py:1493-1498`, thông báo `"No renderer_family in edit_decisions. ..."`); `AGENT_GUIDE.md` chỉ nói `render_runtime` là bắt buộc | Người viết `edit_decisions` theo tài liệu sẽ bị chặn ở compose mà không hiểu vì sao | Ghi rõ cả hai trường bắt buộc (`render_runtime` + `renderer_family`) trong `AGENT_GUIDE.md` và schema `edit_decisions` |
| 13 | **`AGENT_GUIDE.md` yêu cầu ghi `decision_log` với `category: "approval_policy"`, nhưng enum của schema KHÔNG có giá trị đó** | `AGENT_GUIDE.md` ("Human Checkpoint Protocol") viết: *"explicit full-run pre-authorization must be recorded as a `decision_log` entry (`category: "approval_policy"`)"*. Enum thật trong `schemas/artifacts/decision_log.schema.json:27-44` gồm 16 giá trị và **không có** `approval_policy`; ghi vào sẽ fail validate. **Đã gặp thật** khi chạy pipeline | Cơ chế "uỷ quyền toàn bộ lần chạy" mà tài liệu mô tả **không thể thực thi** — agent buộc phải bỏ qua hoặc dùng category sai | Thêm `approval_policy` vào enum, hoặc sửa `AGENT_GUIDE.md` chỉ định một category có sẵn |
| 14 | Cấu trúc `decision_log.options_considered` không được mô tả ở đâu trong tài liệu vận hành | Schema yêu cầu **mảng object** `{option_id, label, score, reason}`, và `selected` phải là `option_id` (`schemas/artifacts/decision_log.schema.json:51-76`). `AGENT_GUIDE.md` chỉ nói "moved into `options_considered`" như thể đó là mảng chuỗi. **Đã gặp thật:** lần viết đầu fail validate | Agent viết `decision_log` theo tài liệu sẽ fail validate và phải đọc schema mới sửa được | Ghi ví dụ cấu trúc đầy đủ vào `AGENT_GUIDE.md` hoặc `skills/meta/checkpoint-protocol.md` |
| 15 | **`piper_tts.get_status()` báo AVAILABLE trong khi tool hoàn toàn không dùng được** | `tools/audio/piper_tts.py:98-101` chỉ kiểm tra `shutil.which("piper")`. Nó **không** kiểm tra voice model có tồn tại hay không. **Đã gặp thật:** preflight báo `tts 1/10 configured` với `avail=piper`, nhưng lần gọi đầu tiên chết với `Unable to find voice`. Kèm theo, `docs/PROVIDERS.md:1197` ghi *"first run downloads automatically"* — **sai** với `piper-tts` 1.8.0 | Đúng loại lỗi mà `AGENT_GUIDE.md` gọi là nguy hiểm nhất: một năng lực **trông có** nhưng không có. Agent lập kế hoạch dựa trên preflight sẽ hứa có thuyết minh rồi hỏng ở stage assets | `get_status()` nên kiểm tra sự tồn tại của ít nhất một voice model (hoặc `.onnx` trong `--data-dir`); sửa `docs/PROVIDERS.md` cho khớp hành vi 1.8.0 |
| 16 | **Prop enum của scene Remotion không được validate ở đâu cả — giá trị sai gây crash với thông báo sai hướng** | `remotion-composer/src/components/CalloutBox.tsx:51` thực hiện `TYPE_DEFAULTS[type]` với index không kiểm tra; `CalloutType` chỉ nhận `info \| warning \| tip \| quote` (`:9`). **Đã gặp thật:** đặt `callout_type: "insight"` làm render chết ở frame 675 với `TypeError: Cannot read properties of undefined (reading 'icon')` — thông báo **không hề nhắc tới `callout_type`** | Agent viết `edit_decisions` sẽ mất thời gian truy `CalloutBox.tsx` mới hiểu. Vì `edit_decisions` là artifact do agent sinh, không có schema nào chặn các giá trị này trước khi tới render | Thêm giá trị mặc định an toàn (`TYPE_DEFAULTS[type] ?? TYPE_DEFAULTS.info`) và/hoặc validate prop scene trong `schemas/artifacts/edit_decisions.schema.json` |
| 17 | **Composition `Explainer` tự cộng thêm 1 giây vào thời lượng — và điều này đụng thẳng vào tiêu chí nghiệm thu của chính pipeline** | `remotion-composer/src/Root.tsx:132`: `durationInFrames = Math.ceil((lastEnd + 1) * 30)`, tức thời lượng render = **`max(cut.out_seconds) + 1.0s`**. **Đã đo thật:** cuts cộng lại 15,0s → render 16,0s = **+6,7%**. Trong khi `pipeline_defs/animated-explainer.yaml` (stage compose) yêu cầu *"Duration within +/-5% of target"* | **Một kế hoạch ngây thơ sẽ tự fail gate của chính nó:** đặt `out_seconds` cuối = 45 cho mục tiêu 45s sẽ render ra 46s (+2,2%... vẫn trong ngưỡng) nhưng nếu mục tiêu là video ngắn 10s thì +1s = +10% và **fail**. Không tài liệu nào nhắc tới đuôi +1s này | Ghi quy tắc vào `skills/pipelines/explainer/edit-director.md`, hoặc bỏ đuôi +1s khi `cuts` đã bao trùm toàn bộ thời lượng |
| **18** | 🔴 **MÂU THUẪN CỨNG: không tồn tại `edit_decisions` vừa hợp lệ schema vừa render được bằng Remotion** | `props` gửi cho Remotion **chính là** `edit_decisions` (`tools/video/video_compose.py:1957,1970`), nên prop của scene (`type`, `text`, `stat`, `chartData`, `color`, …) **buộc phải** nằm trên `cuts[]`. Nhưng `schemas/artifacts/edit_decisions.schema.json:66` đặt `additionalProperties: false` trên `cuts[]` và danh sách property (`:15-64`) **không có** các key đó. Và `lib/checkpoint.py:145-157` validate `edit_decisions` mỗi khi ghi checkpoint. **Đã chứng minh bằng thực nghiệm:** cuts có prop scene → `CheckpointValidationError: Additional properties are not allowed ('color', 'text', 'type' were unexpected)`; cuts sạch → checkpoint OK nhưng render ra video trống | **Toàn bộ đường Remotion của pipeline `animated-explainer` bị chặn.** Không thể đi từ stage `edit` tới `compose` bằng đường templated. Bộ QA của repo **không phát hiện** vì `tests/qa/test_08_end_to_end.py` dùng `operation="compose"` (đường FFmpeg, clip video) chứ không dùng component scene. `render_demo.py` thì render thẳng file props JSON và **bỏ qua** cả `video_compose` lẫn checkpoint — nên hai đường này vốn tách rời nhau | Thêm các key prop scene vào `cuts[]` trong `edit_decisions.schema.json` (cách sửa đúng nhất), **hoặc** cho `video_compose` đọc prop scene từ `metadata`/`scene_plan`, **hoặc** chuyển sang `composition_mode: "atelier"` + `bespoke.props_path` (đường này nhận props JSON tuỳ ý và không cần cut-schema) |
| 19 | Cùng lớp lỗi với #18: khoá `captions` cũng không hợp lệ ở top-level `edit_decisions`, nên **caption burn kiểu Remotion cũng bị chặn** | `remotion-composer/public/demo-props/*.json` dùng khoá `captions`, và `video_compose` chuyển `edit_decisions` nguyên văn làm props — nhưng schema không khai báo `captions`. Chỉ `metadata` (và `cuts[].*` sau khi vá) mới chứa được dữ liệu ngoài schema | Phụ đề từng từ (word-level) trên đường Remotion không thể đi qua một artifact hợp lệ. Lần chạy thật đã phải dùng SRT thay vì Remotion captions | Cùng cách sửa như #18 |
| 20 | `export_bundle` nhận metadata ở **top-level**, không phải trong object `metadata` — và **nuốt im lặng** phần sai | `ExportBundle.input_schema` khai `video_path, title, project_name, export_dir, description, tags, hashtags, chapters, subtitles_path, thumbnail_path, thumbnail_concept, platform, visibility, timestamp`, required chỉ `video_path` và `title`. **Đã gặp thật:** gọi với `metadata={...}` lồng nhau → trả `success: True` nhưng bundle ghi `description: ""`, `tags: []`, `chapters: []` | Tool báo thành công trong khi metadata bị mất — lại đúng loại lỗi im lặng khó phát hiện. Chỉ phát hiện được vì tôi đối chiếu `success` với nội dung file bundle | Cảnh báo khi `metadata` được truyền mà các field tương ứng trống; hoặc chấp nhận cả hai shape |
| 21 | **`CaptionOverlay` làm mất dấu cách giữa các từ — phụ đề hiển thị dính liền nhau** | `CaptionOverlay.tsx:128` render `{w.word}{wordSeparator}` **bên trong** một `<span>` có `display: "inline-block"` + `whiteSpace: "nowrap"`. Theo quy tắc gộp khoảng trắng của CSS, space ở **cuối** một inline-block bị loại bỏ — nên dấu cách có trong DOM nhưng **vô hình**. **Đã gặp thật:** phụ đề burn lên video đọc thành `all.Threeseparatethingsstopit.` | Phụ đề từng từ của **mọi video dùng Remotion captions** đều bị lỗi này, không riêng gì lần chạy này. Rất khó phát hiện vì chỉ nhìn thấy khi xem frame đã render — `final_review` báo `subtitles_present: true, coverage_ratio: 1.0` và **không hề** báo lỗi | ✅ **ĐÃ VÁ trong repo này:** thay ký tự phân cách bằng `marginRight: 0.28em`, thứ mà việc gộp khoảng trắng không xoá được; giữ nguyên hành vi cho CJK (separator rỗng → không margin) |
| 22 | **Phụ đề sinh thẳng từ ASR sẽ burn chữ SAI lên video** | `transcriber` (faster-whisper `base`) đạt `word_accuracy: 0.903` trên chính narration này — nghĩa là ~10% số từ bị nghe sai. **Đã gặp thật:** Whisper nghe "Three separate" thành **"Pre-separate"**, và chuỗi đó được burn lên video. Ngoài ra số từ lệch (script 124 vs transcript 121) | `final_review` coi đây là **đạt** (`transcript_matches_script: true`, `issues: []`) vì ngưỡng của nó thấp hơn mức cần cho phụ đề hiển thị cho người xem. Một quy trình lấy caption trực tiếp từ ASR sẽ ship chữ sai mà không có cảnh báo nào | **Cách đúng:** dùng **chữ từ `script`** và **timing từ ASR**, căn hai chuỗi bằng `difflib.SequenceMatcher` rồi nội suy các từ không khớp. Lần chạy này đã làm vậy: 124 cue, căn khớp 90,3%, chữ hiển thị đúng |

> 🔧 **Phát hiện #18 đã được vá trong bản làm việc này.** `schemas/artifacts/edit_decisions.schema.json` đã được thêm các key prop scene vào `cuts[]` (giữ nguyên `additionalProperties: false`), nhờ đó pipeline `animated-explainer` chạy được đầu-cuối trên đường Remotion — xem [9.6](#96-ví-dụ-đã-chạy-thật-đầu-cuối-zero-key). Đây là **thay đổi hợp đồng của repo**, không phải của upstream; nếu bạn cập nhật từ upstream thì bản vá sẽ mất và blocker quay lại. Cách sửa bền vững hơn là cho `video_compose` đọc prop scene từ `metadata` hoặc `scene_plan` thay vì từ `cuts[]`.
>
> Các phát hiện trên đều **kiểm chứng được bằng `file:dòng`**. Với điều kiện bạn đã làm đủ [mục 4](#4-cài-đặt) (đặc biệt là `npm install` trong `remotion-composer`), chúng **không chặn** kịch bản 1–3 ở trên.
>
> Riêng **#1**, **#4**, **#7** và **#11** có thể khiến bạn mất thời gian debug nếu gặp — nên biết trước. **#11** đặc biệt quan trọng: nếu bạn bỏ qua bước `npm install`, bạn sẽ mất khả năng dựng video từ ảnh, và thông báo lỗi sẽ không nói thẳng ra điều đó.
>
> Nếu bạn định **sửa** repo này: #8 và #9 là hai chỗ dễ gây hiểu nhầm nhất cho người mới (sửa `config.yaml` mà không thấy gì thay đổi; làm theo ví dụ checkpoint trong `docs/ARCHITECTURE.md` rồi bị từ chối).

### 12.3 Giới hạn kiểm chứng của tài liệu này

Để bạn biết chính xác tài liệu đáng tin ở đâu:

| Nội dung | Mức kiểm chứng |
|----------|----------------|
| Yêu cầu hệ thống, luồng cài đặt, danh sách phụ thuộc | ✅ Đọc trực tiếp `Makefile`, `requirements*.txt`, `.github/workflows/ci.yml`, `.python-version` |
| Kịch bản 1 (lệnh render demo) | ✅ **ĐÃ CHẠY THẬT VÀ XÁC NHẬN.** `npm install` → 199 package, exit 0 (~2 phút). `npx remotion render src/index.tsx Explainer ... --props public/demo-props/world-in-numbers.json --codec h264` → exit 0, 690 frame, ra `projects/demos/renders/world-in-numbers.mp4` **4,09 MB** |
| Kịch bản 2 (smoke test) | ✅ Đọc trực tiếp `tests/qa/test_08_end_to_end.py`, `test_05_video_compose.py`, `QA_PLAN.md` — ⚠️ **chưa chạy thật** (máy này không có Python thật và không có FFmpeg) |
| Hợp đồng tool (`video_compose`, `piper_tts`…) | ✅ Đọc `input_schema` và code định tuyến trong `tools/video/video_compose.py` |
| **Remotion render với đúng 6 scene type dự kiến** | ✅ **ĐÃ CHẠY THẬT:** `text_card` + `stat_card` + `bar_chart` + `callout` + `comparison` + overlay `section_title`, theme `clean-professional` → `spike_sky.mp4`, h264 960×540, **46,06 s**, 2,32 MB, exit 0 |
| **Đường tích hợp `video_compose` → Remotion** | ✅ **ĐÃ CHẠY THẬT:** `operation="render"`, `render_runtime="remotion"`, `renderer_family="explainer-data"` → `success: True`, `final_review_status: pass`, h264 1920×1080 30fps, audio mux thành công, render mất 117,4 s cho 16 s video |
| **Mâu thuẫn schema `edit_decisions`** (phát hiện #18) | ✅ **ĐÃ CHỨNG MINH:** `_validate_artifacts_for_stage("edit", "completed", …)` ném `CheckpointValidationError` với cuts có prop scene, và PASS với cuts sạch |
| **Piper TTS tổng hợp giọng** | ✅ **ĐÃ CHẠY THẬT:** 76 ký tự → `spike_piper.wav`, pcm_s16le 22050 Hz mono, **4,69 s** — sau khi tải voice model và truyền đường dẫn tuyệt đối (xem mục 5) |
| API checkpoint | ✅ Đọc `lib/checkpoint.py` — `init_project(project_id, *, title, pipeline_type, pipeline_dir=None, style_playbook=None)`; `get_next_stage(pipeline_dir, project_id, pipeline_type=None)` |
| Schema artifact & checkpoint | ✅ Đọc `schemas/artifacts/*.json` (20 schema) và `schemas/checkpoints/checkpoint.schema.json` |
| Backlot (cổng, bind address, suy giảm êm) | ✅ Đọc `backlot/__main__.py`, `backlot/__init__.py`, `backlot/server.py`, `backlot/state.py` |
| Validate 2 manifest `framework-smoke` / `animated-explainer` | ⚠️ **Kiểm tra thủ công** bằng cách đối chiếu từng key với `additionalProperties: false` + enum trong `pipeline_manifest.schema.json` (không chạy được `jsonschema`) — kết quả: **cả hai hợp lệ** |
| Các phát hiện ở 12.2 | ✅ Kiểm chứng bằng grep + đọc file, không suy đoán |

**Máy này hiện có:** Node v24.16.0, npm 11.13.0, Git, `remotion-composer/node_modules` (199 package), Chrome Headless Shell của Remotion (đã tải ở lần render đầu).
**Máy này còn thiếu:** Python thật (chỉ có stub Microsoft Store), FFmpeg/ffprobe, GNU Make, binary `piper`.

> Vì vậy nếu bạn muốn chạy **kịch bản 2 và 3**, việc cần làm trước tiên vẫn là: cài Python 3.10+ và FFmpeg (mục [4.3](#43-cài-ffmpeg)).

---

## 13. Bảng tra cứu file quan trọng

| Câu hỏi | Xem ở đâu |
|---------|-----------|
| Hợp đồng vận hành cho agent | `AGENT_GUIDE.md` |
| Kiến trúc & quy ước | `PROJECT_CONTEXT.md`, `docs/ARCHITECTURE.md` |
| Cài đặt có gì | `Makefile`, `requirements.txt`, `.env.example` |
| Hệ thống có tool gì | `tools/tool_registry.py` → `provider_menu_summary()` |
| Pipeline gồm những stage nào | `pipeline_defs/<pipeline>.yaml` |
| Stage này phải làm gì | `skills/pipelines/<pipeline>/<stage>-director.md` |
| Artifact phải có field gì | `schemas/artifacts/` |
| Chính sách checkpoint/review | `skills/meta/checkpoint-protocol.md`, `skills/meta/reviewer.md` |
| Style playbook | `styles/*.yaml` |
| Provider nào cần key nào | `docs/PROVIDERS.md` + trường `install_instructions` trong registry |
| Prompt mẫu đã kiểm nghiệm | `PROMPT_GALLERY.md` |
| Bộ test QA chạy được | `tests/qa/QA_PLAN.md` |
| Theo dõi tiến trình | `backlot/README.md` |
| Cấu hình ngân sách / output | `config.yaml` |

---

*Tài liệu này được tạo bằng cách đọc trực tiếp source code trong repo. Khi source thay đổi, hãy ưu tiên registry và `AGENT_GUIDE.md` hơn tài liệu này — nguyên tắc của chính OpenMontage là "đừng tin doc cũ, hãy hỏi registry".*
