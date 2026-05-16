import sys
import os
import json
import re
from ai_engine import AIEngine
from slide_generator import SlideGenerator

def get_next_version(base_filename):
    """
    Checks for existing files with the pattern base_filename_ver_X.pptx
    and returns the next available version suffix.
    """
    version = 1
    pattern = re.compile(rf"^{re.escape(base_filename)}_ver_(\d+)\.pptx$")
    
    # Check if the non-versioned file exists
    if os.path.exists(f"{base_filename}.pptx"):
        # Look for existing versions
        for file in os.listdir("."):
            match = pattern.match(file)
            if match:
                v = int(match.group(1))
                if v >= version:
                    version = v + 1
        return f"_ver_{version}"
    return ""

def main():
    print("====================================")
    print("      AI SLIDES MAKER AGENT         ")
    print("====================================")
    
    # Đảm bảo thư mục Product tồn tại
    product_dir = "Product"
    if not os.path.exists(product_dir):
        os.makedirs(product_dir)
        
    # Check if a JSON file was passed as an argument
    slides_data = None
    json_path = None
    safe_name = None

    if len(sys.argv) > 1:
        json_path = sys.argv[1]
        if os.path.exists(json_path):
            print(f"[*] Đang tải dữ liệu từ file JSON: {json_path}")
            try:
                with open(json_path, "r", encoding="utf-8") as f:
                    slides_data = json.load(f)
                # Extract safe_name from filename
                safe_name = os.path.basename(json_path).replace("_content.json", "")
            except Exception as e:
                print(f"[!] Lỗi khi đọc file JSON: {e}")
                return
        else:
            print(f"[!] Lỗi: Không tìm thấy file {json_path}")
            return

    if not slides_data:
        topic = input("Nhập chủ đề bạn muốn tạo slide: ")
        if not topic.strip():
            print("Lỗi: Chủ đề không được để trống.")
            return

        # --- BƯỚC 1: SINH NỘI DUNG VÀ LƯU FILE JSON ---
        print(f"\n[*] BƯỚC 1: Đang dùng AI (Ollama) để sinh cấu trúc nội dung...")
        ai = AIEngine()
        content = ai.generate_content(topic)

        # Đặt tên file JSON dựa trên chủ đề và đưa vào Product
        safe_name = "".join([c for c in topic if c.isalnum() or c in (' ', '_')]).rstrip().replace(' ', '_')
        json_path = os.path.join(product_dir, f"{safe_name}_content.json")
        
        try:
            with open(json_path, "w", encoding="utf-8") as f:
                json.dump(content, f, ensure_ascii=False, indent=4)
            print(f"[OK] Đã lưu nội dung và bố cục vào file: {json_path}")
            slides_data = content
        except Exception as e:
            print(f"[!] Lỗi khi lưu file JSON: {e}")
            return

    # --- BƯỚC 2: TẠO FILE SLIDES ---
    print(f"\n[*] BƯỚC 2: Agent đang lấy dữ liệu từ file JSON để tạo PowerPoint...")
    
    gen = SlideGenerator()
    
    # 1. Slide tiêu đề
    gen.add_title_slide(slides_data['title'], slides_data['subtitle'])
    
    # 2. Các slide nội dung
    for idx, slide_data in enumerate(slides_data['slides'], 1):
        print(f"    > Đang chuyển đổi nội dung slide {idx}: {slide_data['title']}")
        gen.add_content_slide(slide_data['title'], slide_data['points'])

    # 3. Tính toán phiên bản và lưu file PPTX vào Product
    version = 1
    pattern = re.compile(rf"^{re.escape(safe_name)}_ver_(\d+)\.pptx$")
    ver_suffix = ""
    
    if os.path.exists(os.path.join(product_dir, f"{safe_name}.pptx")):
        for file in os.listdir(product_dir):
            match = pattern.match(file)
            if match:
                v = int(match.group(1))
                if v >= version:
                    version = v + 1
        ver_suffix = f"_ver_{version}"

    pptx_path = os.path.join(product_dir, f"{safe_name}{ver_suffix}.pptx")
    
    try:
        gen.save(pptx_path)
        print(f"\n[OK] TẤT CẢ HOÀN TẤT!")
        print(f"    - File nội dung (JSON): {os.path.abspath(json_path)}")
        print(f"    - File trình chiếu (PPTX): {os.path.abspath(pptx_path)}")
    except Exception as e:
        print(f"\n[!] Lỗi khi lưu file PPTX: {e}")

if __name__ == "__main__":
    main()
