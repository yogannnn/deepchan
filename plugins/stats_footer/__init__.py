from core.i18n import t
from models import Board, Post, PostFile, Thread


def init_app(app):
    def on_footer_render(**kwargs):
        try:
            boards = Board.query.count()
            threads = Thread.query.count()
            posts = Post.query.count()
            files = PostFile.query.count()

            line = t(
                "stats.footer_line",
                boards=boards,
                boards_word=t("stats.total_boards"),
                threads=threads,
                threads_word=t("stats.total_threads"),
                posts=posts,
                posts_word=t("stats.total_posts"),
                files=files,
                files_word=t("stats.total_files"),
            )

            return f'<p style="text-align:center; color:#7ab37a; margin-top:5px; font-size:0.85rem;">{line}</p>'
        except Exception as e:
            app.logger.error(f"stats_footer error: {e}")
            return ""

    app.on("ui.footer_rendering", on_footer_render)
