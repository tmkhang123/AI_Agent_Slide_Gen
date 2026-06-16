"""
agent_reviewer.py — AGENT 4 · REVIEWER / CRITIC  (Phụ trách: Thành viên D / Reviewer)
=============================================================================
NHIỆM VỤ:
    - Nhận danh sách slide đầy đủ (Deck) từ ContentAgent.
    - Với mỗi slide:
      - Gọi LLM để duyệt nội dung.
      - Thêm tag bôi đậm `**` cho các từ khóa/cụm từ quan trọng để cải thiện visual hierarchy.
      - Tối ưu hóa độ dài: rút gọn những câu quá dài (hơn 15 từ) để slide trực quan hơn.
    - Có chế độ dự phòng cục bộ (local fallback) nếu Ollama bị lỗi để đảm bảo không lỗi ứng dụng.
"""

from __future__ import annotations
import re
import llm
from schema import Deck, Slide


def get_nlp_warning(text: str) -> str:
    """Trả về cảnh báo tránh nhầm lẫn NLP chỉ khi văn bản chứa từ 'nlp'."""
    if not text or "nlp" not in text.lower():
        return ""
    return (
        "\nLƯU Ý QUAN TRỌNG: Hãy hiểu 'NLP' ở đây là "
        "'Natural Language Processing' (Xử lý ngôn ngữ tự nhiên trong Khoa học máy tính và Trí tuệ nhân tạo), "
        "hoàn toàn KHÔNG PHẢI 'Neuro-Linguistic Programming' (Lập trình ngôn ngữ tư duy trong tâm lý học). "
        "Tất cả các nội dung, thuật ngữ và ví dụ phải xoay quanh xử lý ngôn ngữ tự nhiên trong AI.\n"
    )


class ReviewerAgent:
    def __init__(self, model_name: str = "llama3.1:8b", api_url: str = llm.GEN_API):
        self.model_name = model_name
        self.api_url = api_url

    def review(self, deck: Deck, on_progress=None) -> Deck:
        def emit(msg):
            print(msg)
            if on_progress:
                try:
                    on_progress(msg)
                except Exception:
                    pass

        total = len(deck.slides)
        emit(f"[Reviewer] Bắt đầu duyệt và tối ưu hóa {total} slide...")

        reviewed_slides: list[Slide] = []
        for i, slide in enumerate(deck.slides, 1):
            emit(f"[Reviewer] Slide {i}/{total}: {slide.title}")
            
            # Nếu là slide Mục lục / Chương trình nghị sự, bỏ qua tối ưu hóa bằng LLM
            clean_title = llm.normalize_vietnamese(slide.title).strip().lower()
            clean_title = re.sub(r'\*\*|__|\*|_|<b>|</b>', '', clean_title).strip()
            is_agenda = (
                "nghị sự" in clean_title or 
                "mục lục" in clean_title or 
                "agenda" in clean_title
            )
            if is_agenda:
                emit(f"[Reviewer]   ✔ Bỏ qua tối ưu hóa cho slide Mục lục/Chương trình nghị sự.")
                points = slide.points
            else:
                # Gọi LLM tối ưu slide
                points = self._optimize_slide_points(slide.title, slide.points)
                
                # Fallback nếu kết quả rỗng, bị cắt cụt hoặc thiếu ý so với slide gốc
                if not points or len(points) < len(slide.points):
                    emit(f"[Reviewer]   ⚠ Sử dụng cơ chế bôi đậm tự động cho slide {i} do thiếu ý hoặc lỗi LLM.")
                    points = self._local_review_fallback(slide.points)
                else:
                    emit(f"[Reviewer]   ✔ Slide {i} đã được tối ưu hóa.")
                
            reviewed_slides.append(Slide(
                title=slide.title,
                points=points,
                image_query=slide.image_query
            ))

        emit(f"[Reviewer] ✔ Đã hoàn tất kiểm duyệt tất cả các slide.")
        return Deck(title=deck.title, subtitle=deck.subtitle, slides=reviewed_slides)

    def _optimize_slide_points(self, title: str, points: list[str]) -> list[str]:
        # Tạo prompt cho slide
        points_str = "\n".join([f"- {p}" for p in points])
        prompt = (
            "Bạn là một Biên tập viên học thuật và Chuyên gia Phản biện Slide (Critic Agent).\n"
            f"Nhiệm vụ của bạn là kiểm duyệt, phản biện và tối ưu hóa nội dung cho slide: \"{title}\".\n\n"
            f"Nội dung slide hiện tại:\n{points_str}\n\n"
            "QUY TRÌNH PHẢN BIỆN & CẢI THIỆN CHẤT LƯỢNG:\n"
            "- Kiểm tra tính thực chất & Lọc bỏ câu sáo rỗng: Hãy lọc bỏ toàn bộ các câu chung chung (như 'rất quan trọng', 'cần phân tích thêm'). "
            "Nếu phát hiện ý nào nông cạn hoặc sáo rỗng, hãy VIẾT LẠI ý đó bằng kiến thức chuyên môn thực chất (định nghĩa kỹ thuật, cơ chế vận hành chính xác, hoặc ví dụ thực tế liên quan mật thiết đến tiêu đề slide).\n"
            "- CẤM BỊA ĐẶT SỐ LIỆU & THUẬT NGỮ GIẢ: Nếu phát hiện bất kỳ số liệu fabricated (tự chế như 99.9%, các thông số không rõ nguồn gốc) hoặc thuật ngữ lạ/sai thực chất (như 'thuật toán treo đè', hoặc 'Vantablack' - vốn là một loại vật chất hấp thụ ánh sáng, không phải thuật toán), hãy loại bỏ hoặc thay thế bằng mô tả kỹ thuật chính xác và trung thực (đối với thuật toán Viterbi, các thuật toán liên quan thực tế là Fano, BCJR, HMM, Dijkstra).\n"
            "- Bôi đậm từ khóa: Thêm thẻ `**từ_khóa**` hoặc `**cụm_từ**` cho các khái niệm cốt lõi hoặc thuật ngữ chuyên ngành (chọn lọc, tối đa 1-2 vị trí mỗi dòng, tránh bôi đậm cả câu).\n"
            "- Tối ưu độ dài: Rút gọn các câu quá dài, đảm bảo mỗi dòng súc tích, cô đọng nhưng vẫn giàu giá trị thông tin.\n"
            "- CẤM RÚT GỌN THÀNH TIÊU ĐỀ MỤC CỘC: Cấm rút gọn các câu slide thành cụm từ quá ngắn không có thông tin thực chất (ví dụ: dưới 8 từ hoặc dạng tiêu đề mục như 'Phân tích và phản biện', 'Cơ chế hoạt động'). Mỗi gạch đầu dòng tối ưu bắt buộc phải là một câu hoàn chỉnh đầy đủ thông tin từ 12-20 từ.\n\n"
            "YÊU CẦU ĐỊNH DẠNG ĐẦU RA (CỰC KỲ QUAN TRỌNG):\n"
            "1. Phân tích hoặc suy nghĩ của bạn có thể ghi ở phần đầu (giới hạn cực kỳ ngắn gọn, dưới 50 từ).\n"
            "2. Khi xuất danh sách slide thực sự, bạn BẮT BUỘC phải in ra dòng phân tách: `---OUTPUT---` (viết hoa, nằm trên dòng riêng).\n"
            "3. Ngay phía sau dòng `---OUTPUT---`, in ra đúng các ý slide:\n"
            "  - Mỗi ý nằm trên MỘT dòng bắt đầu bằng '- '.\n"
            "  - Phải trả về ĐÚNG số lượng dòng bằng số lượng dòng ban đầu.\n"
            "  - Tuyệt đối KHÔNG viết lời dẫn, KHÔNG giải thích các bước thực hiện, KHÔNG lặp lại các ý cũ hay tiêu đề phân tích dưới dòng `---OUTPUT---`."
            f"{get_nlp_warning(title)}"
        )
        try:
            text = llm.generate(prompt, self.model_name, self.api_url,
                                num_predict=1000, temperature=0.5)
        except Exception as e:
            print(f"[Reviewer] Lỗi gọi Ollama: {e}")
            return []
        
        parsed = llm.parse_points(text, min_words=3)
        if len(parsed) == 0:
            return []
        return parsed

    def _local_review_fallback(self, points: list[str]) -> list[str]:
        """Tự động bôi đậm 2-3 từ đầu của mỗi ý nếu LLM bị lỗi."""
        reviewed = []
        for pt in points:
            if "**" in pt or "<b>" in pt:
                reviewed.append(pt)
                continue
            words = pt.split()
            if len(words) > 3:
                num_bold = min(3, len(words) - 1)
                bold_part = " ".join(words[:num_bold])
                rest_part = " ".join(words[num_bold:])
                reviewed.append(f"**{bold_part}** {rest_part}")
            else:
                reviewed.append(f"**{pt}**" if pt else pt)
        return reviewed


# ── Chạy/test độc lập ────────────────────────────────────────────────────────
if __name__ == "__main__":
    import json
    deck = Deck(
        title="Lợi ích của AI trong giáo dục",
        subtitle="Bài demo ReviewerAgent",
        slides=[
            Slide(
                title="Cá nhân hoá học tập",
                points=[
                    "Hệ thống học tập thông minh dựa trên AI có khả năng tự động phân tích hành vi và kết quả của từng học sinh để đưa ra lộ trình học tập cá nhân hóa phù hợp nhất.",
                    "Giáo viên có thể theo dõi tiến độ của học sinh trực quan thông qua dashboard cập nhật theo thời gian thực để hỗ trợ kịp thời."
                ],
                image_query="personalized learning"
            )
        ]
    )
    reviewer = ReviewerAgent()
    reviewed_deck = reviewer.review(deck)
    print(json.dumps(reviewed_deck.to_dict(), ensure_ascii=False, indent=2))
