from flask_sqlalchemy import SQLAlchemy
from datetime import datetime

db = SQLAlchemy()

class Video(db.Model):
    id = db.Column(db.String(50), primary_key=True)  # YouTube video ID
    title = db.Column(db.String(200), nullable=False)
    channel_id = db.Column(db.String(50), nullable=False)
    channel_title = db.Column(db.String(100), nullable=False)
    description = db.Column(db.Text)
    thumbnail_url = db.Column(db.String(200))
    duration = db.Column(db.Integer)  # 초 단위
    published_at = db.Column(db.DateTime)
    view_count = db.Column(db.Integer)
    like_count = db.Column(db.Integer)
    category = db.Column(db.String(50))
    subcategory = db.Column(db.String(50))
    language = db.Column(db.String(20))
    difficulty = db.Column(db.String(20))
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

class SearchHistory(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    query = db.Column(db.String(200), nullable=False)
    category = db.Column(db.String(50))
    subcategory = db.Column(db.String(50))
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password_hash = db.Column(db.String(200), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    last_login = db.Column(db.DateTime)

class UserFavorite(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    video_id = db.Column(db.String(50), db.ForeignKey('video.id'), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    user = db.relationship('User', backref=db.backref('favorites', lazy=True))
    video = db.relationship('Video', backref=db.backref('favorited_by', lazy=True)) 