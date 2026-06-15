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

GEN_API  = "http://localhost:11434/api/generate"
TAGS_API = "http://localhost:11434/api/tags"


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
    payload = {
        "model": model,
        "prompt": prompt,
        "stream": False,
        "options": {"temperature": temperature, "num_predict": num_predict},
    }
    resp = requests.post(api_url, json=payload, timeout=timeout)
    resp.raise_for_status()
    return (resp.json().get("response") or "").strip()


# ─────────────────────────────────────────────────────────────────────────────
# Phân tích văn bản (khoan dung)
# ─────────────────────────────────────────────────────────────────────────────

_FENCE    = re.compile(r"```[a-zA-Z]*")
_BULLET   = re.compile(r"^\s*(?:\d{1,2}\s*[\.\):]|[-*•▪◦‣·–—])\s*")
_SLIDEPFX = re.compile(r"^\s*slide\s*\d+\s*[:.\-)]*\s*", re.IGNORECASE)
_SEP      = re.compile(r"\s*(?:::|\||–|—|\bimage\s*:)\s*", re.IGNORECASE)


def _clean(text: str) -> str:
    text = _FENCE.sub("", text or "")
    return text.replace("`", "").strip()


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
        rows.append((title, query, had_marker))

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
    parsed = []
    any_marker = False
    for raw in _clean(text).splitlines():
        line = raw.strip()
        if not line:
            continue
        marker = bool(_BULLET.match(line))
        any_marker = any_marker or marker
        clean = _BULLET.sub("", line).strip().strip('"').strip(" .-–—")
        if clean:
            parsed.append((clean, marker))

    if any_marker:
        result = [p for (p, m) in parsed if m]
    else:
        result = [p for (p, _) in parsed]

    # bỏ dòng quá ngắn (thường là tiêu đề/rác); nếu lọc sạch hết thì giữ nguyên
    longish = [p for p in result if len(p.split()) >= min_words]
    return longish or result
