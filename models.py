from flask_sqlalchemy import SQLAlchemy
from flask_login import UserMixin
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime

db = SQLAlchemy()

class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password_hash = db.Column(db.String(120))
    preferences = db.Column(db.JSON, default=list)
    is_active = db.Column(db.Boolean, default=True)  
    created_at = db.Column(db.DateTime, default=datetime.utcnow) 

    favorites = db.relationship('Favorite', backref='user', lazy=True)
    sent_invitations = db.relationship(
        'Invitation',
        foreign_keys='Invitation.sender_id',
        backref='sender',
        lazy=True
    )

    received_invitations = db.relationship(
        'Invitation',
        foreign_keys='Invitation.receiver_id',
        backref='receiver',
        lazy=True
    )

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)

class Event(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(200), nullable=False)
    description = db.Column(db.Text)
    category = db.Column(db.String(50), nullable=False)
    date = db.Column(db.DateTime, nullable=False)
    location = db.Column(db.String(200))
    organizer = db.Column(db.String(100))
    image_url = db.Column(db.String(300))
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    favorites = db.relationship('Favorite', backref='event', lazy=True)

class Favorite(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    event_id = db.Column(db.Integer, db.ForeignKey('event.id'), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

class Invitation(db.Model):
    id = db.Column(db.Integer, primary_key=True)

    sender_id = db.Column(
        db.Integer,
        db.ForeignKey('user.id'),
        nullable=False
    )

    receiver_id = db.Column(
        db.Integer,
        db.ForeignKey('user.id'),
        nullable=True
    )

    friend_email = db.Column(db.String(120), nullable=True)

    event_id = db.Column(
        db.Integer,
        db.ForeignKey('event.id'),
        nullable=False
    )

    message = db.Column(db.Text)
    status = db.Column(db.String(20), default='new')
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    event = db.relationship('Event')
