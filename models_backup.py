from flask_sqlalchemy import SQLAlchemy
from datetime import datetime
from werkzeug.security import generate_password_hash, check_password_hash

db = SQLAlchemy()

class Board(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    short_name = db.Column(db.String(10), unique=True, nullable=False)
    name = db.Column(db.String(80), nullable=False)
    description = db.Column(db.Text)
    threads = db.relationship('Thread', backref='board', lazy='dynamic', cascade='all, delete-orphan')

class Thread(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    board_id = db.Column(db.Integer, db.ForeignKey('board.id'), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    bumped_at = db.Column(db.DateTime, default=datetime.utcnow)
    is_pinned = db.Column(db.Boolean, default=False)
    is_locked = db.Column(db.Boolean, default=False)
    posts = db.relationship('Post', backref='thread', lazy='dynamic', cascade='all, delete-orphan')

class Post(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    thread_id = db.Column(db.Integer, db.ForeignKey('thread.id'), nullable=False)
    name = db.Column(db.String(80), default='Аноним')
    subject = db.Column(db.String(200))
    comment = db.Column(db.Text, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    password_hash = db.Column(db.String(256))
    sage = db.Column(db.Boolean, default=False)
    ip_address = db.Column(db.String(45))
    search_text = db.Column(db.Text)   # новое поле для поиска
    files = db.relationship('PostFile', backref='post', lazy='dynamic', cascade='all, delete-orphan')

class PostFile(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    post_id = db.Column(db.Integer, db.ForeignKey('post.id'), nullable=False)
    file_path = db.Column(db.String(255), nullable=False)
    thumb_path = db.Column(db.String(255), nullable=False)
    file_order = db.Column(db.Integer, default=0)
    file_size = db.Column(db.Integer, default=0)
    md5_hash = db.Column(db.String(32))

class PostFTS(db.Model):
    __tablename__ = 'post_fts'
    post_id = db.Column(db.Integer, primary_key=True)
    board_id = db.Column(db.Integer)
    thread_id = db.Column(db.Integer)
    comment = db.Column(db.Text)
    subject = db.Column(db.String(200))
    name = db.Column(db.String(80))

class Ban(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    ip_pattern = db.Column(db.String(45), nullable=False)
    reason = db.Column(db.String(200))
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    expires_at = db.Column(db.DateTime, nullable=True)
    active = db.Column(db.Boolean, default=True)

class WordFilter(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    pattern = db.Column(db.String(200), nullable=False)
    replacement = db.Column(db.String(200), default='[CENSORED]')
    is_regex = db.Column(db.Boolean, default=False)
    action = db.Column(db.String(20), default='replace')
    active = db.Column(db.Boolean, default=True)

class Setting(db.Model):
    key = db.Column(db.String(100), primary_key=True)
    value = db.Column(db.Text)

def hash_password(password):
    if password:
        return generate_password_hash(password)
    return None

def check_password(password, hashed):
    if password and hashed:
        return check_password_hash(hashed, password)
    return False
