import streamlit as st
import os
import json
import re
from ai_engine import AIEngine
from slide_generator import SlideGenerator
import time

def get_next_version(base_filename):
    version = 1
    pattern = re.compile(rf"^{re.escape(base_filename)}_ver_(\d+)\.pptx$")
    if os.path.exists(f"{base_filename}.pptx"):
        for file in os.listdir("."):
            match = pattern.match(file)
            if match:
                v = int(match.group(1))
                if v >= version:
                    version = v + 1
        return f"_ver_{version}"
    return ""

def generate_slides(topic):
    ai = AIEngine()
    gen = SlideGenerator()
    
    # Tạo thư mục Product nếu chưa có
    product_dir = "Product"
    if not os.path.exists(product_dir):
        os.makedirs(product_dir)
    
    with st.status("Đang khởi tạo AI Agent...", expanded=True) as status:
        st.write(f"[*] BƯỚC 1: Đang dùng AI (Ollama) để sinh nội dung cho: {topic}")
        slides_data = ai.generate_content(topic)
        
        safe_name = "".join([c for c in topic if c.isalnum() or c in (' ', '_')]).rstrip().replace(' ', '_')
        json_filename = os.path.join(product_dir, f"{safe_name}_content.json")
        
        with open(json_filename, "w", encoding="utf-8") as f:
            json.dump(slides_data, f, ensure_ascii=False, indent=4)
        
        st.write(f"[*] BƯỚC 2: Đang tạo PowerPoint...")
        gen.add_title_slide(slides_data['title'], slides_data['subtitle'])
        
        for idx, slide_data in enumerate(slides_data['slides'], 1):
            st.write(f"    > Đang tạo slide {idx}: {slide_data['title']}")
            gen.add_content_slide(slide_data['title'], slide_data['points'])

        # Kiểm tra phiên bản trong thư mục Product
        version = 1
        base_pptx = safe_name
        pattern = re.compile(rf"^{re.escape(base_pptx)}_ver_(\d+)\.pptx$")
        
        if os.path.exists(os.path.join(product_dir, f"{base_pptx}.pptx")):
            for file in os.listdir(product_dir):
                match = pattern.match(file)
                if match:
                    v = int(match.group(1))
                    if v >= version:
                        version = v + 1
            ver_suffix = f"_ver_{version}"
        else:
            ver_suffix = ""
            
        pptx_filename = os.path.join(product_dir, f"{safe_name}{ver_suffix}.pptx")
        gen.save(pptx_filename)
        
        status.update(label="Hoàn tất!", state="complete", expanded=False)
        
    return json_filename, pptx_filename

st.set_page_config(page_title="AI Slides Maker", page_icon="📊")

st.title("📊 AI Slides Maker Agent")
st.markdown("Tạo bài thuyết trình chuyên nghiệp tự động bằng AI (Ollama Local).")

with st.sidebar:
    st.header("Cấu hình")
    model = st.text_input("Ollama Model", value="llama3.1:8b")
    st.info("Đảm bảo Ollama đang chạy trên máy của bạn.")

topic = st.text_input("Nhập chủ đề bạn muốn tạo slide:", placeholder="Ví dụ: Lợi ích của AI trong giáo dục")

if st.button("Tạo Slide ngay", type="primary"):
    if topic:
        try:
            json_file, pptx_file = generate_slides(topic)
            
            st.success("🎉 Đã tạo slide thành công!")
            
            col1, col2 = st.columns(2)
            with col1:
                with open(pptx_file, "rb") as f:
                    st.download_button(
                        label="📥 Tải xuống file PPTX",
                        data=f,
                        file_name=os.path.basename(pptx_file),
                        mime="application/vnd.openxmlformats-officedocument.presentationml.presentation"
                    )
            with col2:
                with open(json_file, "rb") as f:
                    st.download_button(
                        label="📄 Tải nội dung JSON",
                        data=f,
                        file_name=os.path.basename(json_file),
                        mime="application/json"
                    )
            
            st.info(f"File đã được lưu tại thư mục: `{os.path.abspath('.')}`")
            
        except Exception as e:
            st.error(f"Đã xảy ra lỗi: {e}")
    else:
        st.warning("Vui lòng nhập chủ đề!")

st.divider()
st.caption("Phát triển bởi AI Agent - GitHub Copilot")
