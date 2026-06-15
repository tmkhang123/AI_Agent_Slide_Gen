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

        slides: list[Slide] = []
        for i, brief in enumerate(outline.briefs, 1):
            emit(f"[Content] Slide {i}/{total}: {brief.title}")
            points = self._points_for(outline.title, brief)

            attempt = 0
            while len(points) < self.min_points and attempt < self.max_retry:
                attempt += 1
                emit(f"[Content]   ↻ thiếu ý, sinh lại (lần {attempt})...")
                points = self._points_for(outline.title, brief, more=True)

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
    def _points_for(self, deck_title: str, brief, more: bool = False) -> list[str]:
        n = self.points_per_slide + (1 if more else 0)
        prompt = (
            f"Bạn là chuyên gia soạn thuyết trình. Viết nội dung cho MỘT slide.\n"
            f"Bài thuyết trình: \"{deck_title}\".\n"
            f"Tiêu đề slide: \"{brief.title}\".\n"
            f"Trọng tâm: {brief.focus}\n\n"
            "Yêu cầu:\n"
            f"- Viết đúng {n} ý.\n"
            "- Mỗi ý nằm trên MỘT dòng, bắt đầu bằng '- '.\n"
            "- Mỗi ý là một câu/đoạn HOÀN CHỈNH 25-45 từ, tiếng Việt, học thuật, "
            "giàu thông tin, không lặp lại tiêu đề.\n"
            "- KHÔNG viết mở đầu, KHÔNG đánh số, chỉ in các dòng ý."
        )
        try:
            text = llm.generate(prompt, self.model_name, self.api_url,
                                num_predict=650, temperature=0.7)
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
