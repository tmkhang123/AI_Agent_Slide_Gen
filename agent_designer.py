"""
agent_designer.py — AGENT 3 · DESIGNER  (Phụ trách: Thành viên C)
================================================================
NHIỆM VỤ (ứng với yêu cầu "Tạo bố cục trình chiếu"):
    - Nhận nội dung đầy đủ (Deck) từ ContentAgent.
    - Với mỗi slide: TỰ QUYẾT có cần tìm ảnh minh hoạ không, rồi tải ảnh
      (qua ImageFetcher, có fallback placeholder).
    - Dựng file .pptx với layout full-bleed (qua SlideGenerator).
    - Quản lý phiên bản file (_ver_1, _ver_2, ...).

INPUT : schema.Deck  (+ thư mục output, tên file gốc)
OUTPUT: đường dẫn file .pptx

Tính "agent": tự ra quyết định ảnh theo từng slide & theo cấu hình use_images;
chịu trách nhiệm toàn bộ khâu trình bày, tách biệt khỏi khâu nội dung.
"""

from __future__ import annotations
import os
import re

from schema import Deck
from image_fetcher import ImageFetcher
from slide_generator import SlideGenerator


class DesignerAgent:
    def __init__(self, use_images: bool = True):
        self.use_images = use_images
        self.fetcher = ImageFetcher()
        self.sg = SlideGenerator()

    # ── API công khai ────────────────────────────────────────────────────────
    def build(self, deck: Deck, output_dir: str = "Product",
              base_name: str = "presentation", on_progress=None) -> str:
        def emit(msg):
            print(msg)
            if on_progress:
                try:
                    on_progress(msg)
                except Exception:
                    pass

        os.makedirs(output_dir, exist_ok=True)
        emit(f"[Designer] Dựng {len(deck.slides)} slide "
             f"(ảnh: {'BẬT' if self.use_images else 'TẮT'})...")

        # 1) Slide tiêu đề -----------------------------------------------------
        title_img = None
        if self.use_images:
            tq = deck.title if deck.title.isascii() else "technology innovation concept"
            emit("[Designer] Tìm ảnh bìa...")
            title_img = self.fetcher.fetch(tq)
        self.sg.add_title_slide(deck.title, deck.subtitle, title_img)

        # 2) Các slide nội dung ------------------------------------------------
        total = len(deck.slides)
        for idx, slide in enumerate(deck.slides, 1):
            emit(f"[Designer] Slide {idx}/{total}: {slide.title}")
            img = self._decide_image(slide)
            self.sg.add_content_slide(
                title=slide.title,
                bullet_points=slide.points,
                image_stream=img,
            )

        # 3) Lưu file (có versioning) -----------------------------------------
        suffix = self._next_version_suffix(output_dir, base_name)
        pptx_path = os.path.join(output_dir, f"{base_name}{suffix}.pptx")
        self.sg.save(pptx_path)
        emit(f"[Designer] ✔ Đã lưu: {pptx_path}")
        return pptx_path

    # ── Quyết định ảnh cho 1 slide ───────────────────────────────────────────
    def _decide_image(self, slide):
        if not self.use_images:
            return None
        query = (slide.image_query or "").strip()
        if not query:
            return None
        return self.fetcher.fetch(query)

    # ── Đặt tên phiên bản ────────────────────────────────────────────────────
    @staticmethod
    def _next_version_suffix(product_dir: str, base_name: str) -> str:
        if not os.path.exists(os.path.join(product_dir, f"{base_name}.pptx")):
            return ""
        version = 1
        pattern = re.compile(rf"^{re.escape(base_name)}_ver_(\d+)\.pptx$")
        for fname in os.listdir(product_dir):
            m = pattern.match(fname)
            if m:
                version = max(version, int(m.group(1)) + 1)
        return f"_ver_{version}"


# ── Cho phép chạy/test ĐỘC LẬP agent này ─────────────────────────────────────
if __name__ == "__main__":
    import sys
    import json

    # Test độc lập: dựng PPTX từ 1 file *_content.json có sẵn,
    # KHÔNG cần Planner hay Content chạy trước.
    if len(sys.argv) > 1 and os.path.exists(sys.argv[1]):
        with open(sys.argv[1], "r", encoding="utf-8") as f:
            deck = Deck.from_dict(json.load(f))
        base = os.path.basename(sys.argv[1]).replace("_content.json", "")
    else:
        # Deck mẫu nếu không truyền file
        deck = Deck.from_dict({
            "title": "Demo DesignerAgent",
            "subtitle": "Dựng slide từ dữ liệu mẫu",
            "slides": [
                {"title": "Slide thử nghiệm",
                 "points": ["Đây là một ý nội dung mẫu để kiểm tra layout.",
                            "Designer chịu trách nhiệm trình bày và tìm ảnh."],
                 "image_query": "abstract technology background"},
            ],
        })
        base = "demo_designer"

    path = DesignerAgent(use_images=True).build(deck, "Product", base)
    print("OUTPUT:", path)
