import requests
import time
from io import BytesIO

_PALETTE = [
    ((30, 39, 97),   (202, 220, 252)),
    ((15, 70, 86),   (93, 202, 165)),
    ((100, 30, 60),  (240, 193, 209)),
    ((42, 67, 23),   (144, 198, 83)),
    ((90, 40, 10),   (239, 159, 39)),
]


def _make_placeholder(query: str, width: int = 1500, height: int = 1125) -> BytesIO:
    """
    Placeholder đơn giản: nền màu gradient + icon nhỏ góc.
    KHÔNG vẽ text to để tránh lộ qua overlay của slide.
    Kích thước mặc định bằng kích thước slide (10"×7.5" @ 150dpi).
    """
    import numpy as np
    from PIL import Image, ImageDraw, ImageFont

    idx = abs(hash(query)) % len(_PALETTE)
    bg, accent = _PALETTE[idx]

    # Nền gradient dọc: màu bg ở trên → phiên bản tối hơn ở dưới
    arr = []
    for row in range(height):
        t   = row / (height - 1)
        r   = int(bg[0] * (1 - t * 0.35))
        g   = int(bg[1] * (1 - t * 0.35))
        b   = int(bg[2] * (1 - t * 0.30))
        arr.append([r, g, b])

    import numpy as _np
    col = _np.array(arr, dtype=_np.uint8)           # (H, 3)
    img_arr = _np.tile(col[:, _np.newaxis, :], (1, width, 1))
    img = Image.fromarray(img_arr, "RGB")
    draw = ImageDraw.Draw(img)

    # Vòng trang trí góc phải dưới (nhỏ, không gây chú ý)
    cx, cy = width - 120, height - 120
    for i in range(5):
        r2 = 50 + i * 35
        draw.ellipse([cx - r2, cy - r2, cx + r2, cy + r2],
                     outline=(*accent, 60), width=2)

    # Icon "image" nhỏ góc trái trên
    ix, iy, sz = 40, 40, 48
    draw.rounded_rectangle([ix, iy, ix + sz, iy + sz],
                             radius=8, fill=(*accent, 120))
    draw.rounded_rectangle([ix + 6, iy + 10, ix + sz - 6, iy + sz - 6],
                             radius=3, fill=(*bg, 255))
    draw.ellipse([ix + 12, iy + 15, ix + 22, iy + 25], fill=(*accent, 200))

    buf = BytesIO()
    img.save(buf, format="JPEG", quality=88, optimize=True)
    buf.seek(0)
    return buf


class ImageFetcher:
    """
    Tìm ảnh từ DuckDuckGo với delay tránh rate-limit.
    Fallback: placeholder gradient kín màu (không text) để hoà hợp với full-bleed layout.
    """
    _HEADERS = {
        "User-Agent": (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/124.0.0.0 Safari/537.36"
        )
    }
    _SKIP_EXT    = (".svg", ".webp", ".bmp", ".tiff", ".ico", ".gif")
    _DELAY       = 2.5   # giây giữa các lần gọi DuckDuckGo

    def __init__(self):
        self.session = requests.Session()
        self.session.headers.update(self._HEADERS)
        self._last = 0.0

    def fetch(self, query: str, timeout: int = 10) -> BytesIO:
        """Luôn trả về BytesIO (ảnh thật hoặc placeholder). Không bao giờ None."""
        if not query or not query.strip():
            return _make_placeholder("background")
        result = self._try_ddg(query, timeout)
        if result is not None:
            return result
        print(f"    [Dự phòng] Tạo placeholder cho: '{query}'")
        return _make_placeholder(query)

    def _throttle(self):
        elapsed = time.time() - self._last
        if elapsed < self._DELAY:
            wait = self._DELAY - elapsed
            print(f"    [⏳] Chờ {wait:.1f}s...")
            time.sleep(wait)
        self._last = time.time()

    def _try_ddg(self, query: str, timeout: int) -> BytesIO | None:
        print(f"    [Ảnh] Đang tìm: '{query}'...")
        self._throttle()
        try:
            try:
                from ddgs import DDGS
            except ImportError:
                from duckduckgo_search import DDGS
            with DDGS() as ddgs:
                results = list(ddgs.images(query, max_results=12,
                                           type_image="photo"))
        except Exception as e:
            print(f"    [!] Tìm kiếm thất bại: {e}")
            return None

        for item in results:
            url = item.get("image", "")
            if not url or not url.startswith("http"):
                continue
            if any(url.lower().endswith(x) for x in self._SKIP_EXT):
                continue
            try:
                resp  = self.session.get(url, timeout=timeout)
                ctype = resp.headers.get("Content-Type", "")
                if (resp.status_code == 200 and "image" in ctype
                        and len(resp.content) > 8000):
                    print(f"    [OK] {len(resp.content) // 1024} KB")
                    return BytesIO(resp.content)
            except Exception:
                continue
        return None
