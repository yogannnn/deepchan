import pytest
from flask import url_for

from models import Board, Post, Thread, db
from services.text import parse_bbcode, process_comment, process_urls


def test_parse_bbcode_bold():
    assert parse_bbcode("[b]text[/b]") == "<strong>text</strong>"


def test_parse_bbcode_italic():
    assert parse_bbcode("[i]text[/i]") == "<em>text</em>"


def test_parse_bbcode_spoiler():
    result = parse_bbcode("[spoiler]hidden[/spoiler]")
    assert '<details class="spoiler">' in result
    assert "hidden" in result


def test_parse_bbcode_code():
    result = parse_bbcode("[code]print(1)[/code]")
    assert "<pre><code>print(1)</code></pre>" in result


def test_process_urls_magnet():
    text = "magnet:?xt=urn:btih:abc123"
    result = process_urls(text)
    assert 'href="magnet:?xt=urn:btih:abc123"' in result


def test_process_urls_i2p():
    text = "http://example.i2p"
    result = process_urls(text)
    assert 'href="http://example.i2p"' in result
    assert "clearnet-warning" not in result


def test_process_urls_onion():
    text = "http://example.onion"
    result = process_urls(text)
    assert 'href="http://example.onion"' in result
    assert "clearnet-warning" not in result


def test_process_urls_clearnet():
    text = "http://example.com"
    result = process_urls(text)
    assert "clearnet-warning" in result


def test_process_comment_quote(app):
    """Цитирование >>номера с существующим постом."""
    with app.app_context():
        board = Board.query.filter_by(short_name="b").first()
        thread = Thread(board_id=board.id)
        db.session.add(thread)
        db.session.flush()
        post = Post(
            thread_id=thread.id,
            name="Аноним",
            subject="Тест",
            comment="Оригинальный комментарий",
        )
        db.session.add(post)
        db.session.commit()

        result = process_comment(f">>{post.id}", board.short_name, thread.id)
        assert "inline-quote" in result
        assert "Оригинальный комментарий" in result


def test_process_comment_escapes_html():
    """HTML-теги экранируются."""
    result = process_comment("<script>alert(1)</script>", "b", 1)
    assert "<script>" not in result
    assert "&lt;script&gt;" in result
