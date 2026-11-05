from camofox_extract import accessibility_tree_to_markdown as to_md
from camofox_extract.extractor import _extract_title


def test_heading_and_paragraph():
    snap = '- heading "Example Domain" [level=1]\n- paragraph: Hello world'
    assert to_md(snap) == "# Example Domain\n\nHello world"


def test_link_with_url():
    snap = '- link "Learn more" [e1]:\n  - /url: https://iana.org/domains/example'
    assert to_md(snap) == "[Learn more](https://iana.org/domains/example)"


def test_link_without_url_does_not_steal_sibling_url_or_drop_content():
    snap = (
        "- list:\n"
        "  - listitem:\n"
        '    - link "No url" [e1]\n'
        "  - listitem:\n"
        "    - paragraph: Keep me\n"
        "  - listitem:\n"
        '    - link "Real" [e2]:\n'
        "      - /url: https://real.example\n"
    )
    out = to_md(snap)
    assert "[No url](" not in out
    assert "No url" in out
    assert "Keep me" in out
    assert "[Real](https://real.example)" in out


def test_text_ending_with_colon_is_kept():
    assert to_md("- text: Note:") == "Note:"


def test_image():
    snap = '- img "Logo":\n  - /url: https://x.example/logo.png'
    assert to_md(snap) == "![Logo](https://x.example/logo.png)"


def test_empty():
    assert to_md("") == ""


def test_extract_title():
    assert _extract_title('- banner:\n  - heading "Hi" [level=1]') == "Hi"
    assert _extract_title("- paragraph: none") == ""
