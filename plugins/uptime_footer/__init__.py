import time
from datetime import timedelta


def init_app(app):
    start_time = time.time()

    def on_footer_render(**kwargs):
        uptime_seconds = int(time.time() - start_time)
        td = timedelta(seconds=uptime_seconds)
        days = td.days
        hours, remainder = divmod(td.seconds, 3600)
        minutes, _ = divmod(remainder, 60)

        parts = []
        if days:
            parts.append(f"{days}d")
        if hours:
            parts.append(f"{hours}h")
        parts.append(f"{minutes}m")

        uptime_str = " ".join(parts)
        return f'<p style="text-align:center; color:#7ab37a; font-size:0.75rem;">🟢 Uptime: {uptime_str}</p>'

    app.on("ui.footer_rendering", on_footer_render)
