import sys
import os
import json
import re
from ai_engine import AIEngine
from slide_generator import SlideGenerator
from image_fetcher import ImageFetcher


def get_next_version_suffix(product_dir: str, base_name: str) -> str:
    if not os.path.exists(os.path.join(product_dir, f"{base_name}.pptx")):
        return ""
    version = 1
    pattern = re.compile(rf"^{re.escape(base_name)}_ver_(\d+)\.pptx$")
    for fname in os.listdir(product_dir):
        m = pattern.match(fname)
        if m:
            v = int(m.group(1))
            version = max(version, v + 1)
    return f"_ver_{version}"


def build_presentation(slides_data: dict, product_dir: str, safe_name: str) -> str:
    fetcher = ImageFetcher()
    sg      = SlideGenerator()

    # ── Slide tiêu đề: tìm ảnh từ title ──
    print(f"\n    > Slide 0 (Title): tìm ảnh bìa...")
    title_query  = slides_data.get("title", "presentation cover")
    # Dùng query ngắn gọn tiếng Anh cho title
    title_img    = fetcher.fetch(title_query if title_query.isascii()
                                 else "technology innovation concept")
    sg.add_title_slide(slides_data["title"], slides_data["subtitle"], title_img)

    # ── Các slide nội dung ──
    total = len(slides_data["slides"])
    for idx, slide_data in enumerate(slides_data["slides"], 1):
        print(f"\n    > Slide {idx}/{total}: {slide_data['title']}")
        image_query  = slide_data.get("image_query", "")
        image_stream = fetcher.fetch(image_query) if image_query else None
        sg.add_content_slide(
            title         = slide_data["title"],
            bullet_points = slide_data["points"],
            image_stream  = image_stream,
        )

    ver_suffix = get_next_version_suffix(product_dir, safe_name)
    pptx_path  = os.path.join(product_dir, f"{safe_name}{ver_suffix}.pptx")
    sg.save(pptx_path)
    return pptx_path


def main():
    print("====================================")
    print("      AI SLIDES MAKER AGENT         ")
    print("  (với hỗ trợ hình ảnh tự động)     ")
    print("====================================")

    product_dir = "Product"
    os.makedirs(product_dir, exist_ok=True)

    slides_data = None
    json_path   = None
    safe_name   = None

    if len(sys.argv) > 1:
        json_path = sys.argv[1]
        if not os.path.exists(json_path):
            print(f"[!] Lỗi: Không tìm thấy file {json_path}")
            return
        print(f"[*] Đang tải dữ liệu từ file JSON: {json_path}")
        try:
            with open(json_path, "r", encoding="utf-8") as f:
                slides_data = json.load(f)
            safe_name = os.path.basename(json_path).replace("_content.json", "")
        except Exception as e:
            print(f"[!] Lỗi khi đọc file JSON: {e}")
            return

    if not slides_data:
        topic = input("Nhập chủ đề bạn muốn tạo slide: ").strip()
        if not topic:
            print("Lỗi: Chủ đề không được để trống.")
            return

        print(f"\n[*] BƯỚC 1: Đang dùng AI (Ollama) để sinh nội dung...")
        ai      = AIEngine()
        content = ai.generate_content(topic)

        safe_name = (
            "".join(c for c in topic if c.isalnum() or c in (" ", "_"))
            .rstrip().replace(" ", "_")
        )
        json_path = os.path.join(product_dir, f"{safe_name}_content.json")
        try:
            with open(json_path, "w", encoding="utf-8") as f:
                json.dump(content, f, ensure_ascii=False, indent=4)
            print(f"[OK] Đã lưu nội dung vào: {json_path}")
            slides_data = content
        except Exception as e:
            print(f"[!] Lỗi khi lưu file JSON: {e}")
            return

    print(f"\n[*] BƯỚC 2: Đang tìm ảnh và tạo PowerPoint...")
    try:
        pptx_path = build_presentation(slides_data, product_dir, safe_name)
        print(f"\n[OK] TẤT CẢ HOÀN TẤT!")
        print(f"    - File nội dung (JSON) : {os.path.abspath(json_path)}")
        print(f"    - File trình chiếu     : {os.path.abspath(pptx_path)}")
    except Exception as e:
        print(f"\n[!] Lỗi khi tạo PPTX: {e}")


if __name__ == "__main__":
    main()
