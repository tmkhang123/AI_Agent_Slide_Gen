"""
selftest.py — KIỂM TRA NHANH (không cần Ollama)
===============================================
Chạy:  python selftest.py

Xác minh:
  1. Bộ phân tích văn bản (parse_titles / parse_points) hoạt động đúng.
  2. Toàn bộ pipeline 3 agent dựng được file PPTX ở CHẾ ĐỘ DỰ PHÒNG
     (giả lập Ollama tắt) — bảo đảm phần "khung" luôn chạy được.

Nếu selftest PASS mà chạy thật vẫn ra dự phòng => vấn đề nằm ở Ollama
(chưa chạy 'ollama serve' hoặc chưa 'ollama pull <model>'),
hãy bấm nút "Kiểm tra Ollama" trong GUI.
"""

import llm
from agent_planner import PlannerAgent
from agent_content import ContentAgent
from agent_designer import DesignerAgent
import os
from pptx import Presentation


def test_parsers() -> bool:
    ok = True
    t = llm.parse_titles("Đây là danh sách:\n1. Giới thiệu :: intro concept\n"
                         "- Phân tích | analysis data\nSlide 3: Kết luận")
    ok &= len(t) == 3
    p = llm.parse_points("Nội dung:\n- Một ý dài đủ để vượt qua kiểm tra số từ "
                         "tối thiểu của hệ thống parser.\n"
                         "- Ý thứ hai cũng đủ dài và mang thông tin cụ thể rõ ràng.")
    ok &= len(p) == 2
    print(f"[1] Parsers: {'PASS' if ok else 'FAIL'} "
          f"(titles={len(t)}, points={len(p)})")
    return ok


def test_pipeline_fallback() -> bool:
    # Giả lập Ollama tắt: mọi lời gọi generate đều ném lỗi
    def down(*a, **k):
        raise ConnectionError("giả lập Ollama tắt")
    llm.generate = down

    outline = PlannerAgent().plan("Chủ đề kiểm thử")
    deck = ContentAgent().write(outline)
    pptx = DesignerAgent(use_images=False).build(deck, "Product", "selftest")


    n = len(Presentation(pptx).slides._sldIdLst)
    ok = (len(deck.slides) >= 6
          and all(len(s.points) >= 3 for s in deck.slides)
          and n == len(deck.slides) + 1
          and os.path.exists(pptx))
    print(f"[2] Pipeline (fallback): {'PASS' if ok else 'FAIL'} "
          f"({len(deck.slides)} slide nội dung, PPTX {n} slide)")
    return ok


if __name__ == "__main__":
    print("=== SELF-TEST (không cần Ollama) ===")
    a = test_parsers()
    b = test_pipeline_fallback()
    print("\nKẾT QUẢ:", "TẤT CẢ PASS ✅" if (a and b) else "CÓ LỖI ❌")
