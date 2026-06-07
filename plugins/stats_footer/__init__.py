from core.i18n import t
from services.stats import get_global_stats


def init_app(app):
    def on_footer_render(**kwargs):
        try:
            stats = get_global_stats()
            line = t(
                "stats.footer_line",
                boards=stats["boards"],
                boards_word=t("stats.total_boards"),
                threads=stats["threads"],
                threads_word=t("stats.total_threads"),
                posts=stats["posts"],
                posts_word=t("stats.total_posts"),
                files=stats["files"],
                files_word=t("stats.total_files"),
            )
            return f'<p style="text-align:center; color:#7ab37a; margin-top:5px; font-size:0.85rem;">{line}</p>'
        except Exception as e:
            app.logger.error(f"stats_footer error: {e}")
            return ""

    app.on("ui.footer_rendering", on_footer_render)
