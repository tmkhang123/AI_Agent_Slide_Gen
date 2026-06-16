import os
import requests
import time
from io import BytesIO

_PALETTE = [
    ((30, 39, 97),   (202, 220, 252)),
    ((15, 70, 86),   (93, 202, 165)),
    ((32, 42, 68),   (180, 200, 240)),
    ((42, 67, 23),   (144, 198, 83)),
    ((20, 50, 70),   (150, 190, 220)),
]

_WIKI_SEARCH = "https://en.wikipedia.org/w/api.php"
_WIKI_THUMB  = 800   # px chiều rộng thumbnail


def _make_placeholder(query: str, width: int = 1500, height: int = 1125) -> BytesIO:
    import numpy as _np
    from PIL import Image, ImageDraw

    idx = abs(hash(query)) % len(_PALETTE)
    bg, accent = _PALETTE[idx]

    arr = []
    for row in range(height):
        t = row / (height - 1)
        arr.append([int(bg[0] * (1 - t * 0.35)),
                    int(bg[1] * (1 - t * 0.35)),
                    int(bg[2] * (1 - t * 0.30))])
    col     = _np.array(arr, dtype=_np.uint8)
    img_arr = _np.tile(col[:, _np.newaxis, :], (1, width, 1))
    img     = Image.fromarray(img_arr, "RGB")
    draw    = ImageDraw.Draw(img)

    cx, cy = width - 120, height - 120
    for i in range(5):
        r2 = 50 + i * 35
        draw.ellipse([cx - r2, cy - r2, cx + r2, cy + r2],
                     outline=(*accent, 60), width=2)

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
    Nguồn ảnh theo thứ tự ưu tiên:
      1. Wikipedia REST API  — diagram/infographic kỹ thuật thật sự
      2. DuckDuckGo          — fallback, filter mạnh tránh ảnh người/thể thao
      3. Placeholder         — gradient màu, luôn thành công
    """
    _HEADERS = {
        "User-Agent": (
            "AI-Slides-Maker/1.0 (educational project; "
            "contact: student@university.edu) python-requests"
        )
    }
    _SKIP_EXT     = (".svg", ".bmp", ".tiff", ".ico", ".gif")
    _DDG_DELAY    = 2.5

    # Domain chặn: stock ảnh người, thể thao
    _BLOCKED_DOMAINS = (
        "shutterstock.com", "istockphoto.com", "gettyimages.com",
        "dreamstime.com", "alamy.com", "123rf.com", "depositphotos.com",
        "pond5.com", "bigstockphoto.com",
    )
    # Từ khoá trong URL/title báo hiệu ảnh người/thể thao
    _BLOCKED_TERMS = (
        "athlete", "runner", "sport", "fitness", "workout",
        "portrait", "headshot", "selfie",
    )

    def __init__(self):
        self.session = requests.Session()
        self.session.headers.update(self._HEADERS)
        self._ddg_last   = 0.0
        self._cache_file = "Product/used_image_urls.txt"
        self._used_urls  = set()

        if os.path.exists(self._cache_file):
            try:
                with open(self._cache_file, "r", encoding="utf-8") as f:
                    for line in f:
                        if line.strip():
                            self._used_urls.add(line.strip())
            except Exception:
                pass

    def _save_cache(self, url: str):
        self._used_urls.add(url)
        try:
            os.makedirs(os.path.dirname(self._cache_file), exist_ok=True)
            with open(self._cache_file, "a", encoding="utf-8") as f:
                f.write(url + "\n")
        except Exception:
            pass

    # ── API công khai ────────────────────────────────────────────────────────
    def fetch(self, query: str, timeout: int = 10) -> BytesIO:
        """Luôn trả BytesIO. Thứ tự: Wikipedia → DDG → placeholder."""
        if not query or not query.strip():
            return _make_placeholder("background")

        # 1) Wikipedia
        result = self._try_wikipedia(query, timeout)
        if result is not None:
            return result

        # 2) DuckDuckGo
        result = self._try_ddg(query, timeout)
        if result is not None:
            return result

        # 3) Placeholder
        print(f"    [Dự phòng] Placeholder cho: '{query}'")
        return _make_placeholder(query)

    # ── Nguồn 1: Wikipedia API ───────────────────────────────────────────────
    def _try_wikipedia(self, query: str, timeout: int) -> BytesIO | None:
        """
        Tìm bài Wikipedia liên quan → lấy ảnh chính của bài (thường là diagram).
        Không cần API key. Dùng Wikipedia REST API (miễn phí).
        """
        try:
            # Bước 1: tìm kiếm bài phù hợp nhất
            search_resp = self.session.get(
                _WIKI_SEARCH,
                params={
                    "action": "query",
                    "list":   "search",
                    "srsearch": query,
                    "format": "json",
                    "srlimit": 5,
                },
                timeout=timeout,
            )
            if search_resp.status_code != 200:
                return None
            hits = search_resp.json().get("query", {}).get("search", [])
            if not hits:
                return None

            # Thử từng kết quả cho đến khi lấy được ảnh
            titles = [h["title"] for h in hits]
            for title in titles:
                img = self._wiki_page_image(title, timeout)
                if img is not None:
                    print(f"    [Wikipedia] '{title}' → OK")
                    return img

        except Exception as e:
            print(f"    [Wikipedia] Lỗi: {e}")
        return None

    def _wiki_page_image(self, title: str, timeout: int) -> BytesIO | None:
        """Lấy thumbnail chính của một trang Wikipedia."""
        try:
            resp = self.session.get(
                _WIKI_SEARCH,
                params={
                    "action":      "query",
                    "titles":      title,
                    "prop":        "pageimages",
                    "pithumbsize": _WIKI_THUMB,
                    "format":      "json",
                },
                timeout=timeout,
            )
            if resp.status_code != 200:
                return None
            pages = resp.json().get("query", {}).get("pages", {})
            for page in pages.values():
                thumb = page.get("thumbnail", {})
                url   = thumb.get("source", "")
                if not url:
                    continue
                if url in self._used_urls:
                    continue
                # Bỏ qua nếu thumbnail là ảnh người (thường là portrait nhỏ)
                url_lower = url.lower()
                if any(t in url_lower for t in self._BLOCKED_TERMS):
                    continue
                img_resp = self.session.get(url, timeout=timeout)
                ctype    = img_resp.headers.get("Content-Type", "")
                if (img_resp.status_code == 200
                        and "image" in ctype
                        and len(img_resp.content) > 5000):
                    self._save_cache(url)
                    return BytesIO(img_resp.content)
        except Exception:
            pass
        return None

    # ── Nguồn 2: DuckDuckGo (fallback) ──────────────────────────────────────
    def _ddg_throttle(self):
        elapsed = time.time() - self._ddg_last
        if elapsed < self._DDG_DELAY:
            wait = self._DDG_DELAY - elapsed
            print(f"    [⏳] Chờ DDG {wait:.1f}s...")
            time.sleep(wait)
        self._ddg_last = time.time()

    def _try_ddg(self, query: str, timeout: int) -> BytesIO | None:
        # KHÔNG dùng type_image="photo" — filter đó chặn luôn diagram/infographic
        negatives = (
            "-portrait -face -woman -man -girl -boy "
            "-athlete -runner -sport -race -fitness -workout "
            "-food -hamburger -cartoon -meme -anime -character "
            "-template -mockup -placeholder"
        )
        print(f"    [DDG fallback] Tìm: '{query}' ...")
        self._ddg_throttle()
        try:
            try:
                from ddgs import DDGS
            except ImportError:
                from duckduckgo_search import DDGS
            with DDGS() as ddgs:
                results = list(ddgs.images(
                    f"{query} {negatives}", max_results=20))
        except Exception as e:
            print(f"    [DDG] Lỗi: {e}")
            return None

        for item in results:
            url = item.get("image", "")
            src = item.get("source", "").lower()
            if not url or not url.startswith("http"):
                continue
            url_lower = url.lower()
            if any(d in url_lower or d in src for d in self._BLOCKED_DOMAINS):
                continue
            if any(t in url_lower for t in self._BLOCKED_TERMS):
                continue
            if url in self._used_urls:
                continue
            if any(url_lower.endswith(x) for x in self._SKIP_EXT):
                continue
            try:
                resp  = self.session.get(url, timeout=timeout)
                ctype = resp.headers.get("Content-Type", "")
                if (resp.status_code == 200
                        and "image" in ctype
                        and len(resp.content) > 8000):
                    print(f"    [DDG] OK {len(resp.content) // 1024} KB")
                    self._save_cache(url)
                    return BytesIO(resp.content)
            except Exception:
                continue
        return None
