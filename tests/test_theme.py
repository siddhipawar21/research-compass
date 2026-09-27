from core.theme import chat_bubble, inject_theme, source_link, LIGHT, DARK, type_tag


def test_source_link_rejects_javascript_url():
    html = source_link("SRC-001", "javascript:alert(1)")
    assert "href=" not in html
    assert "javascript:" not in html
    assert "<a" not in html
    assert "SRC-001" in html


def test_source_link_escapes_html_in_id():
    html = source_link('<script>alert(1)</script>', "https://publisher.org/x")
    assert "<script>" not in html
    assert "&lt;script&gt;" in html
    assert 'href="https://publisher.org/x"' in html


def test_chat_bubble_escapes_script_text(monkeypatch):
    captured: dict[str, str] = {}

    def fake_markdown(s, unsafe_allow_html=False):
        captured["html"] = s
        captured["unsafe"] = unsafe_allow_html

    monkeypatch.setattr("core.theme.st.markdown", fake_markdown)
    chat_bubble("advocate", '<script>alert("xss")</script>', source_link("SRC-1", "javascript:void(0)"))
    out = captured["html"]
    assert "<script>" not in out
    assert "&lt;script&gt;" in out
    assert "javascript:" not in out
    assert captured["unsafe"] is True
    assert "Supporting position" in out


def test_light_theme_is_default_and_has_tokens(monkeypatch):
    captured: list[str] = []
    monkeypatch.setattr("core.theme.st.markdown", lambda s, **k: captured.append(s))
    monkeypatch.setattr("core.theme.st.session_state", {"rc_theme": "light"})
    inject_theme("light")
    css = captured[0]
    assert LIGHT["bg1"] in css
    assert LIGHT["ink"] in css
    assert LIGHT["brass"] in css
    assert "Demo Mode" not in css
    assert "#0A1029" not in css or LIGHT["bg1"] in css


def test_dark_theme_tokens(monkeypatch):
    captured: list[str] = []
    monkeypatch.setattr("core.theme.st.markdown", lambda s, **k: captured.append(s))
    inject_theme("dark")
    css = captured[0]
    assert DARK["bg1"] in css
    assert DARK["ink"] in css
    assert LIGHT["bg1"] not in css


def test_type_tag_is_text_not_icon_only():
    html = type_tag("paper")
    assert "Research paper" in html
    assert type_tag("github").find("GitHub") >= 0
