"""
llm.py — GIAO TIẾP OLLAMA + BỘ PHÂN TÍCH CHỐNG LỖI
==================================================
Đây là phần lõi quyết định độ ổn định của cả hệ thống.

Bài học rút ra từ lỗi cũ:
  - Ép model nhỏ (llama3.1:8b) xuất 'format=json' chứa NHIỀU slide trong MỘT
    lần gọi -> model hay "đóng" JSON sớm -> chỉ ra 1 slide, hoặc đặt sai tên
    key -> parse rỗng -> rơi về dự phòng.

Giải pháp ở đây:
  - generate(): gọi Ollama ở chế độ VĂN BẢN THƯỜNG (không format=json), giới
    hạn token, có nhiệt độ hợp lý.
  - parse_titles()/parse_points(): phân tích kết quả văn bản một cách KHOAN
    DUNG — chấp nhận gạch đầu dòng, đánh số, "Slide 1:", dấu ::/| ngăn cách,
    bỏ câu mở đầu thừa... -> luôn moi được dữ liệu nếu model có trả lời.
  - check_ollama(): kiểm tra Ollama sống và có model trước khi chạy.
"""

from __future__ import annotations
import re
import requests
import unicodedata

GEN_API  = "http://localhost:11434/api/generate"
TAGS_API = "http://localhost:11434/api/tags"

# Lưu trữ lý do dừng của lần gọi LLM gần nhất
LAST_DONE_REASON = "stop"


# ─────────────────────────────────────────────────────────────────────────────
# Gọi Ollama
# ─────────────────────────────────────────────────────────────────────────────

def check_ollama(model_name: str, tags_api: str = TAGS_API, timeout: int = 5):
    """Trả (ok: bool, message: str). Kiểm tra Ollama chạy chưa & có model chưa."""
    try:
        r = requests.get(tags_api, timeout=timeout)
        if r.status_code != 200:
            return False, f"Ollama trả mã {r.status_code}."
        names = [m.get("name", "") for m in r.json().get("models", [])]
        base = model_name.split(":")[0]
        if any(n == model_name or n.startswith(base) for n in names):
            return True, "OK"
        have = ", ".join(names) or "(chưa có model nào)"
        return False, (f"Chưa thấy model '{model_name}'. Đang có: {have}. "
                       f"Hãy chạy: ollama pull {model_name}")
    except Exception as e:
        return False, (f"Không kết nối được Ollama ({e}). "
                       "Hãy mở terminal chạy 'ollama serve' rồi thử lại.")


def generate(prompt: str, model: str, api_url: str = GEN_API,
             timeout: int = 300, num_predict: int = 512,
             temperature: float = 0.6) -> str:
    """Gọi /api/generate ở chế độ văn bản thường. Trả chuỗi (có thể rỗng)."""
    global LAST_DONE_REASON
    LAST_DONE_REASON = "stop"
    payload = {
        "model": model,
        "prompt": prompt,
        "stream": False,
        "options": {"temperature": temperature, "num_predict": num_predict},
    }
    resp = requests.post(api_url, json=payload, timeout=timeout)
    resp.raise_for_status()
    res_json = resp.json()
    LAST_DONE_REASON = res_json.get("done_reason", "stop")
    return (res_json.get("response") or "").strip()


# ─────────────────────────────────────────────────────────────────────────────
# Phân tích văn bản (khoan dung)
# ─────────────────────────────────────────────────────────────────────────────

_FENCE    = re.compile(r"```[a-zA-Z]*")
_BULLET   = re.compile(r"^\s*(?:\d{1,2}\s*[\.\):]|[-*•▪◦‣·–—])\s*")
_SLIDEPFX = re.compile(r"^\s*slide\s*\d+\s*[:.\-)]*\s*", re.IGNORECASE)
_SEP      = re.compile(r"\s*(?:::|\||–|—|\bimage\s*:)\s*", re.IGNORECASE)

_IGNORE_PATTERNS = re.compile(
    r'^\s*(?:kiểm tra|bôi đậm|tối ưu|trả về|yêu cầu|nhiệm vụ|quy trình|bước \d|hướng dẫn|chuyên gia|đã tối ưu|kết quả|tổng kết|lọc bỏ|lưu ý|chú ý|phản biện|critic|slide \d|tiêu đề|nội dung)',
    re.IGNORECASE
)

_LEAK_KEYWORDS = [
    "kiểm tra tính thực chất",
    "bôi đậm từ khóa",
    "tối ưu độ dài",
    "trả về đúng số lượng",
    "lọc bỏ câu sáo rỗng",
    "cấm bịa đặt",
    "số liệu fabricated",
    "thuật ngữ lạ",
    "tôi đã lọc bỏ",
    "tôi đã tối ưu",
    "tôi đã thêm",
    "tôi không phát hiện",
    "quy trình phản biện",
    "phản biện & cải thiện",
    "yêu cầu định dạng",
    "yêu cầu nghiêm ngặt",
]


def _clean(text: str) -> str:
    text = _FENCE.sub("", text or "")
    return text.replace("`", "").strip()


def normalize_vietnamese(text: str) -> str:
    """Chuẩn hóa văn bản Tiếng Việt về dạng NFC để so sánh chính xác."""
    if not text:
        return ""
    return unicodedata.normalize('NFC', text)


def is_heading_style(text: str) -> bool:
    """Kiểm tra xem một gạch đầu dòng có phải dạng tiêu đề mục ngắn không."""
    clean = text.strip()
    clean_no_md = re.sub(r'\*\*|__|\*|_|<b>|</b>', '', clean).strip()
    words = clean_no_md.split()
    
    # Rất ngắn (dưới 5 từ)
    if len(words) < 5:
        return True
        
    # Toàn bộ câu bị bọc trong in nghiêng (không phải bôi đậm) và ngắn dưới 12 từ
    # Ví dụ: *Cơ chế hoạt động của Viterbi*
    is_wrapped = (
        (clean.startswith('*') and clean.endswith('*') and not clean.startswith('**')) or
        (clean.startswith('_') and clean.endswith('_') and not clean.startswith('__'))
    )
    if is_wrapped and len(words) < 12:
        return True
        
    # Các từ khóa thường dùng bắt đầu tiêu đề/mục lục và ngắn dưới 10 từ
    heading_prefixes = (
        "phân tích", "cơ chế", "khái niệm", "định nghĩa", 
        "tổng quan", "vai trò", "ứng dụng", "thách thức", 
        "giải pháp", "ưu điểm", "nhược điểm", "kết luận",
        "hướng dẫn", "bước", "quy trình", "so sánh"
    )
    lower_clean = clean_no_md.lower()
    if lower_clean.startswith(heading_prefixes) and len(words) < 10:
        return True
        
    return False


def is_truncated(text: str) -> bool:
    """Kiểm tra xem câu có bị cắt cụt giữa chừng hay không."""
    # Chỉ coi là cắt cụt nếu LLM bị hết token (done_reason == "length")
    # VÀ câu cuối cùng không kết thúc bằng các dấu câu hợp lệ.
    if LAST_DONE_REASON != "length":
        return False
        
    s = text.strip()
    if not s:
        return False
    # Loại bỏ các ký tự bọc markdown ở cuối để lấy ký tự chữ/dấu thực tế
    s_clean = re.sub(r'[\*_#\s]+$', '', s)
    s_clean = s_clean.replace("</b>", "").strip()
    if not s_clean:
        return False
    return s_clean[-1] not in ('.', '!', '?', '"', '”', '’', ')')


def clean_hallucinations(text: str) -> str:
    """Loại bỏ/thay thế các thuật ngữ bịa đặt/hallucination cụ thể."""
    text = re.sub(r'\bvantablack\b', 'Dijkstra', text, flags=re.IGNORECASE)
    text = re.sub(r'thuật toán treo đè', 'thuật toán tìm kiếm tối ưu', text, flags=re.IGNORECASE)
    return text


def parse_titles(text: str) -> list[tuple[str, str]]:
    """
    Moi ra danh sách (tiêu đề, image_query) từ câu trả lời của model.
    Chấp nhận: '1. Tiêu đề :: keywords', '- Tiêu đề', 'Slide 2: Tiêu đề | kw'...
    """
    rows = []
    for raw in _clean(text).splitlines():
        line = raw.strip()
        if not line:
            continue
        had_marker = bool(_BULLET.match(line)) or bool(_SLIDEPFX.match(line))
        line = _BULLET.sub("", line)
        line = _SLIDEPFX.sub("", line).strip().strip('"').strip()
        if not line:
            continue
        # bỏ câu mở đầu kiểu "Đây là danh sách:" (ngắn & kết thúc bằng ':')
        if line.endswith(":") and len(line.split()) <= 8:
            continue
        parts = _SEP.split(line, maxsplit=1)
        title = parts[0].strip(" .-–—")
        query = parts[1].strip() if len(parts) > 1 else ""
        if not title or len(title) > 140:
            continue
        
        # Xác định xem dòng này có đúng định dạng slide hay không
        # (Có separator :: hoặc bắt đầu bằng số/Slide prefix)
        is_slide_format = bool(re.match(r'^\s*\d+\s*[\.\):]', raw)) or bool(_SLIDEPFX.match(raw)) or (len(parts) > 1)
        rows.append((title, query, had_marker, is_slide_format))

    # Nếu có các dòng đúng định dạng slide -> chỉ giữ các dòng đó (lọc bỏ phần phân tích CoT thô)
    slide_rows = [(t, q, m) for (t, q, m, sf) in rows if sf]
    if len(slide_rows) >= 2:
        rows = slide_rows
    else:
        rows = [(t, q, m) for (t, q, m, sf) in rows]

    # Nếu có >=2 dòng được đánh dấu (số/gạch) -> chỉ lấy các dòng đó (bỏ rác)
    marked = [(t, q) for (t, q, m) in rows if m]
    if len(marked) >= 2:
        return marked
    return [(t, q) for (t, q, _) in rows]


def parse_points(text: str, min_words: int = 4) -> list[str]:
    """
    Moi ra danh sách 'ý' (câu/đoạn) từ câu trả lời của model.
    Ưu tiên dòng có gạch/đánh số; nếu không có thì lấy mọi dòng đủ dài.
    """
    clean_text = _clean(text)
    
    # Tìm kiếm delimiter ---OUTPUT--- để cắt phần suy nghĩ/giải thích của LLM ở phía trước
    parts = re.split(r'---+\s*OUTPUT\s*---+|===+\s*OUTPUT\s*===+', clean_text, flags=re.IGNORECASE)
    if len(parts) > 1:
        clean_text = parts[-1]

    parsed = []
    any_marker = False
    for raw in clean_text.splitlines():
        line = raw.strip()
        if not line:
            continue
        
        # Lọc bỏ dòng chứa chỉ dẫn hệ thống bị rò rỉ
        line_no_md = re.sub(r'\*\*|__|\*|_|<b>|</b>', '', line).strip()
        line_lower = line_no_md.lower()
        if _IGNORE_PATTERNS.match(line) or _IGNORE_PATTERNS.match(line_no_md):
            continue
            
        if any(kw in line_lower for kw in _LEAK_KEYWORDS):
            continue
            
        # Lọc bỏ các dòng có định dạng tiêu đề phụ lục/mục lục cột
        if is_heading_style(line):
            continue
            
        marker = bool(_BULLET.match(line))
        any_marker = any_marker or marker
        
        bullet_free = _BULLET.sub("", line).strip().strip('"').strip()
        # Kiểm tra cắt cụt dựa trên chuỗi chưa bị strip dấu câu ở cuối
        truncated = is_truncated(bullet_free)
        
        clean = bullet_free.strip(" .-–—")
        
        # Lọc bỏ thêm nếu sau khi clean vẫn khớp bộ lọc
        clean_no_md = re.sub(r'\*\*|__|\*|_|<b>|</b>', '', clean).strip()
        clean_clean_lower = clean_no_md.lower()
        if not clean or _IGNORE_PATTERNS.match(clean) or _IGNORE_PATTERNS.match(clean_no_md):
            continue
            
        if any(kw in clean_clean_lower for kw in _LEAK_KEYWORDS):
            continue
            
        if is_heading_style(clean):
            continue
            
        # Khử trùng/sửa lỗi hallucination
        clean = clean_hallucinations(clean)
            
        parsed.append((clean, marker, truncated))

    if any_marker:
        filtered_parsed = [p for p in parsed if p[1]]
    else:
        filtered_parsed = parsed

    # Bỏ dòng quá ngắn (thường là tiêu đề/rác); nếu lọc sạch hết thì giữ nguyên
    longish = [p for p in filtered_parsed if len(p[0].split()) >= min_words]
    final_parsed = longish or filtered_parsed

    # Nếu phần tử cuối cùng được sinh ra bị cắt cụt (truncated), loại bỏ nó
    if final_parsed and final_parsed[-1][2]:
        final_parsed.pop()

    final_list = [p[0] for p in final_parsed]

    # Khử trùng lặp gạch đầu dòng (duyệt ngược từ cuối lên đầu để giữ câu bôi đậm xuất hiện sau)
    seen_cores = set()
    deduped = []
    for item in reversed(final_list):
        # Tạo chuỗi core text chuẩn hóa (lowercase, loại bỏ markdown, loại bỏ tất cả khoảng trắng)
        core = re.sub(r'\*\*|__|\*|_|<b>|</b>', '', item)
        core = "".join(core.lower().split())
        if core not in seen_cores:
            seen_cores.add(core)
            deduped.append(item)
    deduped.reverse()
    
    return deduped
