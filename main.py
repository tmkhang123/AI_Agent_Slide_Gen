import sys
import os
import json
from ai_engine import AIEngine
from slide_generator import SlideGenerator

def main():
    print("====================================")
    print("      AI SLIDES MAKER AGENT         ")
    print("====================================")
    
    topic = input("Nhập chủ đề bạn muốn tạo slide: ")
    if not topic.strip():
        print("Lỗi: Chủ đề không được để trống.")
        return

    # --- BƯỚC 1: SINH NỘI DUNG VÀ LƯU FILE JSON ---
    print(f"\n[*] BƯỚC 1: Đang dùng AI (Ollama) để sinh cấu trúc nội dung...")
    ai = AIEngine()
    content = ai.generate_content(topic)

    # Đặt tên file JSON dựa trên chủ đề
    safe_name = "".join([c for c in topic if c.isalnum() or c in (' ', '_')]).rstrip().replace(' ', '_')
    json_filename = f"{safe_name}_content.json"
    
    try:
        with open(json_filename, "w", encoding="utf-8") as f:
            json.dump(content, f, ensure_ascii=False, indent=4)
        print(f"[OK] Đã lưu nội dung và bố cục vào file: {json_filename}")
    except Exception as e:
        print(f"[!] Lỗi khi lưu file JSON: {e}")

    # --- BƯỚC 2: ĐỌC TỪ JSON VÀ TẠO FILE SLIDES ---
    print(f"\n[*] BƯỚC 2: Agent đang lấy dữ liệu từ file JSON để tạo PowerPoint...")
    
    # Đọc lại file (để đảm bảo quy trình tách biệt đúng ý bạn)
    try:
        with open(json_filename, "r", encoding="utf-8") as f:
            slides_data = json.load(f)
    except Exception as e:
        print(f"[!] Lỗi khi đọc file JSON: {e}")
        return

    gen = SlideGenerator()
    
    # 1. Slide tiêu đề
    gen.add_title_slide(slides_data['title'], slides_data['subtitle'])
    
    # 2. Các slide nội dung
    for idx, slide_data in enumerate(slides_data['slides'], 1):
        print(f"    > Đang chuyển đổi nội dung slide {idx}: {slide_data['title']}")
        gen.add_content_slide(slide_data['title'], slide_data['points'])

    # 3. Lưu file PPTX
    pptx_filename = f"{safe_name}.pptx"
    
    try:
        gen.save(pptx_filename)
        print(f"\n[OK] TẤT CẢ HOÀN TẤT!")
        print(f"    - File nội dung (JSON): {os.path.abspath(json_filename)}")
        print(f"    - File trình chiếu (PPTX): {os.path.abspath(pptx_filename)}")
    except Exception as e:
        print(f"\n[!] Lỗi khi lưu file PPTX: {e}")

if __name__ == "__main__":
    main()
