from flask import Blueprint, render_template, redirect, url_for, request, abort, make_response, flash, current_app
from models import db, Board, Thread, Post, PostFile, PostFTS, RadioTrack, hash_password, check_password
from forms import PostForm
from utils import (
    save_files, check_rate_limit, process_comment, check_ban, apply_word_filters,
    get_file_hash, get_media_duration, generate_tripcode
)
from datetime import datetime, timezone
import html
import os

board_bp = Blueprint('board', __name__, url_prefix='')

def csrf_protect(action):
    from functools import wraps
    from flask import request, abort
    from utils import verify_csrf_token
    def decorator(f):
        @wraps(f)
        def decorated(*args, **kwargs):
            if request.method == 'POST':
                user_id = request.authorization.username if request.authorization else 'anonymous'
                token = request.form.get('csrf_token')
                timestamp = request.form.get('csrf_timestamp')
                if not token or not timestamp:
                    abort(403, description='CSRF token missing')
                if not verify_csrf_token(user_id, action, token, timestamp, current_app.config['SECRET_KEY']):
                    abort(403, description='CSRF token invalid')
            return f(*args, **kwargs)
        return decorated
    return decorator

@board_bp.route('/<string:board_name>/', strict_slashes=False)
def board(board_name):
    board = Board.query.filter_by(short_name=board_name).first_or_404()
    page = request.args.get('page', 1, type=int)
    per_page = int(current_app.config.get('THREADS_PER_PAGE', 50))
    threads_paginated = board.threads.filter(Thread.posts.any()).order_by(
        Thread.is_pinned.desc(), Thread.bumped_at.desc()
    ).paginate(page=page, per_page=per_page, error_out=False)
    form = PostForm()
    return render_template('board.html', 
                           board=board, 
                           threads=threads_paginated.items,
                           pagination=threads_paginated,
                           form=form)

@board_bp.route('/<string:board_name>/catalog', strict_slashes=False)
def board_catalog(board_name):
    board = Board.query.filter_by(short_name=board_name).first_or_404()
    per_page = int(current_app.config.get('THREADS_PER_PAGE', 30))
    threads = board.threads.filter(Thread.posts.any()).order_by(Thread.is_pinned.desc(), Thread.bumped_at.desc()).limit(per_page).all()
    return render_template('catalog.html', board=board, threads=threads)

@board_bp.route('/<string:board_name>/thread/<int:thread_id>')
def thread(board_name, thread_id):
    board = Board.query.filter_by(short_name=board_name).first_or_404()
    thread = Thread.query.filter_by(id=thread_id, board_id=board.id).first_or_404()
    page = request.args.get('page', 1, type=int)
    per_page = int(current_app.config.get('POSTS_PER_PAGE', 50))
    posts_paginated = thread.posts.order_by(Post.created_at.asc()).paginate(
        page=page, per_page=per_page, error_out=False
    )
    form = PostForm()
    quote_text = ""
    reply_to = request.args.get('reply', type=int)
    if reply_to:
        quote_text = f">>{reply_to}\n"
    return render_template('thread.html', 
                           board=board, 
                           thread=thread, 
                           posts=posts_paginated.items,
                           pagination=posts_paginated,
                           form=form,
                           quote_text=quote_text)

@board_bp.route('/<string:board_name>/post', methods=['POST'])
@csrf_protect('post')
def create_post(board_name):
    board = Board.query.filter_by(short_name=board_name).first_or_404()
    form = PostForm()
    check_rate_limit()
    check_ban(request.remote_addr)
    if form.validate_on_submit():
        thread_id = request.args.get('thread_id', type=int)
        sage = form.sage.data
        if thread_id:
            thread = Thread.query.get_or_404(thread_id)
            if thread.is_locked:
                abort(403, description="Тред закрыт")
            if not form.files.data and not form.comment.data:
                form.comment.errors.append('Нужно ввести комментарий или прикрепить файл')
                return render_template('error.html', form=form), 400
        else:
            if not form.subject.data:
                form.subject.errors.append('Тема обязательна для нового треда')
                return render_template('error.html', form=form), 400
            if not form.files.data and not form.comment.data:
                form.comment.errors.append('Нужно ввести комментарий или прикрепить файл')
                return render_template('error.html', form=form), 400
            thread = Thread(board_id=board.id)
            db.session.add(thread)
            db.session.flush()

        filtered_comment = apply_word_filters(form.comment.data)
        filtered_subject = apply_word_filters(form.subject.data) if form.subject.data else None

        saved_files = save_files(form.files.data)

        # Обработка трипкода
        name_input = form.name.data.strip() if form.name.data else "Аноним"
        display_name = name_input
        tripcode = None
        is_admin = False
        if "#" in name_input:
            parts = name_input.split("#", 1)
            display_name = parts[0] or "Аноним"
            password = parts[1]
            tripcode = generate_tripcode(password, current_app.config["SECRET_KEY"])
            admin_secret = current_app.config.get("ADMIN_TRIP_SECRET", "")
            if admin_secret and password == admin_secret:
                is_admin = True
        safe_name = html.escape(display_name) if display_name else "Аноним"
        safe_subject = html.escape(form.subject.data) if form.subject.data else None

        post = Post(
            thread_id=thread.id,
            name=safe_name,
            tripcode=tripcode,
            is_admin_post=is_admin,
            subject=safe_subject if not thread_id else None,
            comment=filtered_comment,
            sage=sage,
            password_hash=hash_password(form.password.data) if form.password.data else None,
            ip_address=request.remote_addr
        )
        post.search_text = (post.comment + ' ' + (post.subject or '')).lower()
        db.session.add(post)
        db.session.flush()

        for fn, tn, order, size, sha256, file_type, duration in saved_files:
            pf = PostFile(post_id=post.id, file_path=fn, thumb_path=tn, file_order=order,
                          file_size=size, md5_hash=sha256, file_type=file_type, duration=duration)
            db.session.add(pf)

            if file_type == 'audio' and current_app.config.get('RADIO_ENABLED', False):
                if not RadioTrack.query.filter_by(original_hash=sha256).first():
                    track = RadioTrack(
                        post_file_id=pf.id,
                        artist='Unknown',
                        title='Untitled',
                        original_hash=sha256,
                        duration=duration,
                        approved=False,
                        file_path=fn
                    )
                    db.session.add(track)

        if not sage:
            thread.bumped_at = datetime.now(timezone.utc)

        fts_entry = PostFTS(
            post_id=post.id,
            board_id=board.id,
            thread_id=thread.id,
            comment=post.comment,
            subject=post.subject or '',
            name=post.name
        )
        db.session.add(fts_entry)

        db.session.commit()

        if thread_id:
            total_posts = thread.posts.count()
            per_page = int(current_app.config.get('POSTS_PER_PAGE', 50))
            last_page = (total_posts + per_page - 1) // per_page
            return redirect(url_for('board.thread', board_name=board_name, thread_id=thread_id, page=last_page))
        else:
            return redirect(url_for('board.thread', board_name=board_name, thread_id=thread.id))
    else:
        return render_template('error.html', form=form), 400

@board_bp.route('/<string:board_name>/delete/<int:post_id>', methods=['POST'])
@csrf_protect('delete_post')
def delete_post(board_name, post_id):
    post = Post.query.get_or_404(post_id)
    password = request.form.get('password')
    if not password or not check_password(password, post.password_hash):
        abort(403, description="Неверный пароль")
    
    thread = post.thread
    board = thread.board
    is_op = (thread.posts.order_by(Post.created_at.asc()).first().id == post.id)

    if is_op:
        for p in thread.posts:
            for pf in p.files:
                try:
                    os.remove(os.path.join(current_app.config['UPLOAD_FOLDER'], pf.file_path))
                    os.remove(os.path.join(current_app.config['UPLOAD_FOLDER'], 'thumbs', pf.thumb_path))
                except:
                    pass
            PostFTS.query.filter_by(post_id=p.id).delete()
        db.session.delete(thread)
        db.session.commit()
        return redirect(url_for('board.board', board_name=board.short_name))
    else:
        for pf in post.files:
            try:
                os.remove(os.path.join(current_app.config['UPLOAD_FOLDER'], pf.file_path))
                os.remove(os.path.join(current_app.config['UPLOAD_FOLDER'], 'thumbs', pf.thumb_path))
            except:
                pass
        PostFTS.query.filter_by(post_id=post.id).delete()
        db.session.delete(post)
        db.session.commit()
        return redirect(url_for('board.thread', board_name=board.short_name, thread_id=thread.id))

@board_bp.route('/<string:board_name>/search')
def board_search(board_name):
    board = Board.query.filter_by(short_name=board_name).first_or_404()
    query = request.args.get('q', '').strip()
    page = request.args.get('page', 1, type=int)
    per_page = 20
    results = []
    pagination = None
    if query:
        post_query = Post.query.join(Thread).filter(Thread.board_id == board.id)
        post_query = post_query.filter(Post.search_text.contains(query.lower())).order_by(Post.created_at.desc())
        pagination = post_query.paginate(page=page, per_page=per_page, error_out=False)
        results = pagination.items
    return render_template('search.html', board=board, query=query, results=results, pagination=pagination)

@board_bp.route('/<string:board_name>/hide/<int:thread_id>')
def hide_thread(board_name, thread_id):
    resp = make_response(redirect(url_for('board.board', board_name=board_name)))
    hidden = request.cookies.get('hidden_threads', '').split(',')
    hidden = [h for h in hidden if h]
    if str(thread_id) not in hidden:
        hidden.append(str(thread_id))
    resp.set_cookie('hidden_threads', ','.join(hidden), max_age=30*24*3600)
    return resp
