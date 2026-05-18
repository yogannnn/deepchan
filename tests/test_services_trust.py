import os
from datetime import datetime, timedelta, timezone

import pytest

from app import create_app
from models import Ban, Board, Post, Report, Thread
from models import db as _db
from services.trust import get_trust_score


@pytest.fixture(scope="function")
def app_with_trust():
    """Создаёт тестовое приложение с таблицами и вспомогательной доской."""
    os.environ["DEEPCHAN_TESTING"] = "1"
    app = create_app()
    app.config["TESTING"] = True
    app.config["SERVER_NAME"] = "localhost"
    with app.app_context():
        _db.create_all()
        board = Board(short_name="b", name="test")
        _db.session.add(board)
        _db.session.commit()
        app.board_id = board.id
    yield app
    with app.app_context():
        _db.drop_all()
    os.environ.pop("DEEPCHAN_TESTING", None)


def test_no_posts_score_50(app_with_trust):
    """Если нет ни одного поста – trust_score = 50."""
    with app_with_trust.app_context():
        score = get_trust_score("unknown_user")
        assert score == 50


def test_posts_increase_score(app_with_trust):
    """Посты повышают trust_score."""
    identity = "poster1"
    with app_with_trust.app_context():
        board = _db.session.get(Board, app_with_trust.board_id)
        for i in range(15):
            thread = Thread(board=board)
            _db.session.add(thread)
            _db.session.flush()
            post = Post(
                thread_id=thread.id,
                name="test",
                comment=f"post {i}",
                identity_hash=identity,
            )
            _db.session.add(post)
        _db.session.commit()
        score = get_trust_score(identity)
        assert score > 50


def test_reports_decrease_score(app_with_trust):
    """Жалобы снижают trust_score."""
    identity = "reported_user"
    with app_with_trust.app_context():
        board = _db.session.get(Board, app_with_trust.board_id)
        thread = Thread(board=board)
        _db.session.add(thread)
        _db.session.flush()
        post = Post(
            thread_id=thread.id, name="test", comment="test", identity_hash=identity
        )
        _db.session.add(post)
        _db.session.flush()

        # Две жалобы на этот пост
        r1 = Report(post_id=post.id, reason="test", identity_hash=identity)
        r2 = Report(post_id=post.id, reason="test", identity_hash=identity)
        _db.session.add_all([r1, r2])
        _db.session.commit()

        score = get_trust_score(identity)
        assert score < 50


def test_bans_decrease_score(app_with_trust):
    """Активные баны резко снижают trust_score."""
    identity = "banned_user"
    with app_with_trust.app_context():
        board = _db.session.get(Board, app_with_trust.board_id)
        thread = Thread(board=board)
        _db.session.add(thread)
        _db.session.flush()
        post = Post(
            thread_id=thread.id, name="test", comment="test", identity_hash=identity
        )
        _db.session.add(post)
        _db.session.flush()

        ban = Ban(
            identity_hash=identity, ip_pattern="0.0.0.0", reason="test", active=True
        )
        _db.session.add(ban)
        _db.session.commit()

        score = get_trust_score(identity)
        assert score < 50


def test_age_increases_score(app_with_trust):
    """Возраст identity (дата первого поста) повышает trust_score."""
    identity = "old_user"
    with app_with_trust.app_context():
        board = _db.session.get(Board, app_with_trust.board_id)

        # Старый пост (30 дней назад)
        thread1 = Thread(board=board)
        _db.session.add(thread1)
        _db.session.flush()
        post1 = Post(
            thread_id=thread1.id,
            name="test",
            comment="old",
            identity_hash=identity,
            created_at=datetime.now(timezone.utc) - timedelta(days=30),
        )
        _db.session.add(post1)

        # Свежий пост
        thread2 = Thread(board=board)
        _db.session.add(thread2)
        _db.session.flush()
        post2 = Post(
            thread_id=thread2.id,
            name="test",
            comment="new",
            identity_hash=identity,
            created_at=datetime.now(timezone.utc) - timedelta(days=1),
        )
        _db.session.add(post2)
        _db.session.commit()

        score = get_trust_score(identity)
        assert score > 55  # базовые 50 + бонус за возраст
