from flask import Blueprint, render_template, send_file, session, request, redirect, url_for
from models import Board, Thread, Post
from utils import generate_captcha
import io

main_bp = Blueprint('main', __name__)

@main_bp.route('/')
def index():
    boards = Board.query.order_by(Board.position).all()
    return render_template('index.html', boards=boards)

@main_bp.route('/captcha')
def captcha_route():
    data, text = generate_captcha()
    session['captcha_text'] = text
    return send_file(io.BytesIO(data.getvalue()), mimetype='image/png')

@main_bp.route('/catalog')
def global_catalog():
    from flask import current_app
    board_id = request.args.get('board_id', type=int)
    page = request.args.get('page', 1, type=int)
    per_page = int(current_app.config.get('THREADS_PER_PAGE', 30))
    query = Thread.query.filter(Thread.posts.any())
    if board_id:
        query = query.filter(Thread.board_id == board_id)
    threads_paginated = query.order_by(Thread.is_pinned.desc(), Thread.bumped_at.desc()).paginate(
        page=page, per_page=per_page, error_out=False)
    boards = Board.query.order_by(Board.position).all()
    return render_template('catalog_global.html',
                           threads=threads_paginated.items,
                           pagination=threads_paginated,
                           boards=boards,
                           selected_board=board_id)

@main_bp.route('/search')
def global_search():
    query = request.args.get('q', '').strip()
    board_id = request.args.get('board_id', type=int)
    page = request.args.get('page', 1, type=int)
    per_page = 20
    results = []
    pagination = None
    boards = Board.query.order_by(Board.position).all()
    if query:
        post_query = Post.query.join(Thread).join(Board)
        if board_id:
            post_query = post_query.filter(Board.id == board_id)
        post_query = post_query.filter(Post.search_text.contains(query.lower())).order_by(Post.created_at.desc())
        pagination = post_query.paginate(page=page, per_page=per_page, error_out=False)
        results = pagination.items
    return render_template('search_global.html', query=query, results=results, pagination=pagination,
                           boards=boards, selected_board=board_id)

@main_bp.route('/bbcode')
def bbcode_help():
    return render_template('bbcode.html')
