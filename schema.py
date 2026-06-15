"""
schema.py — HỢP ĐỒNG DỮ LIỆU CHUNG GIỮA 3 AGENT
================================================
File này định nghĩa "ngôn ngữ chung" mà 3 agent dùng để trao đổi với nhau.
Nhờ có schema rõ ràng, mỗi thành viên có thể phát triển & test agent của mình
độc lập, miễn là tuân thủ đúng input/output đã quy ước ở đây.

LUỒNG DỮ LIỆU:

    topic (str)
        │
        ▼
    PlannerAgent  ──►  Outline      (dàn ý: tiêu đề + danh sách SlideBrief)
        │
        ▼
    ContentAgent  ──►  Deck         (nội dung đầy đủ: danh sách Slide)
        │
        ▼
    DesignerAgent ──►  file .pptx

Deck.to_dict() trả về ĐÚNG cấu trúc JSON cũ:
    {"title","subtitle","slides":[{"title","points","image_query"}]}
=> tương thích ngược với watcher.py / main.py / các file *_content.json cũ.
"""

from __future__ import annotations
from dataclasses import dataclass, field, asdict
from typing import List


# ─────────────────────────────────────────────────────────────────────────────
# OUTPUT của Agent 1 (Planner)
# ─────────────────────────────────────────────────────────────────────────────

@dataclass
class SlideBrief:
    """Mô tả ngắn 1 slide do Planner quyết định (CHƯA có nội dung chi tiết)."""
    title: str                      # Tiêu đề slide (tiếng Việt)
    role: str = "content"           # Vai trò: intro/analysis/application/challenge/conclusion...
    focus: str = ""                 # Gợi ý ngắn cho ContentAgent biết slide này cần nói gì
    image_query: str = "concept"    # Từ khoá TIẾNG ANH để tìm ảnh (3-6 từ)


@dataclass
class Outline:
    """Dàn ý tổng thể của bài thuyết trình."""
    title: str
    subtitle: str
    briefs: List[SlideBrief] = field(default_factory=list)

    # --- chuyển đổi JSON (để lưu / debug) ---
    def to_dict(self) -> dict:
        return {
            "title": self.title,
            "subtitle": self.subtitle,
            "briefs": [asdict(b) for b in self.briefs],
        }

    @staticmethod
    def from_dict(d: dict) -> "Outline":
        return Outline(
            title=d.get("title", "Bài thuyết trình"),
            subtitle=d.get("subtitle", ""),
            briefs=[
                SlideBrief(
                    title=b.get("title", "Slide"),
                    role=b.get("role", "content"),
                    focus=b.get("focus", ""),
                    image_query=b.get("image_query", "concept"),
                )
                for b in d.get("briefs", [])
            ],
        )


# ─────────────────────────────────────────────────────────────────────────────
# OUTPUT của Agent 2 (Content)
# ─────────────────────────────────────────────────────────────────────────────

@dataclass
class Slide:
    """1 slide đã có nội dung đầy đủ."""
    title: str
    points: List[str] = field(default_factory=list)
    image_query: str = "concept"


@dataclass
class Deck:
    """Toàn bộ bài thuyết trình đã sẵn sàng để dựng PPTX."""
    title: str
    subtitle: str
    slides: List[Slide] = field(default_factory=list)

    # --- chuyển đổi sang/from JSON tương thích NGƯỢC với hệ thống cũ ---
    def to_dict(self) -> dict:
        return {
            "title": self.title,
            "subtitle": self.subtitle,
            "slides": [
                {"title": s.title, "points": s.points, "image_query": s.image_query}
                for s in self.slides
            ],
        }

    @staticmethod
    def from_dict(d: dict) -> "Deck":
        return Deck(
            title=d.get("title", "Bài thuyết trình"),
            subtitle=d.get("subtitle", ""),
            slides=[
                Slide(
                    title=s.get("title", "Slide"),
                    points=s.get("points", []),
                    image_query=s.get("image_query", "concept"),
                )
                for s in d.get("slides", [])
            ],
        )
