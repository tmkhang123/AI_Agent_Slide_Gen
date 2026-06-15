"""
gui_app.py — Giao diện Streamlit (kiến trúc 3 AGENT)
====================================================
GUI gọi lần lượt 3 agent độc lập và hiển thị tiến trình TỪNG agent ngay trên
giao diện nhờ callback on_progress:

    topic ─► PlannerAgent ─► ContentAgent ─► DesignerAgent ─► .pptx

Mỗi agent vẫn do một thành viên sở hữu; GUI chỉ là lớp trình bày + ráp nối.
Sản phẩm trung gian (*_outline.json, *_content.json) được lưu để tương thích
với watcher.py (watch mode).
"""

import streamlit as st
import os
import json

import llm
from schema import Outline, Deck
from agent_planner import PlannerAgent
from agent_content import ContentAgent
from agent_designer import DesignerAgent


def safe_name(topic: str) -> str:
    return (
        "".join(c for c in topic if c.isalnum() or c in (" ", "_"))
        .rstrip().replace(" ", "_")
    ) or "presentation"


def generate_slides(topic: str, model_name: str, use_images: bool):
    product_dir = "Product"
    os.makedirs(product_dir, exist_ok=True)
    base = safe_name(topic)

    with st.status("Đang khởi tạo AI Agent...", expanded=True) as status:
        # callback đẩy tiến trình của agent ra giao diện
        def ui(msg):
            st.write(f"&nbsp;&nbsp;&nbsp;{msg}", unsafe_allow_html=True)

        # ── AGENT 1 · PLANNER ────────────────────────────────────────────────
        st.write(f"**Agent 1 · Planner** — lập dàn ý bằng `{model_name}`")
        planner = PlannerAgent(model_name=model_name)
        outline: Outline = planner.plan(topic, on_progress=ui)

        outline_path = os.path.join(product_dir, f"{base}_outline.json")
        with open(outline_path, "w", encoding="utf-8") as f:
            json.dump(outline.to_dict(), f, ensure_ascii=False, indent=4)
        st.write(f"✅ Dàn ý xong — {len(outline.briefs)} slide")

        # ── AGENT 2 · CONTENT ────────────────────────────────────────────────
        st.write("**Agent 2 · Content** — sinh nội dung chi tiết")
        content = ContentAgent(model_name=model_name)
        deck: Deck = content.write(outline, on_progress=ui)

        # Lưu đúng định dạng JSON cũ (tương thích watch mode)
        json_path = os.path.join(product_dir, f"{base}_content.json")
        with open(json_path, "w", encoding="utf-8") as f:
            json.dump(deck.to_dict(), f, ensure_ascii=False, indent=4)
        st.write(f"✅ Nội dung xong — {len(deck.slides)} slide")

        # ── AGENT 3 · DESIGNER ───────────────────────────────────────────────
        mode = "kèm ảnh minh họa" if use_images else "chỉ văn bản"
        st.write(f"**Agent 3 · Designer** — dựng PowerPoint ({mode})")
        designer = DesignerAgent(use_images=use_images)
        pptx_path = designer.build(deck, product_dir, base, on_progress=ui)

        status.update(label="✅ Hoàn tất!", state="complete", expanded=False)

    return json_path, pptx_path


# ── Giao diện ───────────────────────────────────────────────────────────────

st.set_page_config(page_title="AI Slides Maker", page_icon="📊", layout="centered")
st.title("📊 AI Slides Maker Agent")
st.markdown(
    "Tạo bài thuyết trình chuyên nghiệp **tự động** bằng **3 AI Agent** "
    "phối hợp: *Planner → Content → Designer*."
)

with st.sidebar:
    st.header("⚙️ Cấu hình")
    model = st.text_input("Ollama Model", value="llama3.1:8b")
    use_images = st.toggle("🖼️ Tự động thêm ảnh minh họa", value=True)
    if use_images:
        st.info("Hệ thống tự tìm ảnh từ internet cho mỗi slide. Cần kết nối mạng.")
    else:
        st.warning("Chế độ chỉ văn bản — slide sẽ không có ảnh.")
    st.divider()
    st.caption("Kiến trúc 3 agent · Đảm bảo Ollama đang chạy trên máy của bạn.")
    st.caption("Agent 1 Planner · Agent 2 Content · Agent 3 Designer")

    if st.button("🔌 Kiểm tra Ollama", use_container_width=True):
        ok, msg = llm.check_ollama(model)
        if ok:
            st.success(f"Ollama OK — model `{model}` sẵn sàng.")
        else:
            st.error(msg)

topic = st.text_input(
    "Nhập chủ đề bạn muốn tạo slide:",
    placeholder="Ví dụ: Lợi ích của AI trong giáo dục",
)

if st.button("🚀 Tạo Slide ngay", type="primary", use_container_width=True):
    if topic.strip():
        try:
            json_file, pptx_file = generate_slides(topic.strip(), model, use_images)
            st.success("🎉 Slide đã được tạo thành công!")
            col1, col2 = st.columns(2)
            with col1:
                with open(pptx_file, "rb") as f:
                    st.download_button(
                        label="📥 Tải xuống PPTX", data=f,
                        file_name=os.path.basename(pptx_file),
                        mime="application/vnd.openxmlformats-officedocument."
                             "presentationml.presentation",
                        use_container_width=True,
                    )
            with col2:
                with open(json_file, "rb") as f:
                    st.download_button(
                        label="📄 Tải nội dung JSON", data=f,
                        file_name=os.path.basename(json_file),
                        mime="application/json", use_container_width=True,
                    )
            st.info(f"📁 File đã lưu tại: `{os.path.abspath('.')}/Product/`")
        except Exception as e:
            st.error(f"❌ Đã xảy ra lỗi: {e}")
    else:
        st.warning("⚠️ Vui lòng nhập chủ đề!")

st.divider()
st.caption("Phát triển bởi nhóm 3 thành viên · 3 agent độc lập · ảnh tự động qua DuckDuckGo")
