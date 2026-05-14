import requests
import json

class AIEngine:
    """
    Sử dụng Ollama Local API để sinh nội dung bằng model Llama 3.1:8b.
    Đảm bảo Ollama đang chạy trên máy của bạn.
    """
    def __init__(self, model_name="llama3.1:8b"):
        self.model_name = model_name
        self.api_url = "http://localhost:11434/api/generate"

    def generate_content(self, topic):
        print(f"    [Ollama] Đang yêu cầu {self.model_name} phân tích sâu sắc về: {topic}...")
        
        prompt = (
            f"Bạn là một chuyên gia soạn thảo bài thuyết trình chuyên nghiệp. "
            f"Hãy viết nội dung chi tiết cho bài thuyết trình về chủ đề '{topic}' bằng tiếng Việt. "
            "Yêu cầu: "
            "1. Mỗi slide phải có tiêu đề rõ ràng. "
            "2. Mỗi slide phải có ít nhất 3-4 ý chính (points). "
            "3. QUAN TRỌNG: Với mỗi ý chính, hãy thêm một đoạn giải thích ngắn gọn, súc tích ngay bên cạnh hoặc dưới để người xem hiểu rõ vấn đề (ví dụ: 'Ý chính: Giải thích chi tiết hơn một chút'). "
            "4. Nội dung phải mang tính chuyên môn, sâu sắc nhưng dễ hiểu. "
            "Hãy trả về DUY NHẤT một đối tượng JSON (không kèm mã markdown) với cấu trúc: "
            '{"title": "Tiêu đề chính", "subtitle": "Mô tả tổng quan sâu sắc", '
            '"slides": [{"title": "Tiêu đề Slide", "points": ["Ý chính 1: Nội dung giải thích chi tiết...", "Ý chính 2: Nội dung giải thích chi tiết..."]}]}. '
            "Tạo ít nhất 5 slide nội dung."
        )

        try:
            response = requests.post(
                self.api_url,
                json={
                    "model": self.model_name,
                    "prompt": prompt,
                    "format": "json",
                    "stream": False
                },
                timeout=120
            )
            
            if response.status_code == 200:
                data = response.json()
                content = json.loads(data['response'])
                print(f"    [OK] AI đã sinh nội dung thực tế từ model local.")
                return content
            else:
                raise Exception(f"Ollama error: {response.status_code}")

        except Exception as e:
            print(f"    [!] Lỗi kết nối Ollama: {e}. Vui lòng đảm bảo Ollama đang chạy.")
            print(f"    [Dự phòng] Đang tạo cấu trúc thông minh cho: {topic}")
            return {
                "title": f"Chuyên đề: {topic}",
                "subtitle": "Phân tích và định hướng bởi AI Agent",
                "slides": [
                    {"title": f"Giới thiệu về {topic}", "points": ["Định nghĩa và bối cảnh", "Tầm quan trọng hiện nay", "Mục tiêu trình bày"]},
                    {"title": "Phân tích chi tiết", "points": ["Các đặc điểm chính", "Ưu điểm vượt trội", "Cơ sở lý thuyết"]},
                    {"title": "Ứng dụng thực tế", "points": ["Case study điển hình", "Quy trình triển khai", "Hiệu quả mang lại"]},
                    {"title": "Thách thức & Giải mã", "points": ["Các khó khăn gặp phải", "Giải pháp tối ưu", "Kinh nghiệm thực tế"]},
                    {"title": "Kết luận & Q&A", "points": ["Tóm tắt ý chính", "Định hướng tương lai", "Lời chào kết thúc"]}
                ]
            }
