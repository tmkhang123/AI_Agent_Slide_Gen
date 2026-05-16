import sys
import time
import os
import subprocess
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler

class JsonChangeHandler(FileSystemEventHandler):
    def __init__(self, python_exe, script_path):
        self.python_exe = python_exe
        self.script_path = script_path
        self.last_triggered = 0

    def on_modified(self, event):
        if event.is_directory:
            return
        if event.src_path.endswith("_content.json"):
            # Throttling to prevent multiple executions for one save
            current_time = time.time()
            if current_time - self.last_triggered < 2:
                return
            
            self.last_triggered = current_time
            filename = os.path.basename(event.src_path)
            print(f"\n[DETECTED] Phát hiện thay đổi trong: {filename}")
            print(f"[*] Đang tự động cập nhật Slide...")
            
            try:
                # Run main.py with the modified JSON
                subprocess.run([self.python_exe, self.script_path, filename], check=True)
                print(f"[OK] Đã cập nhật xong cho {filename}")
            except Exception as e:
                print(f"[!] Lỗi khi tự động cập nhật: {e}")

def start_watcher():
    python_exe = sys.executable
    script_path = os.path.join(os.path.dirname(__file__), "main.py")
    
    print("============================================================")
    print("      AI SLIDES MAKER - WATCH MODE (AGENTIC)                ")
    print("============================================================")
    print(f"[*] Đang theo dõi các file JSON trong thư mục hiện tại...")
    print("[*] Chỉ cần bạn nhấn Save (Ctrl+S) file JSON, Slide sẽ tự update.")
    print("[*] Nhấn Ctrl+C để dừng theo dõi.")
    
    event_handler = JsonChangeHandler(python_exe, script_path)
    observer = Observer()
    observer.schedule(event_handler, path=".", recursive=False)
    observer.start()
    
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        observer.stop()
        print("\n[*] Đã dừng chế độ Watch Mode.")
    observer.join()

if __name__ == "__main__":
    start_watcher()