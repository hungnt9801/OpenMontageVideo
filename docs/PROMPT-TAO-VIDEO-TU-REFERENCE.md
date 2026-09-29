# PROMPT TẠO VIDEO TỪ REFERENCE
### Nguồn tham chiếu: https://www.youtube.com/shorts/O-xrpM9lOqs

> **Cách dùng:** Mục **1** là kết quả phân tích video gốc (grounding). Mục **2** là PROMPT MẪU
> (master template) — copy dán vào trợ lý AI để sinh ra một video cùng phong cách nhưng
> khác nội dung. Mục **3** là một prompt đã điền sẵn hoàn chỉnh (ví dụ: *Nhà sư và ngọn đèn dầu*).
> Mục **4** là prompt cho từng công cụ (video gen / image gen / overlay / TTS / music) để
> dùng khi không chạy qua OpenMontage. Mục **5** là cấu hình render + checklist.

---

## 1. PHÂN TÍCH VIDEO GỐC (Video Reference Analysis)

### 1.1 Dữ liệu kỹ thuật (lấy từ nguồn công khai — YouTube oEmbed + metadata trang watch)

| Trường | Giá trị |
|---|---|
| Tiêu đề | *Triết lý nhân sinh: Nhà Sư Và Chiếc Bát Rỗng – Câu Chuyện Khiến Ai Cũng Giật Mình Nhìn Lại!* |
| Kênh | Thiền Âm Nhạc (`@Thien-amnhac`) |
| Đăng | 2025-03-25 |
| Thời lượng | **96 giây** |
| Lượt xem (tại thời điểm phân tích) | **~187.552** |
| Định dạng | **Shorts 9:16 dọc** (thumbnail gốc 1280×720 là khung ngang có viền mờ; video thật là dọc) |
| Ngôn ngữ | Tiếng Việt (có track caption `vi`, loại `asr` — tự động) |
| Thể loại | Truyện kể triết lý nhân sinh / Phật giáo + nhạc thiền |

### 1.2 Nội dung (Content)

Truyện ngụ ngôn về **hai nhà sư cùng ấp ủ một ước nguyện: hành hương đến Ấn Độ**.
Nhà sư giàu cứ loay hoay chuẩn bị, chờ "đủ điều kiện"; nhà sư nghèo chỉ có **một chiếc bát
xin ăn** đã lên đường và **hoàn thành chuyến đi trước**. Bài học: cuộc sống không đợi bạn
đủ đầy mới cho phép bạn bước đi — thành công đến từ niềm tin và dũng cảm hành động,
không phải từ sự chuẩn bị hoàn hảo.

**Kết cấu cảm xúc:** đặt câu hỏi đánh trúng nỗi trì hoãn của người xem → kể truyện →
"cú twist" (người nghèo về trước) → chiêm nghiệm → kêu gọi nhìn lại chính mình.

### 1.3 Phong cách (Style)

Hình ảnh **CGI/AI cinematic tả thực** ấm — kiểu phim ngắn Phật giáo: sư mặc áo nâu/vàng
nghệ, chùa cổ, **lá vàng mùa thu**, nắng chiều golden hour, bố cục dọc, chủ thể đi bộ ở
trung tâm khung. Màu chủ đạo: **nâu đất – vàng nghệ – vàng lá – nâu tối**, tương phản mạnh
với chữ vàng trên nền sẫm.

Nhịp: **chậm, thiền định** — mỗi khung giữ 2–4 giây, chuyển động êm, ít cắt nhanh; thay vì
cắt cảnh liên tục, video giữ "nhịp thở" và tạo thay đổi bằng **overlay chữ + chuyển động
camera chậm (dolly/push-in rất nhẹ)**.

### 1.4 Cấu trúc (Structure)

~96 giây, chia **7 khối** theo mô-típ truyện kể:

| # | Thời lượng | Khối | Chức năng |
|---|---|---|---|
| 1 | 0:00–0:07 | **HOOK** | Câu hỏi trực diện: *"Bạn có đang chờ 'thời điểm hoàn hảo'?"* |
| 2 | 0:07–0:20 | **BỐI CẢNH** | Hai nhà sư, cùng một ước nguyện: hành hương Ấn Độ |
| 3 | 0:20–0:45 | **DIỄN BIẾN** | Sư giàu chuẩn bị mãi; sư nghèo chỉ có chiếc bát rỗng → lên đường |
| 4 | 0:45–0:62 | **TWIST** | Sư nghèo hoàn thành chuyến đi trước, trở về |
| 5 | 0:62–0:78 | **BÀI HỌC** | Cuộc sống không đợi bạn đủ đầy |
| 6 | 0:78–0:90 | **CHIÊM NGHIỆM** | Chiếc bát rỗng = tâm rỗng, không bị "đầy" bởi sự chuẩn bị |
| 7 | 0:90–0:96 | **CTA/LOOP** | *"Hành trình vạn dặm… luôn bắt đầu từ một bước chân."* |

### 1.5 Motion (phân loại chuyển động — quyết định đường sản xuất)

> **Kiểm chứng:** không truy cập được storyboard/caption của video để đo `motion_type` tự động
> (YouTube chặn timedtext + storyboard signature trong phiên này, và máy chưa có Python để chạy
> `video_analyzer`). Phân loại dưới đây là **suy luận có căn cứ** từ thumbnail gốc 1280×720 +
> mô-típ của thể loại, **không phải số đo từ tool**. Nếu cần số liệu chính xác, xem mục 6.

- Phần lớn khung là **motion_clip** (clip AI chuyển động: sư đi bộ, lá rơi, khói hương bay,
  nước chảy) — chiếm khoảng 70–80% thời lượng.
- Khoảng 20–30% là **animated_still** (ảnh tĩnh + pan/zoom rất chậm, thường ở các khối
  "bài học" và "chiêm nghiệm" để chèn overlay chữ dài).
- **Không** phải slideshow ảnh tĩnh thuần.

### 1.6 Phân rã 5 aspect (CMU/Harvard CHAI) — dạng canonical

```
SUBJECT
  • Chính: một nhà sư nam ~35–45 tuổi, đầu cạo, đeo kính gọng mảnh, áo nâu/vàng nghệ
    (y/cà-sa quấn vai), chân đất, dáng thư thái. Đây là "identity anchor" phải lặp lại
    nguyên văn ở mọi shot.
  • Phụ: một nhà sư lớn tuổi (thầy/người đối thoại) — đầu cạo, râu bạc ngắn, áo nâu sẫm.
  • Transitions: switching (cắt giữa hai nhà sư khi đối thoại), revealing (sư nghèo xuất
    hiện giữa lá vàng rơi), disappearing (sư giàu khuất sau cột chùa).

SUBJECT MOTION
  • Sư chính: bước chậm, mắt nhìn xuống, tay ôm chiếc bát gỗ/đất nung trước bụng →
    dừng lại → ngẩng nhìn lên → bước tiếp.
  • Sư phụ: ngồi yên trên bậc đá, tay nâng tách trà, gật đầu rất chậm.
  • Tương tác: trao/đỡ chiếc bát, đặt bát xuống bàn đá, cúi đầu chào.
  • Thứ tự thời gian: chậm và liên tục — KHÔNG có hành động dồn dập.

SCENE
  • Setting: sân chùa cổ Việt/Đông Á, cột gỗ sẫm, mái ngói cong, hành lang đá,
    sân lát đá phủ lá vàng, cây bồ đề/cây phong lớn, bàn đá, lư hương.
  • Thời điểm: cuối thu, **golden hour** (nắng chiều ấm, bóng dài).
  • Dynamics: lá vàng rơi chậm, khói hương bay lên, bụi nắng (dust motes) trong tia sáng,
    hơi nước mờ nhẹ ở hậu cảnh.
  • POV: objective/neutral (không POV đặc biệt).
  • OVERLAYS (liệt kê RIÊNG, không trộn vào setting):
      1. Tiêu đề 1–2 dòng, chữ in hoa, vàng (#F5C518) + vàng cam (#E08A2B), có viền/đổ
         bóng đen, cỡ lớn (≈ 64–86 px ở 1080p), nằm ở **1/3 trên** khung.
      2. Chữ Hook và chữ kết: trắng đậm, viền đen 3px, cỡ 52–64 px.
      3. Caption chạy theo lời đọc: trắng, viền đen, đặt trong safe zone, tối đa 2 dòng.
      4. Watermark/logo kênh: mờ, ở rìa trên.
      5. KHÔNG có progress bar, KHÔNG lower-third đồ hoạ.

SPATIAL FRAMING
  • Shot size: chủ yếu MS (trung cảnh, thấy 2/3 người) và WS (toàn cảnh sân chùa);
    chèn CU (cận mặt sư) ở các beat cảm xúc và ECU (bàn tay + bát) ở beat "chiếc bát rỗng".
  • Vị trí chủ thể: **giữa khung theo trục dọc** (bắt buộc với 9:16), chừa khoảng trên
    cho tiêu đề và khoảng dưới cho caption.
  • Depth: FG lá vàng mờ → MG nhà sư sắc nét → BG chùa tan mờ (3 lớp rõ rệt).
  • Height-relative: máy ngang tầm ngực/ngang mắt chủ thể, hơi thấp ở shot toàn để tôn dáng.
  • Thay đổi: khi chủ thể bước tới, khung từ WS siết dần về MS (framing changes by camera
    movement, không phải subject movement).

CAMERA
  • Playback speed: real-time; có 1–2 shot **slow-motion nhẹ** (0.7–0.8×) cho lá rơi/khói hương.
  • Lens: 35–50 mm, không méo; một vài shot ECU dùng tele 85 mm + shallow DoF.
  • Height: ngang ngực (chest-level) phần lớn; ECU hạ xuống ngang bàn tay.
  • Angle: level angle; 1–2 shot low angle nhẹ khi sư nghèo bước đi (tôn dáng).
  • Focus/DoF: shallow, **focus tracking** theo chủ thể đang bước.
  • Steadiness: gimbal — mượt, không rung.
  • Movement: dolly-in rất chậm (push) ở hook và twist; truck phải chậm theo bước chân;
    tilt up nhẹ ở các beat chiêm nghiệm; tuyệt đối tránh pan nhanh / whip.

AUDIO
  • Giọng đọc: nam, trầm, chậm, ấm — phong cách "kể chuyện thiền", tốc độ ~135–150 wpm.
  • Nhạc nền: ambient/thiền — piano thưa + sáo trúc/sound bowl, KHÔNG trống, không beat.
  • SFX: lá rơi, tiếng bước chân trên đá, chuông xa, khói hương (rất khẽ).
  • Mix: nhạc −24 dB dưới giọng đọc; đích −14 LUFS, true peak −1 dBTP.
```

### 1.7 Vì sao video này hiệu quả (What makes it work)

1. **Hook bằng câu hỏi đánh trúng nỗi đau** — "Bạn có đang chờ thời điểm hoàn hoàn?" —
   biến một câu chuyện cổ thành vấn đề cá nhân của người xem trong 3 giây đầu.
2. **Tiêu đề mang tính "curiosity gap"** — "Chiếc Bát Rỗng" + "Khiến Ai Cũng Giật Mình
   Nhìn Lại" tạo mâu thuẫn ngữ nghĩa (cái rỗng mà lại làm nên chuyện) → buộc phải xem để giải mã.
3. **Nghịch lý làm điểm twist** — người tưởng như kém cỏi nhất (chỉ có chiếc bát rỗng) lại
   về đích trước. Cấu trúc "ai cũng nghĩ A, nhưng thật ra B" (misconception-first).
4. **Ngôn ngữ thị giác thống nhất tuyệt đối** — mọi khung đều cùng một mỹ học: sư – chùa –
   lá vàng – nắng chiều. Không có khung nào "lạc tông", nên video trông như phim chứ không
   phải ghép ảnh.
5. **Overlay chữ gánh phần retention** — chữ vàng lớn ở phần trên khung giữ người xem muted
   (85% người xem mobile tắt tiếng), và nhịp đổi chữ tạo "pattern interrupt" thay cho cắt cảnh.
6. **Kết bằng CTA nhẹ + vòng lặp** — câu cuối ngắn, đọc chậm, dễ nhớ, hợp để xem lại (loop).

---

## 2. PROMPT MẪU (MASTER TEMPLATE) — dán vào trợ lý AI / OpenMontage

> Đây là prompt **duy nhất** bạn cần. Thay phần `[...]` bằng chủ đề của bạn.
> Prompt viết theo đúng hợp đồng của OpenMontage: `render_runtime`, `composition_mode`,
> 5 aspect, identity anchor, safe zone 9:16, Layer-3 skill gate.

```text
Hãy sản xuất một video Shorts 9:16 (1080×1920) dài 90–100 giây theo phong cách của
video tham chiếu https://www.youtube.com/shorts/O-xrpM9lOqs (kênh Thiền Âm Nhạc):
truyện kể triết lý nhân sinh Phật giáo, hình ảnh cinematic AI tả thực, chùa cổ mùa thu
lá vàng, nắng golden hour, nhịp chậm thiền định, overlay tiêu đề chữ vàng lớn.

CHỦ ĐỀ CỦA TÔI: [ví dụ: "Nhà sư và ngọn đèn dầu"]
BÀI HỌC TRUNG TÂM: [1 câu, ví dụ: "Ánh sáng không đến từ việc giữ lại, mà từ việc trao đi."]
KHÁN GIẢ: người Việt 25–55, quan tâm chánh niệm / phát triển bản thân / đang trì hoãn.
NGÔN NGỮ: tiếng Việt. GIỌNG ĐỌC: nam trầm ấm, chậm rãi, kiểu kể chuyện thiền.

YÊU CẦU BẮT BUỘC

1) NỘI DUNG — cấu trúc 7 khối, tổng 90–100s, lời đọc 210–250 từ:
   1. HOOK (0–7s): một câu hỏi/khẳng định đánh trúng nỗi đau của người xem, nói thẳng
      vào "bạn". Hiện chữ ngay từ giây 0.5.
   2. BỐI CẢNH (7–20s): giới thiệu nhân vật + ước nguyện chung của họ.
   3. DIỄN BIẾN (20–45s): hai lựa chọn trái ngược — người chờ đợi / người hành động.
   4. TWIST (45–62s): kết quả bất ngờ, đảo ngược kỳ vọng của người xem.
   5. BÀI HỌC (62–78s): phát biểu bài học bằng 1 câu ngắn, mạnh.
   6. CHIÊM NGHIỆM (78–90s): liên hệ biểu tượng trung tâm với đời sống người xem.
   7. CTA + LOOP (90–96s): 1 câu chốt dễ nhớ + gợi ý like/theo dõi; câu chốt phải nối
      được về câu hook để tạo vòng xem lại.

2) HÌNH ẢNH — 8–12 shot, mỗi shot 6–10 giây. Toàn bộ dùng CHUNG một từ vựng mỹ học:
   - IDENTITY ANCHOR (lặp nguyên văn ở mọi shot, không dùng đại từ):
     "nhà sư nam ~40 tuổi, đầu cạo nhẵn, đeo kính gọng mảnh, áo nâu vàng nghệ quấn vai,
      chân đất, dáng thư thái".
   - BỐI CẢNH: sân chùa cổ Đông Á, cột gỗ sẫm, mái ngói cong, sân đá phủ lá vàng,
     cây bồ đề lớn, lư hương, cuối thu, nắng chiều golden hour, bóng dài.
   - ĐỘNG: lá vàng rơi chậm, khói hương cuộn, bụi nắng trong tia sáng, hơi nước mờ hậu cảnh.
   - MỖI SHOT phải ghi rõ 5 aspect: Subject / Subject Motion / Scene (+overlay riêng) /
     Spatial Framing / Camera. Camera chỉ dùng: dolly-in rất chậm, truck phải chậm theo
     bước chân, tilt up nhẹ, gimbal mượt, focus tracking, shallow DoF. Cấm pan nhanh, whip,
     rung tay, zoom số.
   - Chừa khoảng trống ở 1/3 trên (cho tiêu đề) và 1/5 dưới (cho caption) — chủ thể luôn
     ở giữa khung theo trục dọc.
   - KHÔNG để model sinh chữ trong clip. Mọi chữ do lớp overlay vẽ.

3) OVERLAY CHỮ (lớp riêng, không phải nội dung của clip):
   - Tiêu đề 2 dòng, in hoa, vàng #F5C518 + cam #E08A2B, viền đen + đổ bóng, cỡ 72–86 px,
     ở 1/3 trên, hiện từ giây 0 bằng hiệu ứng scale-pop 0.25s.
   - Hook và câu chốt: trắng đậm, viền đen 3 px, 56–64 px.
   - Caption theo lời đọc: trắng, viền đen, tối đa 2 dòng × 30 ký tự, nằm trong safe zone
     900×1400 px; highlight từng từ đang đọc bằng màu vàng.
   - Không logo lớn, không lower-third, không progress bar.

4) ÂM THANH:
   - TTS tiếng Việt, giọng nam trầm, tốc độ 135–150 wpm, nghỉ 0.4–0.6s giữa các khối,
     nghỉ 1.5s sau câu bài học (im lặng có chủ đích).
   - Nhạc: ambient thiền — piano thưa + sáo trúc/sound bowl, 60–75 BPM, KHÔNG trống,
     vào ngay từ giây 0 (không intro im lặng), duck xuống −24 dB dưới giọng đọc.
   - SFX rất khẽ: lá rơi, bước chân trên đá, chuông chùa xa, khói hương.
   - Chuẩn mix: −14 LUFS, true peak −1 dBTP.

5) QUY TRÌNH & KỸ THUẬT:
   - render_runtime: [Remotion / HyperFrames] — nêu rõ ưu/nhược của từng cái cho brief này
     rồi để tôi chốt; composition_mode: atelier (hand-authored, không dùng scene-type
     đóng hộp) nếu đây là video chủ lực.
   - Đường sản xuất: [video gen cho shot chuyển động] + [ảnh gen cho khối bài học] +
     overlay + TTS + nhạc; hoặc toàn bộ bằng ảnh gen + chuyển động camera nếu tiết kiệm.
   - Đọc Layer-3 skill trước khi viết prompt cho từng tool: ai-video-gen / seedance-2-0 /
     veo / flux-best-practices / elevenlabs hoặc text-to-speech / music.
   - Sản xuất SAMPLE 12–15 giây trước (hook + 1 shot giữa), tôi duyệt rồi mới chạy full.

6) ĐẦU RA:
   Trước khi generate, đưa tôi: (a) 3 phương án concept khác nhau,
   (b) script đầy đủ theo timeline + số từ từng khối,
   (c) scene_plan 8–12 shot với prompt 5-aspect cho từng shot,
   (d) bảng chi phí theo provider, (e) kế hoạch nhạc.
   Chờ tôi duyệt rồi mới sinh asset.
```

---

## 3. VÍ DỤ ĐÃ ĐIỀN SẴN — "NHÀ SƯ VÀ NGỌN ĐÈN DẦU"

### 3.1 Tóm tắt concept

**Bài học:** Ánh sáng không đến từ việc giữ lại, mà từ việc trao đi.
**Twist:** Nhà sư giữ ngọn đèn "để dành cho đêm quan trọng nhất" — đêm đó ông ngồi trong
bóng tối, còn người ăn mày ông từng cho lửa lại là người thắp sáng cả sân chùa.
**Tương phản với bản gốc:** bản gốc là *chờ đủ điều kiện mới hành động*; bản này là
*giữ lại vì sợ mất*. Cùng mỹ học, cùng nhịp, nhưng twist và biểu tượng khác.
**Điểm khác biệt (không sao chép):** biểu tượng trung tâm là **lửa/ngọn đèn** thay vì
**chiếc bát**, và có thêm nhân vật người ăn mày → tăng tương tác thị giác.

### 3.2 Script + timeline (96 giây, ~235 từ, 140 wpm)

```
[0:00–0:07] HOOK
Lời đọc: "Có một thứ bạn đang giữ lại… vì nghĩ rằng mình sẽ cần nó vào một ngày quan trọng hơn.
Nhưng ngày đó… không bao giờ đến."
Overlay: "NHÀ SƯ VÀ NGỌN ĐÈN DẦU" / "Bạn đang giữ lại điều gì?"
Camera intent: WS sân chùa lúc chạng vạng, dolly-in rất chậm về phía chính điện, khói hương.

[0:07–0:20] BỐI CẢNH
Lời đọc: "Ở một ngôi chùa cổ, có một nhà sư chỉ giữ cho mình một ngọn đèn dầu.
Ông không thắp nó. Ông để dành. Ông nói: ta sẽ thắp nó vào đêm quan trọng nhất."
Camera intent: MS chính diện, nhà sư — đầu cạo nhẵn, kính gọng mảnh, áo nâu vàng nghệ —
nâng ngọn đèn dầu trong hai tay, ngọn lửa chưa cháy; truck phải chậm theo tay.

[0:20–0:45] DIỄN BIẾN
Lời đọc: "Mùa đông đến. Một người ăn mày gõ cửa xin một chút lửa để sưởi.
Nhà sư nhìn ngọn đèn còn nguyên. Ông lắc đầu. Ông nói: để dành đã.
Người ăn mày cúi đầu, bước ra ngoài sân, và tự nhóm một đốm lửa nhỏ từ hai thanh củi."
Camera intent: ECU bàn tay + ngọn đèn chưa cháy → switching (rack focus) sang người ăn mày
ngoài cổng; CU gương mặt nhà sư, ánh mắt hạ xuống.

[0:45–0:62] TWIST
Lời đọc: "Đêm quan trọng nhất đến — đêm chùa mất điện, cả sân chìm trong bóng tối.
Nhà sư châm ngọn đèn của mình. Một ngọn. Rồi ông nhìn ra sân:
người ăn mày đã thắp sáng cả dãy đèn đá, bằng thứ lửa ông từng được cho."
Camera intent: WS sân chùa tối, tilt up nhẹ theo ngọn đèn; subject revealing — dãy đèn đá
lần lượt sáng lên khi camera truck trái chậm.

[0:62–0:78] BÀI HỌC
Lời đọc: "Ánh sáng không vơi đi khi được chia. Nó chỉ vơi đi khi bị giữ lại."
Overlay: "ÁNH SÁNG KHÔNG VƠI KHI ĐƯỢC CHIA"
Camera intent: MS nhà sư — đầu cạo nhẵn, kính gọng mảnh, áo nâu vàng nghệ — ngồi trên bậc
đá, đèn đặt cạnh; static camera, shallow DoF, (im lặng 1.5s sau câu này).

[0:78–0:90] CHIÊM NGHIỆM
Lời đọc: "Bạn cũng có một ngọn lửa: thời gian, sự tử tế, một lời bạn chưa nói.
Nếu cứ để dành cho 'đêm quan trọng nhất', nó sẽ cháy hết trong im lặng."
Camera intent: CU bàn tay mở ra, ánh lửa hắt lên lòng bàn tay; focus tracking.

[0:90–0:96] CTA + LOOP
Lời đọc: "Hôm nay, hãy thắp một ngọn. Dù chỉ một ngọn."
Overlay: "Hành trình vạn dặm… bắt đầu từ một bước chân."
Camera intent: WS sân chùa, dolly-out rất chậm tới khi sân chùa sáng đèn — khung cuối
gần trùng khung đầu để tạo vòng lặp.
```

### 3.3 Scene plan — prompt 5-aspect cho từng shot (dùng trực tiếp cho video gen)

> Mọi shot dùng chung khối **STYLE** này (lặp lại nguyên văn ở mỗi prompt):
>
> `STYLE: cinematic photoreal CGI, ancient East-Asian temple courtyard in late autumn,
> wet stone paving covered with fallen yellow leaves, dark timber columns, curved tiled
> roof, bronze incense burner, golden-hour-to-dusk warm light, volumetric sun shafts,
> shallow depth of field, 35mm film grain, warm amber-and-brown palette, gimbal-smooth.`
>
> `CONSTRAINT: no text, no logos, no subtitles, no watermark rendered inside the clip.
> Subject centered on the vertical axis, headroom reserved in the upper third, lower fifth clear.`

```
SHOT 1 — HOOK (8s) — "sân chùa chạng vạng"
Subject: một nhà sư nam ~40 tuổi, đầu cạo nhẵn, đeo kính gọng mảnh, áo nâu vàng nghệ quấn vai,
         chân đất, dáng thư thái (không ai khác trong khung).
Subject Motion: đứng yên quay lưng về phía máy, hai tay chắp trước bụng; hơi nghiêng đầu
         sang phải rồi trở lại.
Scene: sân chùa cổ Đông Á cuối thu, sân đá phủ lá vàng, cột gỗ sẫm, lư hương; chạng vạng,
         sương mờ nhẹ; lá vàng rơi chậm, khói hương cuộn lên.
         Overlays: NONE (chữ do lớp overlay riêng vẽ).
Spatial: WS, chủ thể ở giữa khung theo trục dọc, FG lá vàng mờ - MG sư sắc nét - BG chùa tan mờ,
         máy ngang ngực, level angle.
Camera: 40mm, gimbal, real-time, shallow DoF, dolly-in rất chậm (khoảng 1m trong 8 giây).
Audio: gió nhẹ, lá xào xạc, chuông chùa xa rất khẽ.
```

```
SHOT 2 — BỐI CẢNH (7s) — "nâng ngọn đèn trong hai tay"
Subject: nhà sư nam ~40 tuổi, đầu cạo nhẵn, kính gọng mảnh, áo nâu vàng nghệ, chân đất.
Subject Motion: hai tay nâng một ngọn đèn dầu đất nung (ngọn lửa CHƯA cháy), từ từ đưa lên
         ngang ngực, mắt nhìn xuống ngọn đèn, rồi ngẩng lên nhìn về phía xa.
Scene: hành lang chùa có cột gỗ, nắng chiều xiên qua khe cột tạo tia sáng; bụi nắng lơ lửng.
         Overlays: NONE.
Spatial: MS chính diện, chủ thể giữa khung, FG cột gỗ mờ bên trái, BG hành lang tan mờ,
         máy ngang ngực, level angle.
Camera: 50mm, gimbal, focus tracking trên ngọn đèn, truck phải chậm theo tay, shallow DoF.
Audio: tiếng vải áo khẽ, chim xa, gió qua mái ngói.
```

```
SHOT 3 — DIỄN BIẾN (8s) — "ngọn đèn chưa cháy"
Subject: hai bàn tay của nhà sư (áo nâu vàng nghệ) ôm ngọn đèn dầu đất nung.
Subject Motion: ngón tay miết nhẹ vành đèn rồi dừng lại, không châm lửa.
Scene: sân chùa cuối thu, lá vàng trên nền đá, ánh chiều ấm. Overlays: NONE.
Spatial: ECU, chủ thể lấp đầy khung, FG là vành đèn sắc nét, BG tan mờ hoàn toàn,
         máy hạ xuống ngang bàn tay.
Camera: 85mm tele, shallow DoF rất mỏng, static camera, real-time.
Audio: im lặng gần như hoàn toàn, chỉ còn tiếng thở khẽ.
```

```
SHOT 4 — DIỄN BIẾN (9s) — "người ăn mày xin lửa"
Subject: nhà sư nam ~40 tuổi, đầu cạo nhẵn, kính gọng mảnh, áo nâu vàng nghệ; và một người
         ăn mày nam ~60 tuổi, râu ngắn bạc, áo vải thô vá nhiều mảnh, tay ôm bó củi khô.
Subject Motion: người ăn mày chìa hai tay ra xin; nhà sư lắc đầu rất chậm, hai tay siết ngọn
         đèn vào ngực; người ăn mày cúi đầu, quay người bước ra sân.
Scene: cổng chùa gỗ, ngoài sân mưa phùn nhẹ, lá vàng ướt. Overlays: NONE.
Spatial: MS hai người, nhà sư bên trái khung, người ăn mày bên phải, cả hai trong safe zone;
         FG là cột cổng mờ, BG sân chùa mờ; máy ngang ngực, level angle.
Camera: 40mm, gimbal, subject switching bằng rack focus từ nhà sư sang người ăn mày,
         truck phải chậm khi người ăn mày rời khung (subject disappearing).
Audio: mưa phùn, bước chân trên đá ướt, củi khô va nhau.
```

```
SHOT 5 — TWIST (9s) — "sân chùa tối, đèn đá lần lượt sáng"
Subject: dãy đèn đá (stone lantern) dọc sân chùa; bóng nhà sư — đầu cạo nhẵn, áo nâu vàng nghệ —
         ở hậu cảnh, tay cầm một ngọn đèn dầu đã cháy.
Subject Motion: camera truck trái chậm làm lộ dần từng đèn đá đã được thắp; bóng nhà sư đứng
         yên, hạ ngọn đèn xuống.
Scene: sân chùa ban đêm sau mưa, mặt đá phản chiếu ánh lửa, sương mỏng, khói hương.
         Overlays: NONE.
Spatial: WS, dãy đèn dẫn mắt từ FG bên trái vào MG, nhà sư ở BG, máy ngang ngực, level angle.
Camera: 35mm, gimbal, truck trái chậm + tilt up nhẹ, real-time, deep focus ở shot này.
Audio: gió đêm, lửa nổ tí tách, chuông chùa một tiếng xa.
```

```
SHOT 6 — BÀI HỌC (8s) — "ngồi bên ngọn đèn"
Subject: nhà sư nam ~40 tuổi, đầu cạo nhẵn, kính gọng mảnh, áo nâu vàng nghệ, ngồi trên bậc đá.
Subject Motion: ngồi yên, mắt nhìn vào ngọn lửa, hai tay đặt trên đầu gối; chỉ có hơi thở
         làm vai nhô lên rất nhẹ.
Scene: hiên chùa ban đêm, ngọn đèn dầu cháy bên cạnh, tường gỗ sẫm phía sau.
         Overlays: overlay riêng của lớp chữ (câu bài học) — không render trong clip.
Spatial: MS, chủ thể lệch nhẹ phải khung, FG ngọn đèn mờ bên trái, BG tường tối.
         Máy ngang ngực, level angle.
Camera: 50mm, static camera, shallow DoF, real-time (im lặng 1.5 giây cuối shot).
Audio: lửa cháy khẽ, không nhạc trong 1.5 giây cuối.
```

```
SHOT 7 — CHIÊM NGHIỆM (9s) — "bàn tay mở ra, ánh lửa hắt lên"
Subject: bàn tay mở của nhà sư (áo nâu vàng nghệ), lòng bàn tay hứng ánh lửa.
Subject Motion: các ngón tay từ từ mở ra hoàn toàn; ánh lửa nhảy trên lòng bàn tay.
Scene: gần ngọn đèn dầu, nền tối, khói mỏng bay ngang. Overlays: NONE.
Spatial: ECU, bàn tay ở giữa khung, BG đen tan mờ, máy ngang bàn tay.
Camera: 85mm tele, extremely shallow DoF, focus tracking theo bàn tay, slow motion 0.8×.
Audio: lửa tí tách, hơi thở chậm.
```

```
SHOT 8 — CTA/LOOP (8s) — "sân chùa sáng đèn"
Subject: toàn cảnh sân chùa với dãy đèn đá đã cháy; bóng nhà sư — đầu cạo nhẵn, áo nâu vàng nghệ —
         bước chậm vào sâu trong sân.
Subject Motion: nhà sư bước chậm, lá vàng rơi; camera lùi ra.
Scene: sân chùa ban đêm ấm sáng bởi đèn, sương mỏng, mặt đá ướt phản chiếu.
         Overlays: overlay chữ kết + gợi ý like/theo dõi — không render trong clip.
Spatial: WS, chủ thể ở giữa khung, FG lá vàng mờ, MG sân đá, BG chính điện.
         Máy ngang ngực, level angle.
Camera: 35mm, gimbal, dolly-out rất chậm, real-time, deep focus.
Audio: gió, lá rơi, nhạc ambient trở lại đầy hơn, kết bằng một tiếng chuông.
```

### 3.4 Prompt ảnh (image gen) cho các khối tĩnh — FLUX / Nano Banana / Imagen

> Dùng cho shot 3, 6, 7 nếu chọn đường "ảnh + chuyển động camera" để tiết kiệm.
> Prompt ảnh nên **mô tả tĩnh** — bỏ mọi từ chỉ chuyển động.

```text
IMG-1 (ECU ngọn đèn):
Extreme close-up of two weathered hands in saffron-brown monk robes cradling an unlit
clay oil lamp, fingertips resting on the rim, ancient East-Asian temple courtyard blurred
behind, fallen yellow autumn leaves on wet stone, warm golden-hour backlight, shallow
depth of field, cinematic photoreal, 35mm film grain, warm amber and brown palette,
vertical 9:16 composition, subject centered, negative space in the upper third.
Negative: text, watermark, logo, subtitles, extra fingers, deformed hands, cold blue tint.

IMG-2 (MS nhà sư ngồi bên đèn):
Medium shot of a calm Vietnamese Buddhist monk, about 40 years old, shaved head, thin
wire-frame glasses, saffron-brown robe draped over one shoulder, sitting on a stone step
beside a small burning clay oil lamp at night, dark timber temple wall behind, embers and
thin smoke, low-key warm key light from the lamp, shallow depth of field, cinematic
photoreal, 35mm film grain, vertical 9:16, subject slightly right of center.

IMG-3 (ECU bàn tay mở hứng ánh lửa):
Extreme close-up of an open monk's palm catching warm firelight from a small oil lamp,
fingers fully spread, deep black background, floating smoke, extremely shallow depth of
field, cinematic photoreal, warm amber highlights, vertical 9:16.
```

### 3.5 Overlay chữ — thông số để vẽ bằng Remotion/HyperFrames (không để model vẽ)

| Lớp | Nội dung | Font | Cỡ @1080×1920 | Màu | Vị trí | Hiệu ứng |
|---|---|---|---|---|---|---|
| Tiêu đề dòng 1 | NHÀ SƯ VÀ NGỌN ĐÈN DẦU | Inter/Montserrat Bold, in hoa | 78 px | #F5C518 | 1/3 trên, giữa | scale-pop 0.25s, giữ 5s rồi thu nhỏ về 46 px |
| Tiêu đề dòng 2 | Chuyện khiến ai cũng nhìn lại | Inter Bold | 52 px | #E08A2B | ngay dưới dòng 1 | fade-in +0.15s |
| Hook | "Bạn đang giữ lại điều gì?" | Inter Bold | 60 px | #FFFFFF, viền đen 3 px | giữa khung, dưới tiêu đề | gõ từng từ 0.08s/từ |
| Câu bài học | "ÁNH SÁNG KHÔNG VƠI KHI ĐƯỢC CHIA" | Inter ExtraBold | 64 px | #F5C518 | giữa khung | scale-pop + shake nhẹ 0.2s |
| Câu chốt | "Hành trình vạn dặm… bắt đầu từ một bước chân." | Inter SemiBold | 52 px | #FFFFFF | giữa khung | fade-in, giữ tới hết |
| Caption | lời đọc, tối đa 2 dòng × 30 ký tự | Inter Bold | 46 px | #FFFFFF, viền đen + highlight vàng từ đang đọc | trong safe zone 900×1400, đáy safe zone | word-by-word |
| Logo kênh | watermark mờ | — | 28 px | #FFFFFF @35% | rìa trên phải | tĩnh |

**Safe zone:** 900×1400 px canh giữa — không đặt chữ quan trọng trong 120 px trên,
300 px dưới, 96 px hai bên.

### 3.6 TTS — prompt đọc (dùng cho ElevenLabs / Google Chirp3-HD / Azure / OpenAI TTS)

```text
Ngôn ngữ: Tiếng Việt (vi-VN).
Giọng: nam, trầm, ấm, tuổi 40–55, kiểu người kể chuyện thiền — KHÔNG kiểu MC quảng cáo.
Tốc độ: 135–150 từ/phút (chậm hơn bình thường ~15%).
Cao độ: thấp, ổn định. Biểu cảm: tiết chế, chỉ nhấn ở câu bài học và câu chốt.
Xử lý nhịp:
  • Nghỉ 0.3s ở dấu phẩy, 0.6s ở dấu chấm, 0.9s khi xuống dòng giữa các khối.
  • Im lặng 1.5s sau câu "Ánh sáng không vơi đi khi được chia."
  • Câu chốt đọc chậm hơn 10%, hạ giọng ở hai từ cuối.
Phát âm: "nhà sư" (không phải "nhà xư"), "chiếc bát" (bát = /ɓaːt˧˥/), "hành hương"
  (hương = /hɨəŋ˧/). Tránh đọc rời từng tiếng — giữ ngữ điệu liền mạch.
Đầu ra: WAV 48 kHz mono cho từng khối để dễ canh timeline, kèm file timeline JSON.
```

### 3.7 Nhạc & sound design (prompt cho music gen / tiêu chí chọn track)

```text
Thể loại: ambient thiền / Asian meditation.
Nhạc cụ: piano thưa (nốt rời, nhiều khoảng lặng), sáo trúc, singing bowl / sound bowl,
  trống da rất nhẹ hoặc không trống, drone nền ấm.
Tempo: 60–75 BPM. Không có beat rõ, không build-up dồn dập.
Cấu trúc: vào ngay giây 0 (không intro im lặng) → giữ phẳng suốt 60s đầu →
  tại beat TWIST (0:45) thêm một lớp drone trầm → tại câu bài học (0:62) **nhạc tắt hoàn
  toàn 1.5s** rồi quay lại nhỏ hơn → cuối video kết bằng một tiếng chuông/kim loại dài.
Mix: −24 dB dưới giọng đọc; SFX (lá rơi, bước chân, chuông xa) ở −18 đến −14 dB.
Chuẩn: −14 LUFS, true peak −1 dBTP.
```

### 3.8 Bảng chi phí tham khảo (96 giây, 8–10 shot × ~9s)

| Hạng mục | Provider | Đơn giá | SL | Thành tiền |
|---|---|---|---|---|
| Video gen (cao cấp) | Seedance 2.0 `standard` @10s | ~$3.03/clip | 9 | ~$27 |
| Video gen (tiết kiệm) | Seedance 2.0 `fast` @5s | ~$1.21/clip | 9 | ~$11 |
| Video gen (rẻ nhất) | LTX / Wan local hoặc distill | ~$0–0.3/clip | 9 | ~$0–3 |
| Ảnh gen (shot tĩnh) | FLUX / Nano Banana | ~$0.02–0.05/ảnh | 12 | ~$0.25–0.6 |
| TTS | Google Chirp3-HD | gần như miễn phí | 235 từ | ~$0 |
| TTS | ElevenLabs | ~$0.15–0.30/1k ký tự | ~1.5k | ~$0.30 |
| Nhạc | Thư viện `music_library/` (Mixkit/YouTube Audio Library) | $0 | 1 | $0 |
| Nhạc | Music gen API | ~$0.10–0.50 | 1 | ~$0.10–0.50 |
| Nhạc | Suno/ElevenLabs Music | ~$0.10–1.00 | 1 | ~$0.10–1.00 |
| Composition | Remotion / HyperFrames (local) | $0 | — | $0 |
| **Tổng (đường cao cấp)** | | | | **~$27–28** |
| **Tổng (đường tối ưu)** | ảnh gen + chuyển động camera + TTS miễn phí | | | **~$0.5–1.5** |

> **Đường tối ưu** biến chính video này thành **animated_still** (ảnh tĩnh + pan/zoom rất
> chậm + lá vàng/khói hương là lớp particle trong Remotion). Chất lượng thấp hơn video gen
> nhưng chi phí gần bằng 0 và hoàn toàn không phụ thuộc API video.

---

## 4. PROMPT THEO TỪNG CÔNG CỤ (khi không chạy qua OpenMontage)

**4.1 Veo 3.1 / Sora 2** — dán trực tiếp đoạn 5-aspect của từng shot (mục 3.3).
Thêm dòng chống phụ đề: `No subtitles, no captions, no on-screen text.`
Với Veo: thêm `native audio: [ambient + SFX]`, `no dialogue`.

**4.2 Kling 2.6** — rút gọn mỗi shot còn 3–4 câu, dùng `++...++` để nhấn:
`++nhà sư nam đầu cạo, kính gọng mảnh, áo nâu vàng nghệ++ bước chậm qua sân chùa phủ lá vàng,
++dolly-in rất chậm++, golden hour, 35mm film grain.`

**4.3 Seedance 2.0** — dùng cấu trúc 8 thành phần, gộp 3 shot liền kề vào 1 lần gen
multi-shot (khoảng 10–12s), nhớ **lặp nguyên văn identity anchor** ở mọi shot.

**4.4 LTX-2 / Runway Gen-4** — mỗi prompt ≤ 60–80 từ, chỉ tả **chuyển động + bối cảnh**,
không tả ngoại hình dài dòng.

**4.5 Midjourney / FLUX (ảnh)** — dùng khối IMG ở mục 3.4, thêm `--ar 9:16 --style raw`
(Midjourney) hoặc `aspect_ratio: 9:16, guidance: 3.5` (FLUX).

**4.6 CapCut / Premiere (thủ công)** — timeline:
`V1` clip → `V2` overlay chữ → `A1` giọng đọc → `A2` nhạc (−24 dB) → `A3` SFX;
burn caption từ file SRT; export H.264 High@4.2, 1080×1920, 10 Mbps VBR, 30 fps.

---

## 5. CẤU HÌNH RENDER + CHECKLIST

### 5.1 Thông số đầu ra

```yaml
resolution: 1080x1920          # 9:16
fps: 30
codec: H.264 High Profile 4.2
bitrate: 10 Mbps VBR (sàn 8 Mbps)
audio: AAC 192 kbps, 48 kHz, stereo
loudness: -14 LUFS, true peak -1 dBTP
duration: 96 s
container: .mp4
platform_safe_zone: 900x1400 px centered
```

### 5.2 Checklist trước khi render

- [ ] Hook xuất hiện ≤ 0.5s: chữ + giọng đọc cùng lúc, không có intro im lặng/logo.
- [ ] Nhạc vào ngay giây 0, không có khoảng lặng đầu video.
- [ ] Mọi shot dùng **cùng** một identity anchor (lặp nguyên văn, không dùng đại từ).
- [ ] Không có chữ nào do model video sinh ra — 100% chữ ở lớp overlay.
- [ ] Caption có mặt và đúng chính tả tiếng Việt (85% người xem tắt tiếng).
- [ ] Chữ nằm trong safe zone; không có chữ quan trọng ở 300 px dưới cùng.
- [ ] Có 1.5s im lặng sau câu bài học (deliberate silence).
- [ ] Câu chốt nối được về câu hook (loop).
- [ ] Đã qua **sample 12–15s** và được duyệt trước khi gen full.
- [ ] Đã log `decision_log`: `render_runtime_selection`, `composition_mode`,
      `provider_selection`, `voice_selection`, `music_selection`.

### 5.3 Ba concept khác nhau để chọn (đừng sao chép bản gốc)

| | Concept A — *Ngọn đèn dầu* | Concept B — *Chiếc gậy tre* | Concept C — *Hạt cát trong tay* |
|---|---|---|---|
| Giữ từ bản gốc | Nhịp chậm, chùa mùa thu, chữ vàng | Cấu trúc 2 nhân vật đối lập | Hook câu hỏi + twist nghịch lý |
| Twist | Giữ lại thì mất, cho đi thì sáng | Đi một mình mới tới đích | Nắm chặt thì trôi hết |
| Biểu tượng | Ngọn đèn chưa cháy | Cây gậy chống | Nắm cát trong lòng bàn tay |
| Khác biệt thị giác | Ánh lửa đêm, tương phản sáng-tối mạnh | Leo núi, tuyết, góc rộng | Cận cảnh bàn tay + cát, macro |
| Đường sản xuất | Video gen (đêm, lửa) | Video gen (chuyển động nhiều) | Ảnh gen + macro (rẻ nhất) |

---

## 6. Giới hạn phân tích & cách đo lại bằng tool (nếu cần)

Trong phiên phân tích này:

- **Lấy được:** tiêu đề, kênh, ngày đăng, thời lượng (96s), view, mô tả đầy đủ, thumbnail
  1280×720 (đã đọc trực tiếp bằng vision).
- **Không lấy được:** caption/transcript (YouTube `timedtext` + innertube `get_transcript`
  trả rỗng/400), và storyboard frames (`i.ytimg.com/sb/...` trả 403).
- **Hệ quả:** phần `motion_type`, số shot chính xác và lời đọc từng câu là **suy luận từ
  thumbnail + mô tả + mô-típ thể loại**, không phải số đo tự động.

Muốn có số liệu chính xác, chạy trong repo này (cần Python + ffmpeg + Node đã có):

```bash
# 1) Tải video về
python -c "from tools.analysis.video_downloader import VideoDownloader; print(VideoDownloader().execute({'url':'https://www.youtube.com/shorts/O-xrpM9lOqs','output_path':'projects/nha-su-va-ngon-den/assets/source/ref.mp4'}))"

# 2) Phân tích chuẩn (scene detect + motion_type + keyframe + transcript)
python -c "from tools.analysis.video_analyzer import VideoAnalyzer; import json; print(json.dumps(VideoAnalyzer().execute({'source':'projects/nha-su-va-ngon-den/assets/source/ref.mp4','analysis_depth':'standard','max_keyframes':20}).data, ensure_ascii=False, indent=2))"
```

Sau đó đối chiếu với bảng ở mục 1.5–1.6 và cập nhật lại scene plan cho khớp nhịp thật
(ví dụ nếu video gốc cắt 24 lần thì scene plan 8 shot cần tăng lên 14–20 shot).

---

*Tài liệu này được tạo trong `OpenMontageVideo/docs/`. Nền tảng phân tích: `skills/meta/video-reference-analyst.md`,
`skills/creative/video-gen-prompting.md`, `skills/creative/prompting/seedance-prompting.md`,
`skills/creative/short-form.md`, `skills/creative/storytelling.md`.*
