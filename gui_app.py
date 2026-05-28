import streamlit as st
import os
import json
import re
from ai_engine import AIEngine
from slide_generator import SlideGenerator
from image_fetcher import ImageFetcher


def get_next_version_suffix(product_dir: str, base_name: str) -> str:
    if not os.path.exists(os.path.join(product_dir, f"{base_name}.pptx")):
        return ""
    version = 1
    pattern = re.compile(rf"^{re.escape(base_name)}_ver_(\d+)\.pptx$")
    for fname in os.listdir(product_dir):
        m = pattern.match(fname)
        if m:
            v = int(m.group(1))
            version = max(version, v + 1)
    return f"_ver_{version}"


def generate_slides(topic: str, model_name: str, use_images: bool):
    product_dir = "Product"
    os.makedirs(product_dir, exist_ok=True)

    with st.status("Đang khởi tạo AI Agent...", expanded=True) as status:

        # BƯỚC 1: Sinh nội dung
        st.write(f"**Bước 1** · Đang dùng AI ({model_name}) để sinh nội dung...")
        ai = AIEngine(model_name=model_name)
        slides_data = ai.generate_content(topic)
        safe_name = (
            "".join(c for c in topic if c.isalnum() or c in (" ", "_"))
            .rstrip().replace(" ", "_")
        )
        json_path = os.path.join(product_dir, f"{safe_name}_content.json")
        with open(json_path, "w", encoding="utf-8") as f:
            json.dump(slides_data, f, ensure_ascii=False, indent=4)
        st.write(f"✅ Đã sinh xong nội dung — {len(slides_data['slides'])} slides")

        # BƯỚC 2: Tìm ảnh
        title_img    = None
        image_streams = {}

        if use_images:
            st.write("**Bước 2** · Đang tìm ảnh minh họa...")
            fetcher = ImageFetcher()

            # Ảnh bìa (title slide)
            title_query = slides_data.get("title", "")
            cover_query = title_query if title_query.isascii() else "technology innovation concept"
            st.write(f"   🖼️ Ảnh bìa: `{cover_query}`")
            title_img = fetcher.fetch(cover_query)
            st.write("   ✅ Đã tải ảnh bìa")

            # Ảnh từng slide nội dung
            for i, slide_data in enumerate(slides_data["slides"]):
                query = slide_data.get("image_query", "")
                if query:
                    st.write(f"   🔍 Slide {i+1}: `{query}`")
                    stream = fetcher.fetch(query)
                    image_streams[i] = stream
                    st.write(f"   ✅ Slide {i+1} xong")
        else:
            st.write("**Bước 2** · Bỏ qua tìm ảnh (đã tắt)")

        # BƯỚC 3: Tạo PPTX
        st.write("**Bước 3** · Đang dựng file PowerPoint...")
        sg = SlideGenerator()
        sg.add_title_slide(slides_data["title"], slides_data["subtitle"], title_img)

        for idx, slide_data in enumerate(slides_data["slides"]):
            st.write(f"   📄 Slide {idx+1}: {slide_data['title']}")
            sg.add_content_slide(
                title         = slide_data["title"],
                bullet_points = slide_data["points"],
                image_stream  = image_streams.get(idx),
            )

        ver_suffix = get_next_version_suffix(product_dir, safe_name)
        pptx_path  = os.path.join(product_dir, f"{safe_name}{ver_suffix}.pptx")
        sg.save(pptx_path)
        status.update(label="✅ Hoàn tất!", state="complete", expanded=False)

    return json_path, pptx_path


# ── Giao diện ───────────────────────────────────────────────────────────────

st.set_page_config(page_title="AI Slides Maker", page_icon="📊", layout="centered")
st.title("📊 AI Slides Maker Agent")
st.markdown("Tạo bài thuyết trình chuyên nghiệp **tự động** bằng AI + hình ảnh minh họa.")

with st.sidebar:
    st.header("⚙️ Cấu hình")
    model = st.text_input("Ollama Model", value="llama3.1:8b")
    use_images = st.toggle("🖼️ Tự động thêm ảnh minh họa", value=True)
    if use_images:
        st.info("Hệ thống tự tìm ảnh từ internet cho mỗi slide. Cần kết nối mạng.")
    else:
        st.warning("Chế độ chỉ văn bản — slide sẽ không có ảnh.")
    st.divider()
    st.caption("Đảm bảo Ollama đang chạy trên máy của bạn.")

topic = st.text_input(
    "Nhập chủ đề bạn muốn tạo slide:",
    placeholder="Ví dụ: Lợi ích của AI trong giáo dục"
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
                        mime="application/vnd.openxmlformats-officedocument.presentationml.presentation",
                        use_container_width=True
                    )
            with col2:
                with open(json_file, "rb") as f:
                    st.download_button(
                        label="📄 Tải nội dung JSON", data=f,
                        file_name=os.path.basename(json_file),
                        mime="application/json", use_container_width=True
                    )
            st.info(f"📁 File đã lưu tại: `{os.path.abspath('.')}/Product/`")
        except Exception as e:
            st.error(f"❌ Đã xảy ra lỗi: {e}")
    else:
        st.warning("⚠️ Vui lòng nhập chủ đề!")

st.divider()
st.caption("Phát triển bởi AI Agent · Hỗ trợ hình ảnh tự động qua DuckDuckGo")
