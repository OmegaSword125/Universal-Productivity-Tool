"""Markdown -> constrained rich text. No web engine, scripts, images, or CSS from notes."""
from html import escape
from html.parser import HTMLParser
from urllib.parse import unquote, urlsplit

import markdown

ALLOWED = {"p", "br", "hr", "h1", "h2", "h3", "h4", "h5", "h6", "strong", "em",
           "b", "i", "s", "del", "blockquote", "pre", "code", "ul", "ol", "li", "a",
           "table", "thead", "tbody", "tr", "th", "td", "dl", "dt", "dd", "sup", "sub"}
VOID = {"br", "hr"}
DROP = {"script", "style", "iframe", "object", "svg", "math", "template"}


def safe_link(value: str) -> bool:
    if not value or any(ord(c) < 32 for c in value) or "\\" in value:
        return False
    try:
        parsed = urlsplit(value)
        if parsed.scheme:
            if parsed.scheme.lower() in {"http", "https"}:
                return bool(parsed.netloc) and not parsed.username and not parsed.password
            return parsed.scheme.lower() == "mailto" and bool(parsed.path)
        # Only fragments or relative Markdown links; never file:// or UNC paths.
        if parsed.netloc or parsed.path.startswith("/"):
            return False
        path = unquote(parsed.path)
        if "\\" in path or ":" in path or path.startswith("/"):
            return False
        return (not path and bool(parsed.fragment)) or path.lower().endswith(".md")
    except ValueError:
        return False


class Sanitizer(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.parts: list[str] = []
        self.blocked: list[str] = []

    def handle_starttag(self, tag, attrs):
        if self.blocked:
            if tag in DROP:
                self.blocked.append(tag)
            return
        if tag in DROP:
            self.blocked.append(tag)
            return
        attrs = dict(attrs)
        if tag == "img":
            self.parts.append(escape(f"[Image: {attrs.get('alt', 'image')} — not loaded]"))
        elif tag in ALLOWED:
            extra = ""
            if tag == "a" and safe_link(attrs.get("href", "")):
                extra = f' href="{escape(attrs["href"], quote=True)}"'
            elif tag in {"th", "td"} and attrs.get("align") in {"left", "right", "center"}:
                extra = f' align="{attrs["align"]}"'
            self.parts.append(f"<{tag}{extra}>")

    def handle_startendtag(self, tag, attrs):
        self.handle_starttag(tag, attrs)
        if tag not in VOID and tag != "img":
            self.handle_endtag(tag)

    def handle_endtag(self, tag):
        if self.blocked:
            if tag == self.blocked[-1]:
                self.blocked.pop()
            return
        if tag in ALLOWED and tag not in VOID:
            self.parts.append(f"</{tag}>")

    def handle_data(self, data):
        if not self.blocked:
            self.parts.append(escape(data))


STYLE = """
body { color: #dee1e9; background: #21232b; font-family: 'Segoe UI', sans-serif; font-size: 15px; }
h1 { font-size: 28px; color: #f3f0ff; margin-top: 20px; }
h2 { font-size: 22px; color: #f3f0ff; margin-top: 18px; }
h3 { font-size: 18px; color: #eeeafa; }
p, li { line-height: 150%; }
a { color: #b9a8ff; }
pre { background: #181a21; color: #dfddf4; padding: 14px; white-space: pre-wrap; }
code { font-family: Consolas, monospace; color: #d5c7ff; }
blockquote { color: #b6bdcc; margin-left: 18px; }
table { border-collapse: collapse; margin-top: 12px; }
th, td { border: 1px solid #505565; padding: 8px; }
th { background: #303440; }
"""


def render_markdown(text: str) -> str:
    raw = markdown.markdown(text, extensions=["fenced_code", "tables", "sane_lists"],
                            output_format="html")
    clean = Sanitizer()
    clean.feed(raw)
    clean.close()
    return f'<!DOCTYPE html><html><head><style>{STYLE}</style></head><body>' + "".join(clean.parts) + "</body></html>"
