import time
import requests
from bs4 import BeautifulSoup


# ============================================================
# CLASS — 原封不動從 wikipedia_extractor.py 搬過來（只改 error 處理）
# ============================================================
class WikipediaExtractor:
    def __init__(self):
        # CONSTRAINT：必須喺最頂初始化，UI 會讀 .error
        self.error = None
        self.soup = None
        self.title = ""
        self.url = ""

    def fetch(self, topic):
        safe_topic = (topic or "").strip().replace(" ", "_")
        if not safe_topic:
            self.error = "Topic is empty. Please type a topic."
            return

        self.url = "https://en.wikipedia.org/wiki/" + safe_topic
        headers = {"User-Agent": "ISOM3400StudentBot/1.0"}

        try:
            response = requests.get(self.url, headers=headers, timeout=10)
            response.raise_for_status()
        except requests.exceptions.HTTPError:
            self.error = "Article not found (HTTP error). Please check the topic name."
            return
        except requests.exceptions.RequestException as e:
            self.error = "Network error: " + str(e)
            return

        self.soup = BeautifulSoup(response.text, "html.parser")
        h1 = self.soup.find("h1")
        if h1 is None:
            self.error = "Could not find the article title."
            return
        self.title = h1.get_text(strip=True)

    # ---------- 以下同你 console 版一模一樣 ----------
    def _heading_text(self, h2):
        span = h2.find("span", class_="mw-headline")
        if span is not None:
            return span.get_text(strip=True)
        return h2.get_text(strip=True)

    def _content_root(self):
        root = self.soup.find("div", id="mw-content-text")
        if root is None:
            root = self.soup
        return root

    def list_top_sections(self):
        root = self._content_root()
        sections = []
        for h2 in root.find_all("h2"):
            title = self._heading_text(h2)
            if title and title not in (
                "Contents", "Sources", "References", "External links",
                "See also", "Notes", "Further reading", "Bibliography",
            ):
                sections.append(title)
        return sections

    def extract_section(self, section_title):
        root = self._content_root()
        target_h2 = None
        for h2 in root.find_all("h2"):
            if self._heading_text(h2) == section_title:
                target_h2 = h2
                break
        if target_h2 is None:
            return ""

        start = target_h2
        parent = target_h2.parent
        if parent is not None and parent.name == "div":
            parent_classes = parent.attrs.get("class", [])
            if "mw-heading" in parent_classes or "mw-heading2" in parent_classes:
                start = parent

        parts = ["\n=== " + section_title + " ===\n"]
        current = start.find_next_sibling()

        while current is not None:
            if current.name == "div":
                div_classes = current.attrs.get("class", [])
                is_heading_wrapper = any(c.startswith("mw-heading") for c in div_classes)
                if is_heading_wrapper:
                    if current.find("h2") is not None:
                        break
                    inner = current.find("h3") or current.find("h4")
                    if inner is not None:
                        sub_title = inner.get_text(strip=True)
                        if sub_title:
                            parts.append("  " + sub_title + "\n")
                    current = current.find_next_sibling()
                    continue

            if current.name == "h2":
                break
            elif current.name in ("h3", "h4"):
                sub_title = current.get_text(strip=True)
                if sub_title:
                    parts.append("  " + sub_title + "\n")
            elif current.name == "p":
                for sup in current.find_all("sup"):
                    sup.decompose()
                text = current.get_text(strip=True)
                if text:
                    parts.append(text + "\n")
            elif current.name in ("ul", "ol"):
                for li in current.find_all("li"):
                    for sup in li.find_all("sup"):
                        sup.decompose()
                    item_text = li.get_text(strip=True)
                    if item_text:
                        parts.append("  - " + item_text + "\n")
            elif current.name == "table":
                table_classes = current.attrs.get("class", [])
                if "wikitable" in table_classes or "infobox" in table_classes:
                    parts.append("[TABLE]\n")
                    for row in current.find_all("tr"):
                        cells = row.find_all("td") + row.find_all("th")
                        cell_texts = []
                        for cell in cells:
                            for sup in cell.find_all("sup"):
                                sup.decompose()
                            cell_texts.append(cell.get_text(strip=True))
                        if cell_texts:
                            parts.append(" | ".join(cell_texts) + "\n")
                    parts.append("[/TABLE]\n")

            current = current.find_next_sibling()

        result = ""
        for part in parts:
            result = result + part
        return result


# ============================================================
# HELPERS（三個 functions 齊晒！）
# ============================================================
def safe_filename(title):
    """Article title → filesystem-safe base name（唔包 .txt）。"""
    base = ""
    for c in (title or ""):
        # 只准 a-z, A-Z, 0-9，其他一律變做底線
        if c.isascii() and c.isalnum():
            base = base + c
        elif c in (" ", "_", "-"):
            base = base + "_"
    
    base = base.rstrip("_")
    base = base[:50]  # 防止太長
    
    return base or "wikipedia_article"


def numbered_filename(base, existing):
    """若 base.txt 已用過，加 _v2, _v3... 避開撞名（唔用括號，防 Browser 炒車）。"""
    candidate = base + ".txt"
    if candidate not in existing:
        return candidate
    n = 2
    while True:
        candidate = f"{base}_v{n}.txt"  # 改用 _v2 代替 (2)
        if candidate not in existing:
            return candidate
        n += 1


def format_txt(article_title, article_url, sections):
    """唔寫檔，直接 return 字串俾 st.download_button 用。"""
    content = "Source URL: " + (article_url or "") + "\n"
    content = content + "Extraction timestamp: " + time.strftime("%Y-%m-%d %H:%M:%S") + "\n"
    content = content + "Licence: CC BY-SA 4.0\n"
    content = content + "=" * 60 + "\n\n"
    for section in (sections or []):
        content = content + section + "\n"
    return content