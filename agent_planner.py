"""
agent_planner.py — AGENT 1 · PLANNER  (Phụ trách: Thành viên A)
==============================================================
NHIỆM VỤ ("Nhận chủ đề"): nhận chủ đề -> tự quyết bố cục bài (danh sách slide,
vai trò từng slide, từ khoá ảnh tiếng Anh). KHÔNG viết nội dung chi tiết.

INPUT : topic: str            OUTPUT: schema.Outline

ĐỘ ỔN ĐỊNH (sửa lỗi cũ):
  - Hỏi model bằng VĂN BẢN THƯỜNG (danh sách tiêu đề), KHÔNG ép JSON -> tránh
    việc model 8B chỉ trả 1 mục.
  - Dù model trả ít / sai / rỗng, Planner luôn BẢO ĐẢM đủ số slide bằng cách
    chèn thêm các mục chuẩn -> không bao giờ ra deck 1 slide.
"""

from __future__ import annotations
import llm
from schema import Outline, SlideBrief


# Câu truy vấn ảnh (tiếng Anh) mặc định theo vai trò slide
_ROLE_QUERY = {
    "intro":       "introduction concept overview",
    "analysis":    "analysis research data chart",
    "application": "real world application technology",
    "challenge":   "challenge solution strategy",
    "conclusion":  "conclusion future innovation success",
}

# Các mục chuẩn để chèn thêm khi model trả thiếu (không trùng phần intro/kết)
_PAD_SECTIONS = [
    ("Bối cảnh và xu hướng",      "analysis",    "background trend statistics"),
    ("Phân tích chi tiết",        "analysis",    "analysis research detail"),
    ("Ứng dụng thực tế",          "application", "real world application practice"),
    ("Lợi ích và giá trị mang lại", "analysis",  "benefit value growth chart"),
    ("Thách thức và giải pháp",   "challenge",   "challenge solution problem solving"),
    ("Bài học và khuyến nghị",    "analysis",    "lesson recommendation insight"),
]


class PlannerAgent:
    def __init__(self, model_name: str = "llama3.1:8b",
                 api_url: str = llm.GEN_API, num_slides: int = 8):
        self.model_name = model_name
        self.api_url = api_url
        self.num_slides = max(6, num_slides)

    # ── Đoán vai trò slide từ tiêu đề ────────────────────────────────────────
    @staticmethod
    def _role_for(title: str) -> str:
        t = title.lower()
        if any(k in t for k in ("kết luận", "tổng kết", "hỏi đáp", "q&a",
                                "kết thúc", "cảm ơn", "tài liệu tham khảo")):
            return "conclusion"
        if any(k in t for k in ("giới thiệu", "tổng quan", "mở đầu",
                                "khái niệm", "định nghĩa")):
            return "intro"
        if any(k in t for k in ("ứng dụng", "triển khai", "thực tiễn", "thực tế")):
            return "application"
        if any(k in t for k in ("thách thức", "khó khăn", "hạn chế", "rủi ro")):
            return "challenge"
        return "analysis"


    # ── API công khai ────────────────────────────────────────────────────────
    def plan(self, topic: str, on_progress=None) -> Outline:
        def emit(msg):
            print(msg)
            if on_progress:
                try: on_progress(msg)
                except Exception: pass

        emit(f"[Planner] Phân tích chủ đề: {topic}")
        titles = self._titles_from_llm(topic, emit)
        if titles:
            emit(f"[Planner] Model gợi ý {len(titles)} tiêu đề.")
        else:
            emit("[Planner] Model không trả về tiêu đề — dùng bố cục chuẩn.")

        briefs = self._build_briefs(topic, titles)
        emit(f"[Planner] ✔ Dàn ý hoàn chỉnh: {len(briefs)} slide.")

        return Outline(
            title=topic.strip().capitalize(),
            subtitle="Bài thuyết trình do AI Agent biên soạn",
            briefs=briefs,
        )

    # ── Hỏi model (văn bản thường) ───────────────────────────────────────────
    def _titles_from_llm(self, topic: str, emit) -> list[tuple[str, str]]:
        n = self.num_slides
        prompt = (
            f"Hãy đề xuất {n} tiêu đề slide cho một bài thuyết trình tiếng Việt "
            f"về chủ đề: \"{topic}\".\n"
            "Quy tắc:\n"
            f"- In đúng {n} dòng, mỗi dòng MỘT tiêu đề, đánh số 1 đến {n}.\n"
            "- Slide 1 là phần Giới thiệu, slide cuối là phần Kết luận.\n"
            "- Sau mỗi tiêu đề, thêm dấu ' :: ' rồi 2-4 TỪ KHÓA TIẾNG ANH (chỉ "
            "tiếng Anh) để tìm ảnh minh hoạ.\n"
            "- KHÔNG viết gì khác ngoài các dòng tiêu đề.\n"
            "Ví dụ:\n"
            "1. Giới thiệu về chủ đề :: introduction concept overview\n"
            "2. Phân tích hiện trạng :: analysis current situation data"
        )
        try:
            text = llm.generate(prompt, self.model_name, self.api_url,
                                num_predict=400, temperature=0.5)
        except Exception as e:
            emit(f"[Planner] Lỗi gọi Ollama: {e}")
            return []
        return llm.parse_titles(text)

    # ── Ráp dàn ý + BẢO ĐẢM đủ slide ─────────────────────────────────────────
    def _build_briefs(self, topic: str, titles) -> list[SlideBrief]:
        content: list[SlideBrief] = []   # các slide nội dung (giữa)
        conclusion: SlideBrief | None = None
        seen = set()

        for i, (title, query) in enumerate(titles):
            key = title.lower().strip()
            if key in seen:
                continue
            seen.add(key)
            role = "intro" if i == 0 else self._role_for(title)
            brief = SlideBrief(title, role,
                               f"Trình bày rõ về: {title}",
                               self._fix_query(query, role))
            if role == "conclusion" and conclusion is None:
                conclusion = brief          # tách riêng để đưa xuống cuối
            else:
                content.append(brief)

        # Bảo đảm có slide mở đầu ở đầu danh sách
        if not content:
            content.append(SlideBrief(
                f"Giới thiệu về {topic}", "intro",
                "Định nghĩa, bối cảnh và tầm quan trọng của chủ đề.",
                _ROLE_QUERY["intro"]))
        if not any(b.role == "intro" for b in content):
            content[0].role = "intro"
            content[0].image_query = self._fix_query(content[0].image_query, "intro")

        # Chèn thêm mục chuẩn (vào GIỮA) nếu còn thiếu, chừa chỗ cho kết luận
        for title, role, query in _PAD_SECTIONS:
            if len(content) >= self.num_slides - 1:
                break
            if title.lower() in seen:
                continue
            seen.add(title.lower())
            content.append(SlideBrief(title, role,
                                      f"Trình bày rõ về: {title}", query))

        # Kết luận luôn ở CUỐI
        if conclusion is None:
            conclusion = SlideBrief(
                "Kết luận và Hỏi đáp", "conclusion",
                "Tóm tắt ý chính và định hướng tương lai.",
                _ROLE_QUERY["conclusion"])

        return content + [conclusion]

    # ── Vá từ khoá ảnh: phải là tiếng Anh, đủ nghĩa ──────────────────────────
    def _fix_query(self, query: str, role: str) -> str:
        q = (query or "").strip()
        if q and q.isascii() and 2 <= len(q.split()) <= 8:
            return q[:60]
        return _ROLE_QUERY.get(role, "concept overview presentation")


# ── Chạy/test độc lập ────────────────────────────────────────────────────────
if __name__ == "__main__":
    import sys, json
    topic = sys.argv[1] if len(sys.argv) > 1 else "Lợi ích của AI trong giáo dục"
    outline = PlannerAgent().plan(topic)
    print(json.dumps(outline.to_dict(), ensure_ascii=False, indent=2))
