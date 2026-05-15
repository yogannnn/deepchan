import os
from datetime import datetime

from flask import current_app

LOG_FILE = os.path.join(os.path.dirname(__file__), "new_posts.log")


def init_app(app):
    def on_post_created(post, board, thread, **kwargs):
        timestamp = datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S")
        log_line = f"[{timestamp}] New post #{post.id} in /{board.short_name}/ thread #{thread.id}\n"
        with open(LOG_FILE, "a", encoding="utf-8") as f:
            f.write(log_line)
        current_app.logger.info(f"Post logger: {log_line.strip()}")

    app.on("posts.after_create", on_post_created)
