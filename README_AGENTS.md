# AI Slides Maker — Kiến trúc 3 Agent (bản xây lại, chống lỗi)

Dự án tách thành **3 agent độc lập** cho **3 thành viên**, đáp ứng yêu cầu
*"nhóm 3 người, mỗi người 1 agent"*. Bản này được **viết lại phần lõi** để khắc
phục lỗi "chỉ ra 1 slide / toàn dùng nội dung dự phòng".

---

## 1. Phân công 3 agent

| Agent | File chính | Người phụ trách | Ứng với yêu cầu |
|-------|-----------|-----------------|-----------------|
| **Agent 1 · Planner**  | `agent_planner.py`  | Thành viên **A** | *Nhận chủ đề* |
| **Agent 2 · Content**  | `agent_content.py`  | Thành viên **B** | *Sinh nội dung slide* |
| **Agent 3 · Designer** | `agent_designer.py` | Thành viên **C** | *Tạo bố cục trình chiếu* |

Dùng chung (cả nhóm): `llm.py` (lõi gọi model + parser), `schema.py`,
`orchestrator.py`, `main.py`, `gui_app.py`, `watcher.py`, `image_fetcher.py`,
`slide_generator.py`. Tiện ích: `selftest.py`.

Luồng: `topic → Planner (Outline) → Content (Deck) → Designer (.pptx)`.
Ba agent chỉ trao đổi qua hợp đồng dữ liệu trong `schema.py`.

---

## 2. Vì sao bản cũ lỗi & bản này sửa thế nào

**Nguyên nhân lỗi cũ:** ép `llama3.1:8b` xuất `format=json` chứa NHIỀU slide
trong MỘT lần gọi. Model nhỏ thường "đóng" JSON sớm → chỉ 1 slide; hoặc đặt
sai tên key → parse rỗng → rơi về dự phòng.

**Cách sửa trong bản này (tất cả nằm ở `llm.py` + 2 agent):**

1. **Bỏ JSON ép buộc — sinh bằng văn bản thường.** `llm.generate()` gọi Ollama
   ở chế độ text, không `format=json`.
2. **Content sinh theo TỪNG SLIDE.** Mỗi lần gọi chỉ viết 3-4 ý cho 1 tiêu đề
   — việc nhẹ này model 8B làm rất ổn định, thay vì 1 JSON khổng lồ cho cả bài.
3. **Parser khoan dung** (`parse_titles`, `parse_points`): chấp nhận gạch đầu
   dòng, đánh số, `Slide N:`, dấu `::`/`|`, bỏ câu mở đầu thừa, markdown fence…
   → luôn moi được dữ liệu nếu model có trả lời, bất kể định dạng.
4. **Planner bảo đảm đủ slide.** Dù model trả thiếu/sai/rỗng, Planner vẫn chèn
   các mục chuẩn và luôn có *Giới thiệu* ở đầu, *Kết luận* ở cuối → không bao
   giờ ra deck 1 slide.

> Đã test: với model trả về (kể cả định dạng lộn xộn) → ra **đủ slide, nội dung
> thật**; khi Ollama tắt → vẫn ra đủ slide bằng nội dung dự phòng.

---

## 3. Cách chạy

```bash
# Cả pipeline
python main.py "Lợi ích của AI trong giáo dục"
python orchestrator.py "Lợi ích của AI trong giáo dục"

# Dựng lại từ JSON đã chỉnh tay (chỉ Agent 3)
python main.py Product/<ten>_content.json

# Giao diện web
python -m streamlit run gui_app.py
```

Test ĐỘC LẬP từng agent (mỗi thành viên tự kiểm tra phần của mình):
```bash
python agent_planner.py  "Chủ đề bất kỳ"
python agent_content.py
python agent_designer.py Product/<ten>_content.json
```

Kiểm tra nhanh phần khung (KHÔNG cần Ollama):
```bash
python selftest.py        # PASS nghĩa là code chạy tốt, lỗi (nếu có) là do Ollama
```

---

## 4. Khắc phục sự cố (QUAN TRỌNG)

Nếu vẫn thấy "1 slide" hoặc "toàn dự phòng":

1. **Bạn có đang chạy đúng bản mới không?** Log/giao diện bản mới in
   `[Planner] / [Content] / [Designer]`. Nếu thấy `[Ollama]` hay "Bước 1/2/3"
   tức là file cũ chưa được ghi đè — chép ĐỦ tất cả file (đặc biệt `llm.py`,
   `agent_planner.py`, `agent_content.py`, `gui_app.py`) vào đúng thư mục dự án.
2. **Ollama đã chạy & có model chưa?** Trong GUI bấm **"🔌 Kiểm tra Ollama"**.
   Hoặc terminal: `ollama serve` rồi `ollama pull llama3.1:8b` (`ollama list`
   để xem model đang có).
3. **Chạy `python selftest.py`.** Nếu PASS mà chạy thật vẫn dự phòng ⇒ chắc
   chắn vấn đề ở Ollama (chưa chạy / sai tên model / máy hết RAM khi nạp model).
4. **Model quá yếu:** `llama3.1:8b` đôi khi viết sơ sài. Nếu máy đủ khỏe, đổi ô
   "Ollama Model" sang model lớn hơn (đã `ollama pull`) để nội dung tốt hơn.

---

## 5. "Tính agent" để bảo vệ khi demo
- **Planner**: tự lập kế hoạch, tự kiểm tra & bảo đảm bố cục (mở đầu/kết luận,
  đủ slide, image_query tiếng Anh).
- **Content**: sinh theo từng slide, **tự đánh giá** (đủ ý? đủ dài?) và **sinh
  lại có chủ đích**; hỏng thì dùng dự phòng.
- **Designer**: tự quyết ảnh từng slide, chọn overlay theo độ sáng ảnh, quản lý
  phiên bản file.
