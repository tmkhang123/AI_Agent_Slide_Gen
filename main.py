"""
main.py — ĐIỂM VÀO CLI (đã chuyển sang kiến trúc 3-agent)
========================================================
Giữ nguyên cách dùng cũ để tương thích với watcher.py và file .bat:

    python main.py                      → nhập chủ đề, chạy full pipeline
    python main.py "Chủ đề..."          → chạy full pipeline với chủ đề
    python main.py XYZ_content.json     → chỉ dựng lại slide từ JSON (Designer)

Toàn bộ logic nay nằm trong 3 agent + orchestrator. main.py chỉ là lớp vỏ CLI.
"""

import sys
import os

from orchestrator import SlidesMakerOrchestrator


def _resolve_json(arg: str) -> str | None:
    """watcher.py truyền vào tên file trần; thử cả ./ và ./Product/."""
    if os.path.exists(arg):
        return arg
    alt = os.path.join("Product", os.path.basename(arg))
    return alt if os.path.exists(alt) else None


def main():
    print("====================================")
    print("      AI SLIDES MAKER AGENT         ")
    print("    (kiến trúc 3 agent độc lập)     ")
    print("====================================")

    orch = SlidesMakerOrchestrator()

    # Chế độ JSON: dựng lại slide từ file *_content.json
    if len(sys.argv) > 1 and sys.argv[1].endswith("_content.json"):
        json_path = _resolve_json(sys.argv[1])
        if not json_path:
            print(f"[!] Không tìm thấy file: {sys.argv[1]}")
            return
        print(f"[*] Dựng lại slide từ: {json_path}")
        result = orch.run_from_content_json(json_path)

    # Chế độ chủ đề: full pipeline
    else:
        topic = (sys.argv[1] if len(sys.argv) > 1
                 else input("Nhập chủ đề bạn muốn tạo slide: ").strip())
        if not topic:
            print("Lỗi: Chủ đề không được để trống.")
            return
        result = orch.run_from_topic(topic)

    print("\n[OK] TẤT CẢ HOÀN TẤT!")
    for k, v in result.items():
        print(f"   - {k:8s}: {os.path.abspath(v)}")


if __name__ == "__main__":
    main()
