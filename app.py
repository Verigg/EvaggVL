from flask import Flask, render_template, request, redirect, url_for, jsonify, flash
from flask_login import LoginManager, login_user, logout_user, login_required, current_user
from models import db, User, Event, Favorite, Invitation
from datetime import datetime

app = Flask(__name__)
app.config['SECRET_KEY'] = 'your-secret-key-here'
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///events.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db.init_app(app)
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login'

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

def init_db():
    with app.app_context():
        db.create_all()
        if not Event.query.first():
            events = [
                Event(
                    title="Лекция по искусственному интеллекту",
                    description="Современные тенденции в развитии ИИ",
                    category="лекция",
                    date=datetime(2024, 2, 15, 19, 0),
                    location="Москва, ул. Тверская, 1",
                    organizer="Технологический университет"
                ),
                Event(
                    title="Мастер-класс по веб-разработке",
                    description="Практическое занятие по Flask и Django",
                    category="мастер-класс",
                    date=datetime(2024, 2, 20, 18, 0),
                    location="Онлайн",
                    organizer="Школа программирования"
                ),
                Event(
                    title="Музыкальный фестиваль",
                    description="Ежегодный фестиваль современной музыки",
                    category="фестиваль",
                    date=datetime(2024, 3, 1, 12, 0),
                    location="Парк Горького",
                    organizer="Городской культурный центр"
                )
            ]
            db.session.bulk_save_objects(events)
            db.session.commit()

@app.route('/')
def index():
    events = Event.query.order_by(Event.date.asc()).limit(6).all()
    return render_template('index.html', events=events)

@app.route('/events')
def events():
    category = request.args.get('category', '')
    search = request.args.get('search', '')
    
    query = Event.query
    
    if category:
        query = query.filter(Event.category == category)
    if search:
        query = query.filter(Event.title.ilike(f'%{search}%'))
    
    events = query.order_by(Event.date.asc()).all()
    return render_template('events.html', events=events, category=category, search=search)

@app.route('/events/<int:event_id>')
def event_detail(event_id):
    event = Event.query.get_or_404(event_id)
    is_favorite = False
    if current_user.is_authenticated:
        is_favorite = Favorite.query.filter_by(
            user_id=current_user.id, 
            event_id=event_id
        ).first() is not None
    return render_template('event_detail.html', event=event, is_favorite=is_favorite)

@app.route('/recommendations')
@login_required
def recommendations():
    user_preferences = current_user.preferences or []
    
    if user_preferences:
        recommended_events = Event.query.filter(
            Event.category.in_(user_preferences)
        ).order_by(Event.date.asc()).limit(10).all()
    else:
        recommended_events = Event.query.order_by(Event.date.asc()).limit(6).all()
    
    return render_template('events.html', events=recommended_events, title="Рекомендации")

@app.route('/favorite/<int:event_id>', methods=['POST'])
@login_required
def toggle_favorite(event_id):
    favorite = Favorite.query.filter_by(
        user_id=current_user.id, 
        event_id=event_id
    ).first()
    
    if favorite:
        db.session.delete(favorite)
        db.session.commit()
        return jsonify({'status': 'removed'})
    else:
        favorite = Favorite(user_id=current_user.id, event_id=event_id)
        db.session.add(favorite)
        db.session.commit()
        return jsonify({'status': 'added'})

@app.route('/favorites')
@login_required
def favorites():
    favorite_events = Event.query.join(Favorite).filter(
        Favorite.user_id == current_user.id
    ).all()
    return render_template('events.html', events=favorite_events, title="Избранное")

@app.route('/invite/<int:event_id>', methods=['POST'])
@login_required
def invite_friend(event_id):
    friend_email = request.form.get('friend_email')
    message = request.form.get('message', '')
    
    invitation = Invitation(
        user_id=current_user.id,
        friend_email=friend_email,
        event_id=event_id,
        message=message
    )
    db.session.add(invitation)
    db.session.commit()
    
    flash('Приглашение отправлено!', 'success')
    return redirect(url_for('event_detail', event_id=event_id))

@app.route('/profile', methods=['GET', 'POST'])
@login_required
def profile():
    if request.method == 'POST':
        preferences = request.form.getlist('preferences')
        current_user.preferences = preferences
        db.session.commit()
        flash('Настройки сохранены!', 'success')
    
    return render_template('profile.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        action = request.form.get('action')
        
        # Регистрация
        if action == 'register':
            email = request.form.get('email')
            
            if not email:
                flash('Email обязателен для регистрации', 'error')
                return render_template('login.html')
            
            if User.query.filter_by(username=username).first():
                flash('Имя пользователя уже занято', 'error')
                return render_template('login.html')
            
            if User.query.filter_by(email=email).first():
                flash('Email уже зарегистрирован', 'error')
                return render_template('login.html')
            
            user = User(username=username, email=email)
            user.set_password(password)
            db.session.add(user)
            db.session.commit()
            
            login_user(user)
            flash('Регистрация успешна!', 'success')
            return redirect(url_for('index'))
        
        # Вход
        elif action == 'login':
            user = User.query.filter_by(username=username).first()
            
            if user and user.check_password(password):
                login_user(user)
                return redirect(url_for('index'))
            else:
                flash('Неверное имя пользователя или пароль', 'error')
    
    return render_template('login.html')

@app.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect(url_for('index'))

if __name__ == '__main__':
    init_db()
    app.run(debug=True)