from models import Board, Post, PostFile, Thread


def init_app(app):
    def on_footer_render(**kwargs):
        try:
            boards = Board.query.count()
            threads = Thread.query.count()
            posts = Post.query.count()
            files = PostFile.query.count()
            html = (
                '<p style="text-align:center; color:#7ab37a; margin-top:5px; font-size:0.85rem;">'
                f"Всего: {boards} досок, {threads} тредов, {posts} постов, {files} файлов"
                "</p>"
            )
            return html
        except Exception as e:
            app.logger.error(f"stats_footer error: {e}")
            return ""

    app.on("ui.footer_rendering", on_footer_render)
