"""
orchestrator.py — BỘ ĐIỀU PHỐI 3 AGENT
======================================
Đây là "nhạc trưởng" nối 3 agent lại thành một pipeline hoàn chỉnh:

    topic ─► PlannerAgent ─► ContentAgent ─► DesignerAgent ─► file .pptx

Orchestrator KHÔNG chứa logic nghiệp vụ của agent nào — nó chỉ:
    1. Gọi lần lượt 3 agent theo đúng thứ tự.
    2. Lưu các sản phẩm trung gian ra JSON (để debug & tương thích watch mode):
         - <name>_outline.json   (output của Planner)
         - <name>_content.json   (output của Content — ĐÚNG định dạng cũ)
    3. Cho phép "chỉ chạy lại Designer" từ 1 file *_content.json đã chỉnh tay.

Mỗi thành viên vẫn sở hữu & chịu trách nhiệm agent của mình; orchestrator chỉ
là phần ráp nối chung của cả nhóm.
"""

from __future__ import annotations
import os
import json

from schema import Deck, Outline
from agent_planner import PlannerAgent
from agent_content import ContentAgent
from agent_designer import DesignerAgent


def _safe_name(topic: str) -> str:
    return (
        "".join(c for c in topic if c.isalnum() or c in (" ", "_"))
        .rstrip().replace(" ", "_")
    ) or "presentation"


class SlidesMakerOrchestrator:
    def __init__(self, model_name: str = "llama3.1:8b", use_images: bool = True,
                 output_dir: str = "Product"):
        self.output_dir = output_dir
        self.planner = PlannerAgent(model_name=model_name)
        self.content = ContentAgent(model_name=model_name)
        self.designer = DesignerAgent(use_images=use_images)
        os.makedirs(self.output_dir, exist_ok=True)

    # ── Pipeline đầy đủ: từ chủ đề → PPTX ────────────────────────────────────
    def run_from_topic(self, topic: str) -> dict:
        base = _safe_name(topic)

        print("\n=== AGENT 1: PLANNER ===")
        outline = self.planner.plan(topic)
        outline_path = self._save_json(f"{base}_outline.json", outline.to_dict())

        print("\n=== AGENT 2: CONTENT ===")
        deck = self.content.write(outline)
        content_path = self._save_json(f"{base}_content.json", deck.to_dict())

        print("\n=== AGENT 3: DESIGNER ===")
        pptx_path = self.designer.build(deck, self.output_dir, base)

        return {"outline": outline_path, "content": content_path, "pptx": pptx_path}

    # ── Chỉ chạy lại Designer từ file content đã chỉnh tay ────────────────────
    def run_from_content_json(self, json_path: str) -> dict:
        with open(json_path, "r", encoding="utf-8") as f:
            deck = Deck.from_dict(json.load(f))
        base = os.path.basename(json_path).replace("_content.json", "")
        print("\n=== AGENT 3: DESIGNER (rebuild từ JSON) ===")
        pptx_path = self.designer.build(deck, self.output_dir, base)
        return {"content": json_path, "pptx": pptx_path}

    # ── Tiện ích ─────────────────────────────────────────────────────────────
    def _save_json(self, filename: str, data: dict) -> str:
        path = os.path.join(self.output_dir, filename)
        with open(path, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=4)
        print(f"[Orchestrator] Đã lưu: {path}")
        return path


# ── CLI ──────────────────────────────────────────────────────────────────────
if __name__ == "__main__":
    import sys
    orch = SlidesMakerOrchestrator()

    if len(sys.argv) > 1 and sys.argv[1].endswith("_content.json"):
        result = orch.run_from_content_json(sys.argv[1])
    else:
        topic = (sys.argv[1] if len(sys.argv) > 1
                 else input("Nhập chủ đề: ").strip())
        result = orch.run_from_topic(topic)

    print("\n[OK] HOÀN TẤT:")
    for k, v in result.items():
        print(f"   - {k:8s}: {os.path.abspath(v)}")
