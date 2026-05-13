from flask import render_template_string

from models import Board

TEMPLATE = """
<span style="margin-left: 15px; font-size: 0.9rem;">
{% for board in boards %}
  <a href="/{{ board.short_name }}/" style="color: #66ff66; margin-right: 10px; text-decoration: none;">/{{ board.short_name }}/</a>
{% endfor %}
</span>
<br>
<span style="margin-left: 15px; font-size: 0.7rem; color: #7ab37a;">(тест первого плагина, вывод досок)</span>
"""


def init_app(app):
    def on_header_render(**kwargs):
        boards = Board.query.order_by(Board.position).all()
        return render_template_string(TEMPLATE, boards=boards)

    app.on("ui.header_rendering", on_header_render)
