import requests
import json

class AIEngine:
    """
    Sử dụng Ollama Local API để sinh nội dung.
    JSON trả về bao gồm trường 'image_query' (tiếng Anh) cho mỗi slide.
    """
    def __init__(self, model_name="llama3.1:8b"):
        self.model_name = model_name
        self.api_url = "http://localhost:11434/api/generate"

    def generate_content(self, topic):
        print(f"    [Ollama] Đang yêu cầu {self.model_name} phân tích về: {topic}...")

        prompt = (
            f"Bạn là một chuyên gia soạn thảo bài thuyết trình chuyên nghiệp. "
            f"Hãy viết nội dung cực kỳ chi tiết cho bài thuyết trình về chủ đề '{topic}' bằng tiếng Việt. "
            "Yêu cầu khắt khe: "
            "1. Mỗi slide phải có tiêu đề rõ ràng. "
            "2. Mỗi slide phải có ít nhất 3-4 mục nội dung. "
            "3. BẮT BUỘC: Mỗi mục nội dung phải là một đoạn văn đầy đủ (30-50 từ). "
            "4. Nội dung phải mang tính học thuật, giàu thông tin. "
            "5. Trường 'image_query' PHẢI là tiếng Anh thuần túy (3-6 từ), "
            "   không được chứa tiếng Việt, dùng để tìm ảnh minh họa. "
            "Trả về DUY NHẤT JSON (không markdown) với cấu trúc: "
            '{"title": "...", "subtitle": "...", '
            '"slides": [{"title": "...", "points": ["..."], "image_query": "english only keywords"}]}. '
            "Tạo ít nhất 7 slide nội dung."
        )

        try:
            response = requests.post(
                self.api_url,
                json={"model": self.model_name, "prompt": prompt,
                      "format": "json", "stream": False},
                timeout=300
            )
            if response.status_code == 200:
                data = response.json()
                content = json.loads(data["response"])
                print(f"    [OK] AI đã sinh nội dung từ model local.")
                return content
            else:
                raise Exception(f"Ollama error: {response.status_code} — "
                                "Kiểm tra: (1) Ollama đang chạy chưa? "
                                "(2) Tên model có đúng không? Chạy 'ollama list' để kiểm tra.")
        except Exception as e:
            print(f"    [!] Lỗi kết nối Ollama: {e}")
            print(f"    [Dự phòng] Đang tạo cấu trúc cho: {topic}")
            # ── Fallback: image_query LUÔN là tiếng Anh ──
            topic_en = topic.encode("ascii", "ignore").decode().strip() or "topic"
            return {
                "title": f"Chuyên đề: {topic}",
                "subtitle": "Phân tích và định hướng bởi AI Agent",
                "slides": [
                    {
                        "title": f"Giới thiệu về {topic}",
                        "points": ["Định nghĩa và bối cảnh", "Tầm quan trọng hiện nay", "Mục tiêu trình bày"],
                        "image_query": "introduction concept overview"
                    },
                    {
                        "title": "Phân tích chi tiết",
                        "points": ["Các đặc điểm chính", "Ưu điểm vượt trội", "Cơ sở lý thuyết"],
                        "image_query": "analysis research detail"
                    },
                    {
                        "title": "Ứng dụng thực tế",
                        "points": ["Case study điển hình", "Quy trình triển khai", "Hiệu quả mang lại"],
                        "image_query": "real world application practice"
                    },
                    {
                        "title": "Thách thức & Giải pháp",
                        "points": ["Các khó khăn gặp phải", "Giải pháp tối ưu", "Kinh nghiệm thực tế"],
                        "image_query": "challenges solutions problem solving"
                    },
                    {
                        "title": "Kết luận & Q&A",
                        "points": ["Tóm tắt ý chính", "Định hướng tương lai", "Lời chào kết thúc"],
                        "image_query": "conclusion future innovation"
                    }
                ]
            }
