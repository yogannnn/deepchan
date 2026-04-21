from flask import Blueprint, render_template, redirect, url_for, request, abort, flash
from flask import current_app
from models import db, Board, Thread, Post, PostFile, PostFTS, Ban, WordFilter, Setting
from sqlalchemy import func
from datetime import datetime, timedelta, timezone
import os
import shutil
from functools import wraps

admin_bp = Blueprint('admin', __name__, url_prefix='/admin')

def admin_required(f):
    from flask import request, Response
    @wraps(f)
    def decorated(*args, **kwargs):
        auth = request.authorization
        if not auth or auth.password != current_app.config['ADMIN_PASSWORD']:
            return Response('Введите логин и пароль.', 401, {'WWW-Authenticate': 'Basic realm="Admin Area"'})
        return f(*args, **kwargs)
    return decorated

def csrf_protect(action):
    def decorator(f):
        from flask import request, abort
        from utils import verify_csrf_token
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

def save_setting(key, value):
    s = db.session.get(Setting, key)
    if not s:
        s = Setting(key=key)
    s.value = str(value)
    db.session.add(s)
    db.session.commit()
    current_app.config[key] = value

@admin_bp.route('/')
@admin_required
def admin_index():
    return render_template('admin/index.html')

@admin_bp.route('/boards')
@admin_required
def admin_boards():
    boards = Board.query.all()
    return render_template('admin/boards.html', boards=boards)

@admin_bp.route('/boards/create', methods=['GET', 'POST'])
@admin_required
@csrf_protect('create_board')
def admin_create_board():
    if request.method == 'POST':
        b = Board(
            short_name=request.form['short_name'],
            name=request.form['name'],
            description=request.form.get('description', '')
        )
        db.session.add(b)
        db.session.commit()
        return redirect(url_for('admin.admin_boards'))
    return render_template('admin/board_form.html', board=None)

@admin_bp.route('/boards/edit/<int:board_id>', methods=['GET', 'POST'])
@admin_required
@csrf_protect('edit_board')
def admin_edit_board(board_id):
    board = Board.query.get_or_404(board_id)
    if request.method == 'POST':
        board.short_name = request.form['short_name']
        board.name = request.form['name']
        board.description = request.form.get('description', '')
        db.session.commit()
        return redirect(url_for('admin.admin_boards'))
    return render_template('admin/board_form.html', board=board)

@admin_bp.route('/boards/delete/<int:board_id>', methods=['POST'])
@admin_required
@csrf_protect('delete_board')
def admin_delete_board(board_id):
    board = Board.query.get_or_404(board_id)
    db.session.delete(board)
    db.session.commit()
    return redirect(url_for('admin.admin_boards'))

@admin_bp.route('/threads')
@admin_required
def admin_threads():
    board_id = request.args.get('board_id', type=int)
    query = Thread.query
    if board_id:
        query = query.filter(Thread.board_id == board_id)
    threads = query.order_by(Thread.bumped_at.desc()).all()
    boards = Board.query.all()
    return render_template('admin/threads.html', threads=threads, boards=boards, selected_board=board_id)

@admin_bp.route('/threads/toggle_pin/<int:thread_id>', methods=['POST'])
@admin_required
@csrf_protect('toggle_pin')
def admin_toggle_pin(thread_id):
    thread = Thread.query.get_or_404(thread_id)
    thread.is_pinned = not thread.is_pinned
    db.session.commit()
    return redirect(url_for('admin.admin_threads', board_id=request.args.get('board_id')))

@admin_bp.route('/threads/toggle_lock/<int:thread_id>', methods=['POST'])
@admin_required
@csrf_protect('toggle_lock')
def admin_toggle_lock(thread_id):
    thread = Thread.query.get_or_404(thread_id)
    thread.is_locked = not thread.is_locked
    db.session.commit()
    return redirect(url_for('admin.admin_threads', board_id=request.args.get('board_id')))

@admin_bp.route('/threads/delete/<int:thread_id>', methods=['POST'])
@admin_required
@csrf_protect('delete_thread')
def admin_delete_thread(thread_id):
    thread = Thread.query.get_or_404(thread_id)
    for post in thread.posts:
        for pf in post.files:
            try:
                os.remove(os.path.join(current_app.config['UPLOAD_FOLDER'], pf.file_path))
                os.remove(os.path.join(current_app.config['UPLOAD_FOLDER'], 'thumbs', pf.thumb_path))
            except:
                pass
    db.session.delete(thread)
    db.session.commit()
    return redirect(url_for('admin.admin_threads', board_id=request.args.get('board_id')))

@admin_bp.route('/threads/bulk', methods=['POST'])
@admin_required
@csrf_protect('bulk_threads')
def admin_bulk_threads():
    action = request.form.get('action')
    thread_ids = request.form.getlist('thread_ids')
    if not thread_ids:
        return redirect(url_for('admin.admin_threads'))
    threads = Thread.query.filter(Thread.id.in_(thread_ids)).all()
    if action == 'delete':
        for t in threads:
            for post in t.posts:
                for pf in post.files:
                    try:
                        os.remove(os.path.join(current_app.config['UPLOAD_FOLDER'], pf.file_path))
                        os.remove(os.path.join(current_app.config['UPLOAD_FOLDER'], 'thumbs', pf.thumb_path))
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
    return redirect(url_for('admin.admin_threads', board_id=request.args.get('board_id')))

@admin_bp.route('/thread/<int:thread_id>')
@admin_required
def admin_thread_detail(thread_id):
    thread = Thread.query.get_or_404(thread_id)
    posts = thread.posts.order_by(Post.created_at.asc()).all()
    return render_template('admin/thread_detail.html', thread=thread, posts=posts)

@admin_bp.route('/post/delete/<int:post_id>', methods=['POST'])
@admin_required
@csrf_protect('delete_post')
def admin_delete_post(post_id):
    post = Post.query.get_or_404(post_id)
    thread = post.thread
    for pf in post.files:
        try:
            os.remove(os.path.join(current_app.config['UPLOAD_FOLDER'], pf.file_path))
            os.remove(os.path.join(current_app.config['UPLOAD_FOLDER'], 'thumbs', pf.thumb_path))
        except:
            pass
    PostFTS.query.filter_by(post_id=post.id).delete()
    db.session.delete(post)
    db.session.commit()
    if thread.posts.count() == 0:
        db.session.delete(thread)
        db.session.commit()
        return redirect(url_for('admin.admin_threads'))
    return redirect(url_for('admin.admin_thread_detail', thread_id=thread.id))

@admin_bp.route('/files')
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

@admin_bp.route('/files/delete/<int:file_id>', methods=['POST'])
@admin_required
@csrf_protect('delete_file')
def admin_delete_file(file_id):
    pf = PostFile.query.get_or_404(file_id)
    try:
        os.remove(os.path.join(current_app.config['UPLOAD_FOLDER'], pf.file_path))
        os.remove(os.path.join(current_app.config['UPLOAD_FOLDER'], 'thumbs', pf.thumb_path))
    except:
        pass
    db.session.delete(pf)
    db.session.commit()
    flash('Файл удалён', 'info')
    return redirect(url_for('admin.admin_files', board_id=request.args.get('board_id')))

@admin_bp.route('/files/orphaned')
@admin_required
def admin_orphaned_files():
    orphaned = []
    for root, dirs, files in os.walk(current_app.config['UPLOAD_FOLDER']):
        for f in files:
            if '_thumb' in f:
                continue
            full_path = os.path.join(root, f)
            rel_path = os.path.relpath(full_path, current_app.config['UPLOAD_FOLDER'])
            exists = PostFile.query.filter_by(file_path=rel_path).first()
            if not exists:
                size = os.path.getsize(full_path)
                orphaned.append((rel_path, size))
    return render_template('admin/orphaned.html', orphaned=orphaned)

@admin_bp.route('/files/cleanup', methods=['POST'])
@admin_required
@csrf_protect('cleanup_files')
def admin_cleanup_files():
    action = request.form.get('action')
    if action == 'orphaned':
        for root, dirs, files in os.walk(current_app.config['UPLOAD_FOLDER']):
            for f in files:
                if '_thumb' in f:
                    continue
                full_path = os.path.join(root, f)
                rel_path = os.path.relpath(full_path, current_app.config['UPLOAD_FOLDER'])
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
        threshold = datetime.now(timezone.utc) - timedelta(days=30)
        old_threads = Thread.query.filter(Thread.bumped_at < threshold).all()
        for t in old_threads:
            for p in t.posts:
                for pf in p.files:
                    try:
                        os.remove(os.path.join(current_app.config['UPLOAD_FOLDER'], pf.file_path))
                        os.remove(os.path.join(current_app.config['UPLOAD_FOLDER'], 'thumbs', pf.thumb_path))
                    except:
                        pass
            db.session.delete(t)
        db.session.commit()
        flash(f'Удалено старых тредов: {len(old_threads)}', 'success')
    return redirect(url_for('admin.admin_files'))

@admin_bp.route('/bans')
@admin_required
def admin_bans():
    bans = Ban.query.order_by(Ban.created_at.desc()).all()
    return render_template('admin/bans.html', bans=bans)

@admin_bp.route('/bans/add', methods=['POST'])
@admin_required
@csrf_protect('add_ban')
def admin_add_ban():
    ip = request.form['ip_pattern']
    reason = request.form.get('reason', '')
    expires_days = request.form.get('expires_days', type=int)
    expires = datetime.now(timezone.utc) + timedelta(days=expires_days) if expires_days else None
    ban = Ban(ip_pattern=ip, reason=reason, expires_at=expires)
    db.session.add(ban)
    db.session.commit()
    flash(f'IP {ip} забанен', 'success')
    return redirect(url_for('admin.admin_bans'))

@admin_bp.route('/bans/toggle/<int:ban_id>', methods=['POST'])
@admin_required
@csrf_protect('toggle_ban')
def admin_toggle_ban(ban_id):
    ban = Ban.query.get_or_404(ban_id)
    ban.active = not ban.active
    db.session.commit()
    return redirect(url_for('admin.admin_bans'))

@admin_bp.route('/bans/delete/<int:ban_id>', methods=['POST'])
@admin_required
@csrf_protect('delete_ban')
def admin_delete_ban(ban_id):
    ban = Ban.query.get_or_404(ban_id)
    db.session.delete(ban)
    db.session.commit()
    flash('Бан удалён', 'success')
    return redirect(url_for('admin.admin_bans'))

@admin_bp.route('/filters')
@admin_required
def admin_filters():
    filters = WordFilter.query.order_by(WordFilter.id.desc()).all()
    return render_template('admin/filters.html', filters=filters)

@admin_bp.route('/filters/add', methods=['POST'])
@admin_required
@csrf_protect('add_filter')
def admin_add_filter():
    pattern = request.form['pattern']
    replacement = request.form.get('replacement', '[CENSORED]')
    is_regex = 'is_regex' in request.form
    action = request.form['action']
    wf = WordFilter(pattern=pattern, replacement=replacement, is_regex=is_regex, action=action)
    db.session.add(wf)
    db.session.commit()
    flash('Фильтр добавлен', 'success')
    return redirect(url_for('admin.admin_filters'))

@admin_bp.route('/filters/toggle/<int:filter_id>', methods=['POST'])
@admin_required
@csrf_protect('toggle_filter')
def admin_toggle_filter(filter_id):
    wf = WordFilter.query.get_or_404(filter_id)
    wf.active = not wf.active
    db.session.commit()
    return redirect(url_for('admin.admin_filters'))

@admin_bp.route('/filters/delete/<int:filter_id>', methods=['POST'])
@admin_required
@csrf_protect('delete_filter')
def admin_delete_filter(filter_id):
    wf = WordFilter.query.get_or_404(filter_id)
    db.session.delete(wf)
    db.session.commit()
    flash('Фильтр удалён', 'success')
    return redirect(url_for('admin.admin_filters'))

@admin_bp.route('/settings', methods=['GET', 'POST'])
@admin_required
@csrf_protect('save_settings')
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
        save_setting('MAX_VIDEO_DURATION', request.form.get('max_video_duration', '180'))
        save_setting('MAX_VIDEO_SIZE', int(request.form.get('max_video_size', 50)) * 1024 * 1024)
        save_setting('MAX_AUDIO_DURATION', request.form.get('max_audio_duration', '600'))
        save_setting('MAX_AUDIO_SIZE', int(request.form.get('max_audio_size', 30)) * 1024 * 1024)
        save_setting('WEBP_CONVERT_ENABLED', 'webp_convert_enabled' in request.form)
        save_setting('STEALTH_TRIM', 'stealth_trim' in request.form)
        save_setting('RADIO_ENABLED', 'radio_enabled' in request.form)
        save_setting('RADIO_BITRATE', request.form.get('radio_bitrate', '128k'))
        flash('Настройки сохранены', 'success')
        return redirect(url_for('admin.admin_settings'))

    ctx = {
        'captcha_enabled': current_app.config.get('CAPTCHA_ENABLED', False),
        'stats_show_ips': current_app.config.get('STATS_SHOW_IPS', False),
        'board_closed': current_app.config.get('BOARD_CLOSED', False),
        'auto_refresh_enabled': current_app.config.get('AUTO_REFRESH_ENABLED', True),
        'auto_refresh_interval': current_app.config.get('AUTO_REFRESH_INTERVAL', 30),
        'rate_limit_seconds': current_app.config.get('RATE_LIMIT_SECONDS', 30),
        'header_html': current_app.config.get('HEADER_HTML', ''),
        'footer_html': current_app.config.get('FOOTER_HTML', ''),
        'site_title': current_app.config.get('SITE_TITLE', 'Имиджборда'),
        'threads_per_page': current_app.config.get('THREADS_PER_PAGE', 50),
        'posts_per_page': current_app.config.get('POSTS_PER_PAGE', 50),
        'max_files': current_app.config.get('MAX_FILES', 4),
        'allowed_extensions': current_app.config.get('ALLOWED_EXTENSIONS', ['jpg','jpeg','png','gif']),
        'announcement_html': current_app.config.get('ANNOUNCEMENT_HTML', ''),
        'max_content_length': int(current_app.config.get('MAX_CONTENT_LENGTH') or 10*1024*1024) // (1024 * 1024),
        'max_image_dimension': current_app.config.get('MAX_IMAGE_DIMENSION', 5000),
        'max_video_duration': current_app.config.get('MAX_VIDEO_DURATION', 180),
        'max_video_size': current_app.config.get('MAX_VIDEO_SIZE', 50 * 1024 * 1024) // (1024 * 1024),
        'max_audio_duration': current_app.config.get('MAX_AUDIO_DURATION', 600),
        'max_audio_size': current_app.config.get('MAX_AUDIO_SIZE', 30 * 1024 * 1024) // (1024 * 1024),
        'webp_convert_enabled': current_app.config.get('WEBP_CONVERT_ENABLED', True),
        'stealth_trim': current_app.config.get('STEALTH_TRIM', True),
        'radio_enabled': current_app.config.get('RADIO_ENABLED', False),
        'radio_bitrate': current_app.config.get('RADIO_BITRATE', '128k'),
    }
    return render_template('admin/settings.html', **ctx)

@admin_bp.route('/stats')
@admin_required
def admin_stats():
    total_threads = Thread.query.count()
    total_posts = Post.query.count()
    total_files = PostFile.query.count()
    total_boards = Board.query.count()

    today = datetime.now(timezone.utc).date()
    daily_posts = []
    daily_threads = []
    for i in range(7):
        day = today - timedelta(days=i)
        start = datetime(day.year, day.month, day.day, tzinfo=timezone.utc)
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

    db_path = current_app.config['SQLALCHEMY_DATABASE_URI'].replace('sqlite:///', '')
    db_size_bytes = os.path.getsize(db_path) if os.path.exists(db_path) else 0
    db_size_mb = db_size_bytes / (1024 * 1024)

    upload_folder = current_app.config['UPLOAD_FOLDER']
    disk_usage = shutil.disk_usage(upload_folder)
    total_disk_gb = disk_usage.total / (1024**3)
    used_disk_gb = disk_usage.used / (1024**3)
    free_disk_gb = disk_usage.free / (1024**3)

    show_ips = current_app.config.get('STATS_SHOW_IPS', False)
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
