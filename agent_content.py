"""
agent_content.py — AGENT 2 · CONTENT  (Phụ trách: Thành viên B)
==============================================================
NHIỆM VỤ ("Sinh nội dung slide"): nhận dàn ý (Outline) -> viết nội dung chi
tiết cho TỪNG slide (3-4 ý, mỗi ý 25-45 từ, tiếng Việt).

INPUT : schema.Outline        OUTPUT: schema.Deck

ĐỘ ỔN ĐỊNH (sửa lỗi cũ):
  - Sinh nội dung THEO TỪNG SLIDE (mỗi lần gọi chỉ viết vài ý cho 1 tiêu đề) —
    việc nhẹ này model 8B làm rất tốt, thay vì ép 1 JSON khổng lồ cho cả bài.
  - Dùng văn bản thường + parse khoan dung -> không phụ thuộc tên key JSON.
  - Slide nào model trả thiếu/ngắn -> thử lại 1 lần; vẫn không được -> nội dung
    dự phòng. Luôn bảo đảm mỗi slide có đủ ý.
"""

from __future__ import annotations
import llm
from schema import Outline, Deck, Slide

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


class ContentAgent:
    def __init__(self, model_name: str = "llama3.1:8b",
                 api_url: str = llm.GEN_API,
                 points_per_slide: int = 3, min_points: int = 3,
                 max_retry: int = 1):
        self.model_name = model_name
        self.api_url = api_url
        self.points_per_slide = points_per_slide
        self.min_points = min_points
        self.max_retry = max_retry

    # ── API công khai ────────────────────────────────────────────────────────
    def write(self, outline: Outline, on_progress=None) -> Deck:
        def emit(msg):
            print(msg)
            if on_progress:
                try: on_progress(msg)
                except Exception: pass

        total = len(outline.briefs)
        emit(f"[Content] Viết nội dung cho {total} slide (theo từng slide)...")

        # Tạo chuỗi dàn ý toàn bài làm ngữ cảnh chung (Global Context)
        global_outline_str = "\n".join([f"Slide {idx}: {b.title}" for idx, b in enumerate(outline.briefs, 1)])

        slides: list[Slide] = []
        for i, brief in enumerate(outline.briefs, 1):
            emit(f"[Content] Slide {i}/{total}: {brief.title}")
            
            # Nếu là slide Mục lục / Chương trình nghị sự, tự động sinh nội dung từ outline
            clean_title = llm.normalize_vietnamese(brief.title).strip().lower()
            is_agenda = (
                brief.role == "agenda" or 
                "nghị sự" in clean_title or 
                "mục lục" in clean_title or 
                "agenda" in clean_title
            )
            if is_agenda:
                agenda_titles = [b.title for b in outline.briefs if b.role not in ("intro", "conclusion") and not ("nghị sự" in llm.normalize_vietnamese(b.title).lower() or "mục lục" in llm.normalize_vietnamese(b.title).lower() or "agenda" in llm.normalize_vietnamese(b.title).lower())]
                points = [f"Phần {idx}: {title}" for idx, title in enumerate(agenda_titles[:4], 1)]
                if len(agenda_titles) > 4:
                    points.append("Các nội dung thảo luận liên quan & Kết luận")
                emit(f"[Content]   ✔ Tự động điền mục lục với {len(points)} phần.")
            else:
                points = self._points_for(outline.title, brief, global_outline_str=global_outline_str)

                attempt = 0
                while len(points) < self.min_points and attempt < self.max_retry:
                    attempt += 1
                    emit(f"[Content]   ↻ thiếu ý, sinh lại (lần {attempt})...")
                    points = self._points_for(outline.title, brief, more=True, global_outline_str=global_outline_str)

                if len(points) < self.min_points:
                    emit(f"[Content]   ⚠ dùng nội dung dự phòng cho slide {i}.")
                    points = self._fallback_points(brief)
                else:
                    emit(f"[Content]   ✔ {len(points)} ý.")

            slides.append(Slide(title=brief.title,
                                points=points[:4],
                                image_query=brief.image_query))

        emit(f"[Content] ✔ Hoàn tất {len(slides)} slide nội dung.")
        return Deck(title=outline.title, subtitle=outline.subtitle, slides=slides)

    # ── Sinh ý cho 1 slide (văn bản thường) ──────────────────────────────────
    def _points_for(self, deck_title: str, brief, more: bool = False, global_outline_str: str = "") -> list[str]:
        n = self.points_per_slide + (1 if more else 0)
        prompt = (
            "Bạn là một Giáo sư/Chuyên gia đầu ngành có kiến thức sâu rộng. "
            "Hãy biên soạn nội dung chuyên sâu, giàu thông tin và mang tính học thuật cao cho MỘT slide.\n\n"
            f"Chủ đề bài thuyết trình: \"{deck_title}\"\n"
            "Cấu trúc toàn bài (để tham khảo ngữ cảnh, tránh lặp lại hoặc viết lệch hướng):\n"
            f"{global_outline_str}\n\n"
            f"Tiêu đề slide hiện tại: \"{brief.title}\"\n"
            f"Trọng tâm của slide này: {brief.focus}\n\n"
            "YÊU CẦU NGHIÊM NGẶT VỀ NỘI DUNG:\n"
            "- CẤM TUYỆT ĐỐI các câu chung chung, sáo rỗng hoặc mang tính mở đầu/kéo dài (ví dụ: 'Vấn đề này rất quan trọng', 'Cần được phân tích kỹ', 'Khái niệm này có nhiều ứng dụng').\n"
            "- BẮT BUỘC mỗi ý phải chứa đựng thông tin thực chất: định nghĩa kỹ thuật chính xác, giải thích cơ chế vận hành, hoặc ví dụ thực tế cụ thể.\n"
            "- CẤM TUYỆT ĐỐI việc tự bịa đặt, chế tạo các số liệu thống kê giả (như tự đặt ra tỷ lệ %, dung lượng bộ nhớ MB, tần số kHz nếu không có dữ liệu thực tế chính xác được thừa nhận). Nếu không có số liệu thực tế chuẩn xác, hãy tập trung giải thích cơ chế kỹ thuật và ứng dụng thực tế.\n"
            "- CẤM TUYỆT ĐỐI tự dịch sai hoặc bịa ra các thuật ngữ/thuật toán không tồn tại trong literature (ví dụ: không dùng các thuật ngữ lạ như 'thuật toán treo đè' hay 'hanging algorithm' cho thuật toán Viterbi; khi so sánh thuật toán, chỉ đối sánh với các đối thủ có thật như Fano, BCJR, HMM, Dijkstra, tuyệt đối không bịa ra các tên như 'Vantablack' - vốn là một loại vật liệu hấp thụ ánh sáng chứ không phải thuật toán).\n\n"
            "YÊU CẦU ĐỊNH DẠNG ĐẦU RA (CỰC KỲ QUAN TRỌNG):\n"
            "1. Tuyệt đối KHÔNG viết phân tích, suy nghĩ hay bất kỳ lời dẫn nào ở phía trước.\n"
            "2. Bắt đầu câu trả lời bằng dòng phân tách: `---OUTPUT---` (viết hoa, nằm trên dòng riêng).\n"
            "3. Ngay phía sau dòng `---OUTPUT---`, in ra đúng các ý slide:\n"
            f"  - Viết đúng {n} ý.\n"
            "  - Mỗi ý nằm trên MỘT dòng bắt đầu bằng '- '.\n"
            "  - Mỗi ý là một câu/đoạn hoàn chỉnh từ 25-45 từ, tiếng Việt, hành văn học thuật, chuyên nghiệp.\n"
            "  - Không thêm bất cứ ký hiệu số thứ tự hay lời dẫn nào dưới dòng `---OUTPUT---`."
            f"{get_nlp_warning(deck_title + ' ' + brief.title)}"
        )
        try:
            text = llm.generate(prompt, self.model_name, self.api_url,
                                num_predict=1200, temperature=0.7)
        except Exception as e:
            print(f"[Content] Lỗi gọi Ollama: {e}")
            return []
        points = llm.parse_points(text, min_words=6)
        # chỉ giữ các ý đủ dài, tối đa 4 ý
        points = [p for p in points if len(p.split()) >= 6][:4]
        return points

    # ── Nội dung dự phòng (bám theo focus của Planner) ───────────────────────
    def _fallback_points(self, brief) -> list[str]:
        focus = brief.focus or brief.title
        return [
            f"{focus} Đây là nội dung quan trọng cần được phân tích kỹ để người "
            f"nghe nắm được bản chất và ý nghĩa của vấn đề trong bối cảnh hiện nay.",
            f"Xét trên nhiều khía cạnh, '{brief.title}' cho thấy những điểm đáng "
            f"chú ý, đòi hỏi cách tiếp cận hệ thống và liên hệ với thực tiễn cụ thể.",
            f"Cuối cùng, cần kết nối nội dung này với mục tiêu chung của bài "
            f"thuyết trình nhằm bảo đảm tính mạch lạc, logic và sức thuyết phục.",
        ]


# ── Chạy/test độc lập ────────────────────────────────────────────────────────
if __name__ == "__main__":
    import json
    from schema import SlideBrief
    sample = Outline(
        title="Lợi ích của AI trong giáo dục",
        subtitle="Bài demo ContentAgent",
        briefs=[
            SlideBrief("Giới thiệu AI trong giáo dục", "intro",
                       "Định nghĩa và bối cảnh.", "ai education intro"),
            SlideBrief("Cá nhân hoá học tập", "analysis",
                       "AI cá nhân hoá lộ trình học.", "personalized learning"),
            SlideBrief("Kết luận và Hỏi đáp", "conclusion",
                       "Tóm tắt và hướng phát triển.", "future education"),
        ],
    )
    deck = ContentAgent().write(sample)
    print(json.dumps(deck.to_dict(), ensure_ascii=False, indent=2))
