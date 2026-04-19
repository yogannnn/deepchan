from flask import Flask, render_template, redirect, url_for, request, abort, make_response, Response, flash, send_file, session
import html
from config import Config
from models import db, Board, Thread, Post, PostFile, PostFTS, Ban, WordFilter, Setting, hash_password, check_password
from forms import PostForm
from utils import save_files, check_rate_limit, process_comment, check_ban, apply_word_filters, generate_captcha
from datetime import datetime, timedelta
import os
import logging
import shutil
from logging.handlers import RotatingFileHandler
from sqlalchemy import inspect, text, func
from functools import wraps
import io
import time
import random

app = Flask(__name__)
app.config.from_object(Config)
db.init_app(app)
app.secret_key = app.config['SECRET_KEY']

app.jinja_env.filters['process_comment'] = process_comment

if not app.debug:
    handler = RotatingFileHandler('board.log', maxBytes=10000, backupCount=3)
    handler.setLevel(logging.INFO)
    app.logger.addHandler(handler)

os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)
os.makedirs(os.path.join(app.config['UPLOAD_FOLDER'], 'thumbs'), exist_ok=True)

def load_settings():
    with app.app_context():
        # DEPLOY_MODE берём только из переменной окружения, не из БД
        app.config['DEPLOY_MODE'] = os.environ.get('DEPLOY_MODE', 'production')
        if not inspect(db.engine).has_table('setting'):
            return
        settings = Setting.query.all()
        for s in settings:
            if s.key == 'DEPLOY_MODE':
                continue
            if s.key in ('CAPTCHA_ENABLED', 'STATS_SHOW_IPS', 'BOARD_CLOSED', 'AUTO_REFRESH_ENABLED'):
                app.config[s.key] = s.value == 'True'
            elif s.key in ('AUTO_REFRESH_INTERVAL', 'RATE_LIMIT_SECONDS', 'THREADS_PER_PAGE', 'POSTS_PER_PAGE', 'MAX_FILES', 'MAX_CONTENT_LENGTH', 'MAX_IMAGE_DIMENSION'):
                app.config[s.key] = int(s.value) if s.value.isdigit() else 5000
            elif s.key in ('HEADER_HTML', 'FOOTER_HTML', 'SITE_TITLE'):
                app.config[s.key] = s.value
            elif s.key == 'ALLOWED_EXTENSIONS':
                app.config['ALLOWED_EXTENSIONS'] = s.value.split(',') if s.value else ['jpg', 'jpeg', 'png', 'gif']
            elif s.key == 'WEBP_CONVERT_ENABLED':
                app.config['WEBP_CONVERT_ENABLED'] = s.value == 'True'
            elif s.key == 'STEALTH_TRIM':
                app.config['STEALTH_TRIM'] = s.value == 'True'
            elif s.value == 'True':
                app.config[s.key] = True
            elif s.value == 'False':
                app.config[s.key] = False
            elif s.value.isdigit():
                app.config[s.key] = int(s.value)
            else:
                app.config[s.key] = s.value

def save_setting(key, value):
    s = db.session.get(Setting, key)
    if not s:
        s = Setting(key=key)
    s.value = str(value)
    db.session.add(s)
    db.session.commit()
    app.config[key] = value

def admin_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        auth = request.authorization
        if not auth or auth.password != app.config['ADMIN_PASSWORD']:
            return authenticate()
        return f(*args, **kwargs)
    return decorated

def authenticate():
    return Response('Введите логин и пароль.', 401, {'WWW-Authenticate': 'Basic realm="Admin Area"'})

@app.before_request
def check_board_closed():
    if app.config.get('BOARD_CLOSED', False):
        if request.path.startswith('/admin') or request.path.startswith('/static'):
            return
        if request.endpoint != 'board_closed':
            return render_template('board_closed.html'), 503

@app.route('/closed')
def board_closed():
    return render_template('board_closed.html')

@app.route('/captcha')
def captcha_route():
    data, text = generate_captcha()
    session['captcha_text'] = text
    return send_file(io.BytesIO(data.getvalue()), mimetype='image/png')

@app.route('/catalog', strict_slashes=False)
def global_catalog():
    board_id = request.args.get('board_id', type=int)
    page = request.args.get('page', 1, type=int)
    per_page = int(app.config.get('THREADS_PER_PAGE', 30))
    query = Thread.query.filter(Thread.posts.any())
    if board_id:
        query = query.filter(Thread.board_id == board_id)
    threads_paginated = query.order_by(Thread.is_pinned.desc(), Thread.bumped_at.desc()).paginate(
        page=page, per_page=per_page, error_out=False)
    boards = Board.query.all()
    return render_template('catalog_global.html',
                           threads=threads_paginated.items,
                           pagination=threads_paginated,
                           boards=boards,
                           selected_board=board_id)

@app.route('/search', strict_slashes=False)
def global_search():
    query = request.args.get('q', '').strip()
    board_id = request.args.get('board_id', type=int)
    page = request.args.get('page', 1, type=int)
    per_page = 20
    results = []
    pagination = None
    boards = Board.query.all()
    if query:
        post_query = Post.query.join(Thread).join(Board)
        if board_id:
            post_query = post_query.filter(Board.id == board_id)
        post_query = post_query.filter(Post.search_text.contains(query.lower())).order_by(Post.created_at.desc())
        pagination = post_query.paginate(page=page, per_page=per_page, error_out=False)
        results = pagination.items
    return render_template('search_global.html', query=query, results=results, pagination=pagination,
                           boards=boards, selected_board=board_id)

@app.route('/bbcode')
def bbcode_help():
    return render_template('bbcode.html')

@app.route('/')
def index():
    boards = Board.query.all()
    return render_template('index.html', boards=boards)

@app.route('/<string:board_name>/', strict_slashes=False)
def board(board_name):
    board = Board.query.filter_by(short_name=board_name).first_or_404()
    page = request.args.get('page', 1, type=int)
    per_page = int(app.config.get('THREADS_PER_PAGE', 50))
    threads_paginated = board.threads.filter(Thread.posts.any()).order_by(
        Thread.is_pinned.desc(), Thread.bumped_at.desc()
    ).paginate(page=page, per_page=per_page, error_out=False)
    form = PostForm()
    return render_template('board.html', 
                           board=board, 
                           threads=threads_paginated.items,
                           pagination=threads_paginated,
                           form=form)

@app.route('/<string:board_name>/catalog', strict_slashes=False)
def board_catalog(board_name):
    board = Board.query.filter_by(short_name=board_name).first_or_404()
    per_page = int(app.config.get('THREADS_PER_PAGE', 30))
    threads = board.threads.filter(Thread.posts.any()).order_by(Thread.is_pinned.desc(), Thread.bumped_at.desc()).limit(per_page).all()
    return render_template('catalog.html', board=board, threads=threads)

@app.route('/<string:board_name>/thread/<int:thread_id>')
def thread(board_name, thread_id):
    board = Board.query.filter_by(short_name=board_name).first_or_404()
    thread = Thread.query.filter_by(id=thread_id, board_id=board.id).first_or_404()
    page = request.args.get('page', 1, type=int)
    per_page = int(app.config.get('POSTS_PER_PAGE', 50))
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

@app.route('/<string:board_name>/post', methods=['POST'])
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

        safe_name = html.escape(form.name.data) if form.name.data else 'Аноним'
        safe_subject = html.escape(form.subject.data) if form.subject.data else None

        post = Post(
            thread_id=thread.id,
            name=safe_name,
            subject=safe_subject if not thread_id else None,
            comment=filtered_comment,
            sage=sage,
            password_hash=hash_password(form.password.data) if form.password.data else None,
            ip_address=request.remote_addr
        )
        post.search_text = (post.comment + ' ' + (post.subject or '')).lower()
        db.session.add(post)
        db.session.flush()

        for fn, tn, order, size, md5 in saved_files:
            pf = PostFile(post_id=post.id, file_path=fn, thumb_path=tn, file_order=order,
                          file_size=size, md5_hash=md5)
            db.session.add(pf)

        if not sage:
            thread.bumped_at = datetime.utcnow()

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
            per_page = int(app.config.get('POSTS_PER_PAGE', 50))
            last_page = (total_posts + per_page - 1) // per_page
            return redirect(url_for('thread', board_name=board_name, thread_id=thread_id, page=last_page))
        else:
            return redirect(url_for('thread', board_name=board_name, thread_id=thread.id))
    else:
        return render_template('error.html', form=form), 400

@app.route('/<string:board_name>/delete/<int:post_id>', methods=['POST'])
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
                    os.remove(os.path.join(app.config['UPLOAD_FOLDER'], pf.file_path))
                    os.remove(os.path.join(app.config['UPLOAD_FOLDER'], 'thumbs', pf.thumb_path))
                except:
                    pass
            PostFTS.query.filter_by(post_id=p.id).delete()
        db.session.delete(thread)
        db.session.commit()
        return redirect(url_for('board', board_name=board.short_name))
    else:
        for pf in post.files:
            try:
                os.remove(os.path.join(app.config['UPLOAD_FOLDER'], pf.file_path))
                os.remove(os.path.join(app.config['UPLOAD_FOLDER'], 'thumbs', pf.thumb_path))
            except:
                pass
        PostFTS.query.filter_by(post_id=post.id).delete()
        db.session.delete(post)
        db.session.commit()
        return redirect(url_for('thread', board_name=board.short_name, thread_id=thread.id))

@app.route('/<string:board_name>/search')
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

@app.route('/<string:board_name>/hide/<int:thread_id>')
def hide_thread(board_name, thread_id):
    resp = make_response(redirect(url_for('board', board_name=board_name)))
    hidden = request.cookies.get('hidden_threads', '').split(',')
    hidden = [h for h in hidden if h]
    if str(thread_id) not in hidden:
        hidden.append(str(thread_id))
    resp.set_cookie('hidden_threads', ','.join(hidden), max_age=30*24*3600)
    return resp

# ===== АДМИНКА =====
@app.route('/admin')
@admin_required
def admin_index():
    return render_template('admin/index.html')

@app.route('/admin/boards')
@admin_required
def admin_boards():
    boards = Board.query.all()
    return render_template('admin/boards.html', boards=boards)

@app.route('/admin/boards/create', methods=['GET', 'POST'])
@admin_required
def admin_create_board():
    if request.method == 'POST':
        b = Board(
            short_name=request.form['short_name'],
            name=request.form['name'],
            description=request.form.get('description', '')
        )
        db.session.add(b)
        db.session.commit()
        return redirect(url_for('admin_boards'))
    return render_template('admin/board_form.html', board=None)

@app.route('/admin/boards/edit/<int:board_id>', methods=['GET', 'POST'])
@admin_required
def admin_edit_board(board_id):
    board = Board.query.get_or_404(board_id)
    if request.method == 'POST':
        board.short_name = request.form['short_name']
        board.name = request.form['name']
        board.description = request.form.get('description', '')
        db.session.commit()
        return redirect(url_for('admin_boards'))
    return render_template('admin/board_form.html', board=board)

@app.route('/admin/boards/delete/<int:board_id>', methods=['POST'])
@admin_required
def admin_delete_board(board_id):
    board = Board.query.get_or_404(board_id)
    db.session.delete(board)
    db.session.commit()
    return redirect(url_for('admin_boards'))

@app.route('/admin/threads')
@admin_required
def admin_threads():
    board_id = request.args.get('board_id', type=int)
    query = Thread.query
    if board_id:
        query = query.filter(Thread.board_id == board_id)
    threads = query.order_by(Thread.bumped_at.desc()).all()
    boards = Board.query.all()
    return render_template('admin/threads.html', threads=threads, boards=boards, selected_board=board_id)

@app.route('/admin/threads/toggle_pin/<int:thread_id>', methods=['POST'])
@admin_required
def admin_toggle_pin(thread_id):
    thread = Thread.query.get_or_404(thread_id)
    thread.is_pinned = not thread.is_pinned
    db.session.commit()
    return redirect(url_for('admin_threads', board_id=request.args.get('board_id')))

@app.route('/admin/threads/toggle_lock/<int:thread_id>', methods=['POST'])
@admin_required
def admin_toggle_lock(thread_id):
    thread = Thread.query.get_or_404(thread_id)
    thread.is_locked = not thread.is_locked
    db.session.commit()
    return redirect(url_for('admin_threads', board_id=request.args.get('board_id')))

@app.route('/admin/threads/delete/<int:thread_id>', methods=['POST'])
@admin_required
def admin_delete_thread(thread_id):
    thread = Thread.query.get_or_404(thread_id)
    for post in thread.posts:
        for pf in post.files:
            try:
                os.remove(os.path.join(app.config['UPLOAD_FOLDER'], pf.file_path))
                os.remove(os.path.join(app.config['UPLOAD_FOLDER'], 'thumbs', pf.thumb_path))
            except:
                pass
    db.session.delete(thread)
    db.session.commit()
    return redirect(url_for('admin_threads', board_id=request.args.get('board_id')))

@app.route('/admin/threads/bulk', methods=['POST'])
@admin_required
def admin_bulk_threads():
    action = request.form.get('action')
    thread_ids = request.form.getlist('thread_ids')
    if not thread_ids:
        return redirect(url_for('admin_threads'))
    threads = Thread.query.filter(Thread.id.in_(thread_ids)).all()
    if action == 'delete':
        for t in threads:
            for post in t.posts:
                for pf in post.files:
                    try:
                        os.remove(os.path.join(app.config['UPLOAD_FOLDER'], pf.file_path))
                        os.remove(os.path.join(app.config['UPLOAD_FOLDER'], 'thumbs', pf.thumb_path))
                    except:
                        pass
            db.session.delete(t)
    elif action == 'lock':
        for t in threads:
            t.is_locked = True
    elif action == 'unlock':
        for t in threads:
            t.is_locked = False
    db.session.commit()
    return redirect(url_for('admin_threads', board_id=request.args.get('board_id')))

@app.route('/admin/thread/<int:thread_id>')
@admin_required
def admin_thread_detail(thread_id):
    thread = Thread.query.get_or_404(thread_id)
    posts = thread.posts.order_by(Post.created_at.asc()).all()
    return render_template('admin/thread_detail.html', thread=thread, posts=posts)

@app.route('/admin/post/delete/<int:post_id>', methods=['POST'])
@admin_required
def admin_delete_post(post_id):
    post = Post.query.get_or_404(post_id)
    thread = post.thread
    for pf in post.files:
        try:
            os.remove(os.path.join(app.config['UPLOAD_FOLDER'], pf.file_path))
            os.remove(os.path.join(app.config['UPLOAD_FOLDER'], 'thumbs', pf.thumb_path))
        except:
            pass
    PostFTS.query.filter_by(post_id=post.id).delete()
    db.session.delete(post)
    db.session.commit()
    if thread.posts.count() == 0:
        db.session.delete(thread)
        db.session.commit()
        return redirect(url_for('admin_threads'))
    return redirect(url_for('admin_thread_detail', thread_id=thread.id))

@app.route('/admin/files')
@admin_required
def admin_files():
    board_id = request.args.get('board_id', type=int)
    query = PostFile.query.join(Post).join(Thread).join(Board)
    if board_id:
        query = query.filter(Board.id == board_id)
    files = query.order_by(PostFile.id.desc()).limit(500).all()
    boards = Board.query.all()
    duplicates = []
    show_dupes = request.args.get('show_dupes') == '1'
    if show_dupes:
        dupes = db.session.query(PostFile.md5_hash, db.func.count(PostFile.id)).group_by(PostFile.md5_hash).having(db.func.count(PostFile.id) > 1).all()
        for md5, count in dupes:
            files_dupe = PostFile.query.filter_by(md5_hash=md5).all()
            duplicates.append((md5, count, files_dupe))
    return render_template('admin/files.html', files=files, boards=boards, selected_board=board_id,
                           duplicates=duplicates, show_dupes=show_dupes)

@app.route('/admin/files/delete/<int:file_id>', methods=['POST'])
@admin_required
def admin_delete_file(file_id):
    pf = PostFile.query.get_or_404(file_id)
    try:
        os.remove(os.path.join(app.config['UPLOAD_FOLDER'], pf.file_path))
        os.remove(os.path.join(app.config['UPLOAD_FOLDER'], 'thumbs', pf.thumb_path))
    except:
        pass
    db.session.delete(pf)
    db.session.commit()
    flash('Файл удалён', 'info')
    return redirect(url_for('admin_files', board_id=request.args.get('board_id')))

@app.route('/admin/files/orphaned')
@admin_required
def admin_orphaned_files():
    orphaned = []
    for root, dirs, files in os.walk(app.config['UPLOAD_FOLDER']):
        for f in files:
            if '_thumb' in f:
                continue
            full_path = os.path.join(root, f)
            rel_path = os.path.relpath(full_path, app.config['UPLOAD_FOLDER'])
            exists = PostFile.query.filter_by(file_path=rel_path).first()
            if not exists:
                size = os.path.getsize(full_path)
                orphaned.append((rel_path, size))
    return render_template('admin/orphaned.html', orphaned=orphaned)

@app.route('/admin/files/cleanup', methods=['POST'])
@admin_required
def admin_cleanup_files():
    action = request.form.get('action')
    if action == 'orphaned':
        for root, dirs, files in os.walk(app.config['UPLOAD_FOLDER']):
            for f in files:
                if '_thumb' in f:
                    continue
                full_path = os.path.join(root, f)
                rel_path = os.path.relpath(full_path, app.config['UPLOAD_FOLDER'])
                if not PostFile.query.filter_by(file_path=rel_path).first():
                    try:
                        os.remove(full_path)
                        thumb_path = full_path.replace('/uploads/', '/uploads/thumbs/').replace('.', '_thumb.')
                        if os.path.exists(thumb_path):
                            os.remove(thumb_path)
                    except:
                        pass
        flash('Осиротевшие файлы удалены', 'success')
    elif action == 'old_threads':
        threshold = datetime.utcnow() - timedelta(days=30)
        old_threads = Thread.query.filter(Thread.bumped_at < threshold).all()
        for t in old_threads:
            for p in t.posts:
                for pf in p.files:
                    try:
                        os.remove(os.path.join(app.config['UPLOAD_FOLDER'], pf.file_path))
                        os.remove(os.path.join(app.config['UPLOAD_FOLDER'], 'thumbs', pf.thumb_path))
                    except:
                        pass
            db.session.delete(t)
        db.session.commit()
        flash(f'Удалено старых тредов: {len(old_threads)}', 'success')
    return redirect(url_for('admin_files'))

@app.route('/admin/bans')
@admin_required
def admin_bans():
    bans = Ban.query.order_by(Ban.created_at.desc()).all()
    return render_template('admin/bans.html', bans=bans)

@app.route('/admin/bans/add', methods=['POST'])
@admin_required
def admin_add_ban():
    ip = request.form['ip_pattern']
    reason = request.form.get('reason', '')
    expires_days = request.form.get('expires_days', type=int)
    expires = datetime.utcnow() + timedelta(days=expires_days) if expires_days else None
    ban = Ban(ip_pattern=ip, reason=reason, expires_at=expires)
    db.session.add(ban)
    db.session.commit()
    flash(f'IP {ip} забанен', 'success')
    return redirect(url_for('admin_bans'))

@app.route('/admin/bans/toggle/<int:ban_id>', methods=['POST'])
@admin_required
def admin_toggle_ban(ban_id):
    ban = Ban.query.get_or_404(ban_id)
    ban.active = not ban.active
    db.session.commit()
    return redirect(url_for('admin_bans'))

@app.route('/admin/bans/delete/<int:ban_id>', methods=['POST'])
@admin_required
def admin_delete_ban(ban_id):
    ban = Ban.query.get_or_404(ban_id)
    db.session.delete(ban)
    db.session.commit()
    flash('Бан удалён', 'success')
    return redirect(url_for('admin_bans'))

@app.route('/admin/filters')
@admin_required
def admin_filters():
    filters = WordFilter.query.order_by(WordFilter.id.desc()).all()
    return render_template('admin/filters.html', filters=filters)

@app.route('/admin/filters/add', methods=['POST'])
@admin_required
def admin_add_filter():
    pattern = request.form['pattern']
    replacement = request.form.get('replacement', '[CENSORED]')
    is_regex = 'is_regex' in request.form
    action = request.form['action']
    wf = WordFilter(pattern=pattern, replacement=replacement, is_regex=is_regex, action=action)
    db.session.add(wf)
    db.session.commit()
    flash('Фильтр добавлен', 'success')
    return redirect(url_for('admin_filters'))

@app.route('/admin/filters/toggle/<int:filter_id>', methods=['POST'])
@admin_required
def admin_toggle_filter(filter_id):
    wf = WordFilter.query.get_or_404(filter_id)
    wf.active = not wf.active
    db.session.commit()
    return redirect(url_for('admin_filters'))

@app.route('/admin/filters/delete/<int:filter_id>', methods=['POST'])
@admin_required
def admin_delete_filter(filter_id):
    wf = WordFilter.query.get_or_404(filter_id)
    db.session.delete(wf)
    db.session.commit()
    flash('Фильтр удалён', 'success')
    return redirect(url_for('admin_filters'))

@app.route('/admin/settings', methods=['GET', 'POST'])
@admin_required
def admin_settings():
    if request.method == 'POST':
        save_setting('CAPTCHA_ENABLED', 'captcha_enabled' in request.form)
        save_setting('STATS_SHOW_IPS', 'stats_show_ips' in request.form)
        save_setting('BOARD_CLOSED', 'board_closed' in request.form)
        save_setting('AUTO_REFRESH_ENABLED', 'auto_refresh_enabled' in request.form)
        save_setting('AUTO_REFRESH_INTERVAL', request.form.get('auto_refresh_interval', '30'))
        save_setting('RATE_LIMIT_SECONDS', request.form.get('rate_limit_seconds', '30'))
        save_setting('HEADER_HTML', request.form.get('header_html', ''))
        save_setting('FOOTER_HTML', request.form.get('footer_html', ''))
        save_setting('SITE_TITLE', request.form.get('site_title', 'Имиджборда'))
        save_setting('THREADS_PER_PAGE', request.form.get('threads_per_page', '50'))
        save_setting('POSTS_PER_PAGE', request.form.get('posts_per_page', '50'))
        save_setting('MAX_FILES', request.form.get('max_files', '4'))
        allowed = ','.join(request.form.getlist('allowed_extensions'))
        save_setting('ALLOWED_EXTENSIONS', allowed)
        save_setting('ANNOUNCEMENT_HTML', request.form.get('announcement_html', ''))
        save_setting('MAX_CONTENT_LENGTH', int(request.form.get('max_content_length', 10)) * 1024 * 1024)
        save_setting('MAX_IMAGE_DIMENSION', request.form.get('max_image_dimension', '5000'))
        save_setting('WEBP_CONVERT_ENABLED', 'webp_convert_enabled' in request.form)
        save_setting('STEALTH_TRIM', 'stealth_trim' in request.form)
        flash('Настройки сохранены', 'success')
        return redirect(url_for('admin_settings'))

    ctx = {
        'captcha_enabled': app.config.get('CAPTCHA_ENABLED', False),
        'stats_show_ips': app.config.get('STATS_SHOW_IPS', False),
        'board_closed': app.config.get('BOARD_CLOSED', False),
        'auto_refresh_enabled': app.config.get('AUTO_REFRESH_ENABLED', True),
        'auto_refresh_interval': app.config.get('AUTO_REFRESH_INTERVAL', 30),
        'rate_limit_seconds': app.config.get('RATE_LIMIT_SECONDS', 30),
        'header_html': app.config.get('HEADER_HTML', ''),
        'footer_html': app.config.get('FOOTER_HTML', ''),
        'site_title': app.config.get('SITE_TITLE', 'Имиджборда'),
        'threads_per_page': app.config.get('THREADS_PER_PAGE', 50),
        'posts_per_page': app.config.get('POSTS_PER_PAGE', 50),
        'max_files': app.config.get('MAX_FILES', 4),
        'allowed_extensions': app.config.get('ALLOWED_EXTENSIONS', ['jpg','jpeg','png','gif']),
        'announcement_html': app.config.get('ANNOUNCEMENT_HTML', ''),
        'max_content_length': int(app.config.get('MAX_CONTENT_LENGTH') or 10*1024*1024) // (1024 * 1024),
        'max_image_dimension': app.config.get('MAX_IMAGE_DIMENSION', 5000),
        'webp_convert_enabled': app.config.get('WEBP_CONVERT_ENABLED', True),
        'stealth_trim': app.config.get('STEALTH_TRIM', True),
    }
    return render_template('admin/settings.html', **ctx)

@app.route('/admin/stats')
@admin_required
def admin_stats():
    total_threads = Thread.query.count()
    total_posts = Post.query.count()
    total_files = PostFile.query.count()
    total_boards = Board.query.count()

    today = datetime.utcnow().date()
    daily_posts = []
    daily_threads = []
    for i in range(7):
        day = today - timedelta(days=i)
        start = datetime(day.year, day.month, day.day)
        end = start + timedelta(days=1)
        posts_count = Post.query.filter(Post.created_at >= start, Post.created_at < end).count()
        threads_count = Thread.query.filter(Thread.created_at >= start, Thread.created_at < end).count()
        daily_posts.append((day.strftime('%d.%m'), posts_count))
        daily_threads.append((day.strftime('%d.%m'), threads_count))

    top_boards = db.session.query(
        Board.short_name, Board.name, func.count(Post.id).label('post_count')
    ).select_from(Board).join(Thread).join(Post).group_by(Board.id).order_by(func.count(Post.id).desc()).limit(10).all()

    total_size_bytes = db.session.query(func.coalesce(func.sum(PostFile.file_size), 0)).scalar()
    total_size_mb = total_size_bytes / (1024 * 1024)

    db_path = app.config['SQLALCHEMY_DATABASE_URI'].replace('sqlite:///', '')
    db_size_bytes = os.path.getsize(db_path) if os.path.exists(db_path) else 0
    db_size_mb = db_size_bytes / (1024 * 1024)

    upload_folder = app.config['UPLOAD_FOLDER']
    disk_usage = shutil.disk_usage(upload_folder)
    total_disk_gb = disk_usage.total / (1024**3)
    used_disk_gb = disk_usage.used / (1024**3)
    free_disk_gb = disk_usage.free / (1024**3)

    show_ips = app.config.get('STATS_SHOW_IPS', False)
    recent_ips = []
    if show_ips:
        recent_ips = db.session.query(Post.ip_address, func.count(Post.id)).group_by(Post.ip_address).order_by(func.count(Post.id).desc()).limit(20).all()

    return render_template('admin/stats.html',
                           total_threads=total_threads,
                           total_posts=total_posts,
                           total_files=total_files,
                           total_boards=total_boards,
                           daily_posts=daily_posts,
                           daily_threads=daily_threads,
                           top_boards=top_boards,
                           total_size_mb=total_size_mb,
                           db_size_mb=db_size_mb,
                           total_disk_gb=total_disk_gb,
                           used_disk_gb=used_disk_gb,
                           free_disk_gb=free_disk_gb,
                           recent_ips=recent_ips,
                           show_ips=show_ips)

# ===== WSGI Middleware для удаления заголовков и задержки =====
class ParanoidMiddleware:
    def __init__(self, app):
        self.app = app

    def __call__(self, environ, start_response):
        def custom_start_response(status, headers, exc_info=None):
            # Удаляем Server и X-Powered-By из заголовков
            new_headers = [(k, v) for k, v in headers if k not in ('Server', 'X-Powered-By')]
            return start_response(status, new_headers, exc_info)

        # Случайная задержка 5-50 мс
        time.sleep(random.uniform(0.005, 0.05))
        return self.app(environ, custom_start_response)

app.wsgi_app = ParanoidMiddleware(app.wsgi_app)

# ===== КЕШИРОВАНИЕ СТАТИКИ =====
@app.after_request
def add_cache_headers(response):
    if request.path.startswith('/static'):
        response.cache_control.no_cache = None
        response.cache_control.no_store = None
        if request.path.endswith('.css') or '/fonts/' in request.path:
            response.cache_control.max_age = 604800
            response.cache_control.public = True
        elif request.path.endswith(('.png', '.jpg', '.jpeg', '.gif', '.webp')):
            response.cache_control.max_age = 86400
            response.cache_control.public = True
        else:
            response.cache_control.max_age = 3600
    else:
        response.cache_control.no_cache = True
        response.cache_control.no_store = True
    return response

from flask_wtf.csrf import generate_csrf
app.jinja_env.globals['csrf_token'] = generate_csrf

if __name__ == '__main__':
    with app.app_context():
        db.create_all()
        if not inspect(db.engine).has_table('setting'):
            Setting.__table__.create(db.engine)
        load_settings()
        with db.engine.connect() as conn:
            res = conn.execute(text("PRAGMA table_info(post)"))
            cols = [row[1] for row in res]
            if 'search_text' not in cols:
                conn.execute(text("ALTER TABLE post ADD COLUMN search_text TEXT"))
                conn.commit()
        for post in Post.query.all():
            if not post.search_text:
                post.search_text = (post.comment + ' ' + (post.subject or '')).lower()
        db.session.commit()
        with db.engine.connect() as conn:
            for table, col, col_type in [('post_file', 'md5_hash', 'VARCHAR(32)'),
                                         ('post_file', 'file_size', 'INTEGER DEFAULT 0'),
                                         ('post', 'ip_address', 'VARCHAR(45)')]:
                res = conn.execute(text(f"PRAGMA table_info({table.split()[0]})"))
                cols = [row[1] for row in res]
                if col not in cols:
                    conn.execute(text(f"ALTER TABLE {table} ADD COLUMN {col} {col_type}"))
            conn.commit()
        insp = inspect(db.engine)
        if not insp.has_table('post_fts'):
            PostFTS.__table__.create(db.engine)
        if not Board.query.filter_by(short_name='b').first():
            b = Board(short_name='b', name='Бред', description='Общий раздел')
            db.session.add(b)
            db.session.commit()
    deploy_mode = app.config.get('DEPLOY_MODE', 'production')
    if deploy_mode == 'development':
        print("🚀 Запуск через Flask development server на http://127.0.0.1:5000")
        app.run(host='127.0.0.1', port=5000, debug=True, threaded=True)
    else:
        from waitress import serve
        print("🚀 Запуск через Waitress (production) на http://127.0.0.1:5000")
        serve(app, host='127.0.0.1', port=5000, threads=4, channel_timeout=300, ident=None)
