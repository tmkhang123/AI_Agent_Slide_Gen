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
import re
import llm
from schema import Outline, SlideBrief

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

def _format_presentation_title(title: str) -> str:
    """Viết hoa đúng các từ viết tắt chuyên ngành và viết hoa chữ đầu tiên."""
    t = title.strip()
    if not t:
        return ""
    
    # Loại bỏ các ký tự markdown ở đầu và cuối trước khi format để từ chữ cái đầu tiên được viết hoa chính xác
    t = re.sub(r'^\s*[\*_#]+|[\*_#]+\s*$', '', t)
    t = t.replace("<b>", "").replace("</b>", "").strip()
    if not t:
        return ""
        
    acronyms = ["nlp", "ai", "gpt", "api", "gui", "llm", "pptx", "json", "cli", "ddg", "cs", "bert", "lstm", "rnn", "cnn", "vit", "rag", "gan", "vae", "mlp", "svm", "knn", "sql", "nosql", "iot", "ar", "vr", "xr"]
    words = t.split()
    formatted_words = []
    for idx, w in enumerate(words):
        clean_w = re.sub(r'[^\w]', '', w).lower()
        if clean_w in acronyms:
            w_replaced = re.sub(re.escape(clean_w), clean_w.upper(), w, flags=re.IGNORECASE)
            formatted_words.append(w_replaced)
        else:
            if idx == 0:
                formatted_words.append(w.capitalize())
            else:
                formatted_words.append(w)
    return " ".join(formatted_words)


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

        # Trích xuất các từ khóa chủ đề (tiếng Anh/viết tắt/tên riêng không dấu)
        topic_keywords = []
        vietnamese_stops = {
            "thuật", "toán", "lợi", "ích", "của", "trong", "và", "về", 
            "các", "bài", "thuyết", "trình", "giới", "thiệu", "tổng", 
            "quan", "phân", "tích", "so", "sánh", "giáo", "dục"
        }
        for w in topic.split():
            clean_w = re.sub(r'[^\w]', '', w).lower()
            if not clean_w or clean_w in vietnamese_stops:
                continue
            if clean_w.isascii():
                topic_keywords.append(clean_w)
        if not topic_keywords:
            topic_keywords = ["technology"]

        briefs = self._build_briefs(topic, titles, topic_keywords)
        emit(f"[Planner] ✔ Dàn ý hoàn chỉnh: {len(briefs)} slide.")

        return Outline(
            title=_format_presentation_title(topic),
            subtitle="Bài thuyết trình do AI Agent biên soạn",
            briefs=briefs,
        )

    # ── Hỏi model (văn bản thường) ───────────────────────────────────────────
    def _titles_from_llm(self, topic: str, emit) -> list[tuple[str, str]]:
        n = self.num_slides
        prompt = (
            "Bạn là một chuyên gia nghiên cứu và thiết lập bài giảng học thuật. "
            f"Hãy lên dàn ý cho một bài thuyết trình tiếng Việt chuyên sâu về chủ đề: \"{topic}\".\n\n"
            "Hãy thực hiện theo quy trình lập luận sau:\n"
            "Bước 1: Phân tích sâu về chủ đề (HÃY SUY NGHĨ VÀ VIẾT BẰNG TIẾNG VIỆT):\n"
            "  - Định nghĩa chính xác phạm vi kiến thức, tránh các sự nhầm lẫn khái niệm trùng tên.\n"
            "  - Liệt kê các khía cạnh chuyên môn cốt lõi, cơ chế vận hành, số liệu quan trọng hoặc nhánh kiến thức cần làm rõ.\n"
            "  - Xác định đối tượng người nghe và mục tiêu cụ thể để điều chỉnh chiều sâu.\n"
            f"Bước 2: Dựa trên phân tích trên, hãy đề xuất dàn ý gồm {n} slide.\n\n"
            "QUY TẮC ĐẦU RA CỦA DÀN Ý:\n"
            f"- Viết đúng {n} dòng tiêu đề slide dưới phân tích của bạn, mỗi dòng bắt đầu bằng số thứ tự '1.' đến '{n}.'\n"
            "- Slide 1 luôn là Giới thiệu tổng quan, slide cuối luôn là Kết luận.\n"
            "- Sau mỗi tiêu đề, thêm dấu ' :: ' rồi đến 2-4 TỪ KHÓA TIẾNG ANH (chỉ dùng tiếng Anh, mô tả trực quan, tránh các từ trừu tượng) để tìm ảnh minh hoạ.\n"
            "- CẤM các từ khóa tiếng Anh dễ sinh ra ảnh người hoặc phong cảnh chung chung không liên quan (như 'man', 'human', 'people', 'person', 'team', 'working', 'nature', 'outdoor', 'indoor', 'office').\n"
            "- ƯU TIÊN các từ mô tả trực quan sơ đồ kỹ thuật, khái niệm hoặc minh họa công nghệ (như 'diagram', 'architecture', 'vector', 'concept', 'flowchart', 'infographic', 'neural network', 'mechanism').\n"
            "- Khi đối sánh thuật toán hoặc phân tích so sánh, bắt buộc lồng ghép tên chủ đề cụ thể vào từ khóa tìm ảnh (ví dụ: 'viterbi decoding comparison' hoặc 'viterbi algorithm structure' thay vì chỉ dùng 'algorithm flowchart' hay 'comparison diagram' chung chung) để tránh ra các sơ đồ cộng trừ cơ bản không liên quan.\n"
            "Ví dụ:\n"
            "1. Tổng quan về xử lý ngôn ngữ tự nhiên :: introduction neural network computer\n"
            "2. Cơ chế phân tích cú pháp :: syntax parsing diagram algorithm"
            f"{get_nlp_warning(topic)}"
        )
        try:
            text = llm.generate(prompt, self.model_name, self.api_url,
                                num_predict=700, temperature=0.5)
        except Exception as e:
            emit(f"[Planner] Lỗi gọi Ollama: {e}")
            return []
        return llm.parse_titles(text)

    # ── Ráp dàn ý + BẢO ĐẢM đủ slide ─────────────────────────────────────────
    def _build_briefs(self, topic: str, titles, topic_keywords: list[str]) -> list[SlideBrief]:
        content: list[SlideBrief] = []   # các slide nội dung (giữa)
        conclusion: SlideBrief | None = None
        seen = set()

        for i, (title, query) in enumerate(titles):
            key = title.lower().strip()
            if key in seen:
                continue
            seen.add(key)
            role = "intro" if i == 0 else self._role_for(title)
            formatted_title = _format_presentation_title(title)
            brief = SlideBrief(formatted_title, role,
                               f"Trình bày rõ về: {formatted_title}",
                               self._fix_query(query, role, topic_keywords))
            if role == "conclusion" and conclusion is None:
                conclusion = brief          # tách riêng để đưa xuống cuối
            else:
                content.append(brief)

        # Bảo đảm có slide mở đầu ở đầu danh sách
        if not content:
            intro_title = _format_presentation_title(f"Giới thiệu về {topic}")
            content.append(SlideBrief(
                intro_title, "intro",
                f"Định nghĩa, bối cảnh và tầm quan trọng của {intro_title}.",
                self._fix_query("", "intro", topic_keywords)))
        if not any(b.role == "intro" for b in content):
            content[0].role = "intro"
            content[0].image_query = self._fix_query(content[0].image_query, "intro", topic_keywords)

        # Tự động chèn slide Chương trình nghị sự / Mục lục làm slide thứ 2
        agenda_title = "Chương trình nghị sự"
        agenda_kw = topic_keywords[0] if topic_keywords else "technology"
        agenda_brief = SlideBrief(
            title=agenda_title,
            role="agenda",
            focus="Tóm tắt ngắn gọn cấu trúc và các phần chính của bài thuyết trình.",
            image_query=f"abstract structure diagram {agenda_kw}"
        )
        # Chèn vào vị trí thứ 2 (chỉ số 1)
        content.insert(1, agenda_brief)
        seen.add(agenda_title.lower())

        # Chèn thêm mục chuẩn (vào GIỮA) nếu còn thiếu, chừa chỗ cho kết luận
        for title, role, query in _PAD_SECTIONS:
            if len(content) >= self.num_slides - 1:
                break
            if title.lower() in seen:
                continue
            seen.add(title.lower())
            formatted_title = _format_presentation_title(title)
            content.append(SlideBrief(formatted_title, role,
                                      f"Trình bày rõ về: {formatted_title}", 
                                      self._fix_query(query, role, topic_keywords)))

        # Kết luận luôn ở CUỐI
        if conclusion is None:
            conclusion = SlideBrief(
                "Kết luận và Hỏi đáp", "conclusion",
                "Tóm tắt ý chính và định hướng tương lai.",
                self._fix_query("", "conclusion", topic_keywords))

        return content + [conclusion]

    # ── Vá từ khoá ảnh: phải là tiếng Anh, đủ nghĩa ──────────────────────────
    def _fix_query(self, query: str, role: str, topic_keywords: list[str]) -> str:
        q = (query or "").strip().lower()
        q = re.sub(r'\*\*|__|\*|_', '', q)
        
        if not q or not q.isascii() or not (2 <= len(q.split()) <= 8):
            q = _ROLE_QUERY.get(role, "concept overview presentation")
            
        # Đảm bảo từ khóa chính của chủ đề có mặt trong query để tránh ảnh generic
        if topic_keywords:
            words_in_q = q.split()
            if not any(tk in words_in_q for tk in topic_keywords):
                q = f"{topic_keywords[0]} {q}"
                
        # Cấm các từ khóa tạo ra ảnh người hoặc phong cảnh chung chung không liên quan
        forbidden = {"man", "human", "people", "person", "team", "working", "nature", "outdoor", "indoor", "office"}
        clean_words = [w for w in q.split() if w not in forbidden]
        if not clean_words:
            clean_words = ["technology", "concept"]
        return " ".join(clean_words[:6])


# ── Chạy/test độc lập ────────────────────────────────────────────────────────
if __name__ == "__main__":
    import sys, json
    topic = sys.argv[1] if len(sys.argv) > 1 else "Lợi ích của AI trong giáo dục"
    outline = PlannerAgent().plan(topic)
    print(json.dumps(outline.to_dict(), ensure_ascii=False, indent=2))
