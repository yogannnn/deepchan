from flask import Blueprint, render_template, redirect, url_for, request, abort, flash, Response, current_app
from models import db, RadioTrack
from utils import (
    get_file_hash, get_media_duration, convert_for_radio,
    verify_csrf_token
)
import os
import secrets
import subprocess
import glob
import random
from functools import wraps

radio_bp = Blueprint('radio', __name__, url_prefix='')

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

@radio_bp.route('/radio')
def radio_page():
    if not current_app.config.get('RADIO_ENABLED', False):
        return render_template('radio_disabled.html')
    tracks = RadioTrack.query.filter_by(approved=True).order_by(RadioTrack.created_at.desc()).all()
    return render_template('radio.html', tracks=tracks)

@radio_bp.route('/radio-stream')
def radio_stream():
    radio_folder = current_app.config.get('RADIO_FOLDER', '/opt/deepchan/static/radio')
    playlist_dir = os.path.join(radio_folder, 'playlist')
    
    def generate():
        tracks = glob.glob(os.path.join(playlist_dir, '*.mp3'))
        random.shuffle(tracks)
        if not tracks:
            yield b''
            return

        track_index = 0
        while True:
            track_path = tracks[track_index]
            with open(track_path, 'rb') as f:
                while chunk := f.read(8192):
                    yield chunk
            track_index = (track_index + 1) % len(tracks)

    return Response(generate(), mimetype='audio/mpeg')

@radio_bp.route('/admin/radio')
@admin_required
def admin_radio():
    status = request.args.get('status', 'pending')
    query = RadioTrack.query
    if status == 'approved':
        query = query.filter(RadioTrack.approved == True)
    elif status == 'rejected':
        query = query.filter(RadioTrack.approved == False, RadioTrack.post_file_id != None)
    else:
        query = query.filter(RadioTrack.approved == False)
    tracks = query.order_by(RadioTrack.created_at.desc()).all()
    return render_template('admin/radio.html', tracks=tracks, status=status)

@radio_bp.route('/admin/radio/upload', methods=['POST'])
@admin_required
@csrf_protect('upload_radio')
def admin_radio_upload():
    if 'file' not in request.files:
        flash('Файл не выбран', 'error')
        return redirect(url_for('radio.admin_radio'))
    f = request.files['file']
    if f.filename == '':
        flash('Файл не выбран', 'error')
        return redirect(url_for('radio.admin_radio'))
    ext = f.filename.rsplit('.', 1)[-1].lower()
    if ext not in ['mp3', 'ogg', 'flac', 'wav', 'm4a']:
        flash('Недопустимый формат', 'error')
        return redirect(url_for('radio.admin_radio'))
    tmp_path = os.path.join(current_app.config['UPLOAD_FOLDER'], secrets.token_hex(16) + '.' + ext)
    f.save(tmp_path)
    file_hash = get_file_hash(tmp_path)
    if RadioTrack.query.filter_by(original_hash=file_hash).first():
        os.remove(tmp_path)
        flash('Трек уже существует в базе радио', 'error')
        return redirect(url_for('radio.admin_radio'))
    track = RadioTrack(
        artist=request.form.get('artist', 'Unknown'),
        title=request.form.get('title', 'Untitled'),
        original_hash=file_hash,
        duration=get_media_duration(tmp_path),
        approved=False
    )
    db.session.add(track)
    db.session.commit()
    pending_dir = os.path.join(current_app.config.get('RADIO_FOLDER', '/opt/deepchan/static/radio'), 'pending')
    os.makedirs(pending_dir, exist_ok=True)
    pending_path = os.path.join(pending_dir, f'radio_pending_{track.id}.{ext}')
    os.rename(tmp_path, pending_path)
    track.file_path = pending_path
    db.session.commit()
    flash('Трек добавлен на модерацию', 'success')
    return redirect(url_for('radio.admin_radio'))

@radio_bp.route('/admin/radio/approve/<int:track_id>', methods=['POST'])
@admin_required
@csrf_protect('approve_radio')
def admin_radio_approve(track_id):
    track = RadioTrack.query.get_or_404(track_id)
    if track.approved:
        flash('Трек уже одобрен', 'error')
        return redirect(url_for('radio.admin_radio'))
    playlist_dir = os.path.join(current_app.config.get('RADIO_FOLDER', '/opt/deepchan/static/radio'), 'playlist')
    os.makedirs(playlist_dir, exist_ok=True)
    output_path = os.path.join(playlist_dir, f'radio_{track.id}.mp3')
    input_path = os.path.join(current_app.config['UPLOAD_FOLDER'], track.file_path) if not os.path.isabs(track.file_path) else track.file_path
    try:
        convert_for_radio(input_path, output_path, track.artist, track.title, current_app.config.get('RADIO_BITRATE', '128k'))
    except Exception as e:
        flash(f'Ошибка конвертации: {str(e)}', 'error')
        return redirect(url_for('radio.admin_radio'))
    if os.path.exists(track.file_path):
        os.remove(track.file_path)
    track.file_path = output_path
    track.approved = True
    db.session.commit()
    flash('Трек одобрен и добавлен в плейлист', 'success')
    return redirect(url_for('radio.admin_radio'))

@radio_bp.route('/admin/radio/reject/<int:track_id>', methods=['POST'])
@admin_required
@csrf_protect('reject_radio')
def admin_radio_reject(track_id):
    track = RadioTrack.query.get_or_404(track_id)
    if track.approved:
        flash('Нельзя отклонить уже одобренный трек', 'error')
        return redirect(url_for('radio.admin_radio'))
    if os.path.exists(track.file_path):
        os.remove(track.file_path)
    track.approved = False
    track.file_path = None
    db.session.commit()
    flash('Трек отклонён', 'success')
    return redirect(url_for('radio.admin_radio'))

@radio_bp.route('/admin/radio/edit/<int:track_id>', methods=['GET', 'POST'])
@admin_required
@csrf_protect('edit_radio')
def admin_radio_edit(track_id):
    track = RadioTrack.query.get_or_404(track_id)
    if request.method == 'POST':
        track.artist = request.form.get('artist', '')
        track.title = request.form.get('title', '')
        db.session.commit()
        flash('Метаданные обновлены', 'success')
        return redirect(url_for('radio.admin_radio'))
    return render_template('admin/radio_edit.html', track=track)

@radio_bp.route('/admin/radio/delete/<int:track_id>', methods=['POST'])
@admin_required
@csrf_protect('delete_radio')
def admin_radio_delete(track_id):
    track = RadioTrack.query.get_or_404(track_id)
    if track.file_path and os.path.exists(track.file_path):
        os.remove(track.file_path)
    db.session.delete(track)
    db.session.commit()
    flash('Трек удалён', 'success')
    return redirect(url_for('radio.admin_radio'))

@radio_bp.route('/admin/radio/toggle', methods=['POST'])
@admin_required
@csrf_protect('toggle_radio')
def admin_radio_toggle():
    current = current_app.config.get('RADIO_ENABLED', False)
    from models import Setting
    s = db.session.get(Setting, 'RADIO_ENABLED')
    if not s:
        s = Setting(key='RADIO_ENABLED')
    s.value = str(not current)
    db.session.add(s)
    db.session.commit()
    current_app.config['RADIO_ENABLED'] = not current
    flash(f'Радио {"включено" if not current else "выключено"}', 'success')
    return redirect(url_for('radio.admin_radio'))
