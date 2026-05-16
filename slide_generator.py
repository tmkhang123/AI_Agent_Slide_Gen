from pptx import Presentation
from pptx.util import Inches, Pt

class SlideGenerator:
    def __init__(self):
        self.prs = Presentation()

    def add_title_slide(self, title, subtitle):
        slide_layout = self.prs.slide_layouts[0]
        slide = self.prs.slides.add_slide(slide_layout)
        title_placeholder = slide.shapes.title
        subtitle_placeholder = slide.placeholders[1]
        
        title_placeholder.text = title
        subtitle_placeholder.text = subtitle

    def add_content_slide(self, title, bullet_points):
        slide_layout = self.prs.slide_layouts[1]
        slide = self.prs.slides.add_slide(slide_layout)
        title_placeholder = slide.shapes.title
        title_placeholder.text = title
        
        body_shape = slide.placeholders[1]
        tf = body_shape.text_frame
        tf.word_wrap = True
        
        for point in bullet_points:
            p = tf.add_paragraph()
            p.text = point
            p.level = 0
            # Tự động chỉnh phông chữ nhỏ lại một chút để hiển thị được nhiều nội dung hơn
            p.font.size = Pt(18)

    def save(self, filename="presentation.pptx"):
        self.prs.save(filename)
        return filename
