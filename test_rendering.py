import pytest

from upt.rendering import render_markdown, safe_link


def test_common_markdown():
    html = render_markdown("# Heading\n\n- first\n- second\n\n**bold** *italic* [site](https://example.com)\n\n"
                           "```python\nprint('<safe>')\n```\n\n| A | B |\n|---|---|\n| 1 | 2 |")
    for tag in ("<h1>", "<ul>", "<li>", "<strong>", "<em>", '<a href="https://example.com">',
                "<pre><code>", "<table>", "<td>"):
        assert tag in html
    assert "&lt;safe&gt;" in html


def test_active_html_and_resources_removed():
    html = render_markdown('<script>alert(1)</script>\n<style>body{display:none}</style>\n'
                           '<iframe src="https://tracker.test"></iframe>\n'
                           '<img src="file:///secret" onerror="steal()" alt="secret">\n'
                           '<a href="javascript:alert(1)" onclick="steal()">bad</a>\n'
                           '<p style="background:url(https://tracker.test)">Visible</p>\n'
                           '![Remote](https://tracker.test/image.png)')
    for forbidden in ("<script", "<iframe", "<img", "javascript:", "onclick", "onerror", "tracker.test",
                      "file:///", "display:none", "alert(1)"):
        assert forbidden not in html
    assert "Image: Remote" in html and "Visible" in html


@pytest.mark.parametrize("link", ["javascript:alert(1)", "file:///etc/passwd", "data:text/html,test",
                                   "//evil.test", "\\\\server\\note.md", "/etc/file.md", "ftp://x",
                                   "https://name:secret@example.com", "%2Fetc/a.md", "a%5Cb.md",
                                   "mailto:", "https://", "a\nb.md"])
def test_unsafe_links(link):
    assert not safe_link(link)


@pytest.mark.parametrize("link", ["https://example.com", "http://example.com/a", "mailto:person@example.com",
                                   "notes/hello.md", "hello%20world.md", "#section"])
def test_supported_links(link):
    assert safe_link(link)


def test_malformed_html_cannot_enable_resources():
    html = render_markdown('<svg><script>hidden</script></svg><p>after</p><IMG SRC="https://bad.test">')
    assert "bad.test" not in html and "<svg" not in html and "<script" not in html
