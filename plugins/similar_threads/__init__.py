from flask import render_template_string

from models import Post, Thread
from services.thread_search import index_thread, search_similar_threads


def index_all_threads():
    """Индексирует все существующие треды (если ещё не проиндексированы)."""
    threads = Thread.query.all()
    for t in threads:
        posts = (
            Post.query.filter_by(thread_id=t.id).order_by(Post.created_at.asc()).all()
        )
        if posts:
            text = " ".join(p.comment or "" for p in posts)
            index_thread(t.id, text)


def init_app(app):
    # Индексируем все старые треды при старте
    with app.app_context():
        index_all_threads()

    # При создании нового поста обновляем индекс треда
    def on_post_created(post, thread, **kwargs):
        posts = (
            Post.query.filter_by(thread_id=thread.id)
            .order_by(Post.created_at.asc())
            .all()
        )
        if posts:
            text = " ".join(p.comment or "" for p in posts)
            index_thread(thread.id, text)

    app.on("posts.after_create", on_post_created)

    # Вывод похожих тредов под тредом
    def show_similar_threads(thread, **kwargs):
        similar = search_similar_threads(thread.id, limit=5)
        if not similar:
            return ""
        return render_template_string(
            """
            <details style="margin-top: 10px;">
                <summary style="cursor: pointer; color: #66ff66;">Похожие треды</summary>
                <ul style="list-style: none; padding-left: 20px;">
                    {% for t in similar %}
                    <li>
                        <a href="/{{ t.board.short_name }}/thread/{{ t.id }}">{{ t.posts.first().subject or 'Без темы' }}</a>
                        <span style="color: #7ab37a; font-size: 0.8rem;">({{ t.bumped_at.strftime('%d.%m.%y %H:%M') }})</span>
                    </li>
                    {% endfor %}
                </ul>
            </details>
        """,
            similar=similar,
        )

    app.on("thread.content_bottom", show_similar_threads)
