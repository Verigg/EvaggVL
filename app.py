from flask import Flask, render_template, request, redirect, url_for, jsonify, flash, abort
from flask_login import LoginManager, login_user, logout_user, login_required, current_user
from models import db, User, Event, Favorite, Invitation
from datetime import datetime
from functools import wraps 

app = Flask(__name__)
app.config['SECRET_KEY'] = 'your-secret-key-here'
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///events.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db.init_app(app)
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login'

def admin_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not current_user.is_authenticated or current_user.username != 'admin':
            abort(403)
        return f(*args, **kwargs)
    return decorated_function

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

def init_db():
    with app.app_context():
        db.create_all()

        admin = User.query.filter_by(username='admin').first()
        if not admin:
            admin = User(username='admin', email='admin@example.com')
            admin.set_password('admin123')  # CHANGE PASSWORD
            db.session.add(admin)
        
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
        
        # Registration
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
        
        # Login
        elif action == 'login':
            user = User.query.filter_by(username=username).first()
            
            if user and user.check_password(password):
                login_user(user)
                return redirect(url_for('index'))
            else:
                flash('Неверное имя пользователя или пароль', 'error')
    
    return render_template('login.html')

@app.route('/admin')
@login_required
@admin_required
def admin_dashboard():
    stats = {
        'total_events': Event.query.count(),
        'total_users': User.query.count(),
        'total_favorites': Favorite.query.count(),
        'total_invitations': Invitation.query.count(),
        'recent_events': Event.query.order_by(Event.created_at.desc()).limit(5).all(),
        'recent_users': User.query.order_by(User.id.desc()).limit(5).all()
    }
    return render_template('admin/dashboard.html', stats=stats)

@app.route('/admin/events')
@login_required
@admin_required
def admin_events():
    page = request.args.get('page', 1, type=int)
    per_page = 10
    
    events = Event.query.order_by(Event.date.desc()).paginate(
        page=page, per_page=per_page, error_out=False
    )
    
    return render_template('admin/events.html', events=events)

@app.route('/admin/events/new', methods=['GET', 'POST'])
@login_required
@admin_required
def admin_create_event():
    if request.method == 'POST':
        try:
            event = Event(
                title=request.form['title'],
                description=request.form['description'],
                category=request.form['category'],
                date=datetime.strptime(request.form['date'], '%Y-%m-%dT%H:%M'),
                location=request.form['location'],
                organizer=request.form['organizer'],
                image_url=request.form.get('image_url') or None
            )
            db.session.add(event)
            db.session.commit()
            flash('Мероприятие успешно создано!', 'success')
            return redirect(url_for('admin_events'))
        except Exception as e:
            db.session.rollback()
            flash(f'Ошибка при создании мероприятия: {str(e)}', 'error')
    
    categories = ['лекция', 'мастер-класс', 'фестиваль', 'конференция', 'выставка', 'концерт']
    return render_template('admin/event_form.html', categories=categories, event=None)

@app.route('/admin/events/<int:event_id>/edit', methods=['GET', 'POST'])
@login_required
@admin_required
def admin_edit_event(event_id):
    event = Event.query.get_or_404(event_id)
    
    if request.method == 'POST':
        try:
            event.title = request.form['title']
            event.description = request.form['description']
            event.category = request.form['category']
            event.date = datetime.strptime(request.form['date'], '%Y-%m-%dT%H:%M')
            event.location = request.form['location']
            event.organizer = request.form['organizer']
            event.image_url = request.form.get('image_url') or None
            
            db.session.commit()
            flash('Мероприятие успешно обновлено!', 'success')
            return redirect(url_for('admin_events'))
        except Exception as e:
            db.session.rollback()
            flash(f'Ошибка при обновлении мероприятия: {str(e)}', 'error')
    
    categories = ['лекция', 'мастер-класс', 'фестиваль', 'конференция', 'выставка', 'концерт']
    return render_template('admin/event_form.html', event=event, categories=categories)

@app.route('/admin/events/<int:event_id>/delete', methods=['POST'])
@login_required
@admin_required
def admin_delete_event(event_id):
    event = Event.query.get_or_404(event_id)
    
    try:
        Favorite.query.filter_by(event_id=event_id).delete()
        Invitation.query.filter_by(event_id=event_id).delete()
        
        db.session.delete(event)
        db.session.commit()
        flash('Мероприятие успешно удалено!', 'success')
    except Exception as e:
        db.session.rollback()
        flash(f'Ошибка при удалении мероприятия: {str(e)}', 'error')
    
    return redirect(url_for('admin_events'))

@app.route('/admin/users')
@login_required
@admin_required
def admin_users():
    page = request.args.get('page', 1, type=int)
    per_page = 15
    
    users = User.query.order_by(User.id.desc()).paginate(
        page=page, per_page=per_page, error_out=False
    )
    
    return render_template('admin/users.html', users=users)

@app.route('/admin/users/<int:user_id>/toggle', methods=['POST'])
@login_required
@admin_required
def admin_toggle_user(user_id):
    user = User.query.get_or_404(user_id)
    
    if hasattr(user, 'is_active'):
        user.is_active = not user.is_active
        db.session.commit()
        status = "разблокирован" if user.is_active else "заблокирован"
        flash(f'Пользователь {user.username} {status}!', 'success')
    
    return redirect(url_for('admin_users'))

@app.route('/admin/stats')
@login_required
@admin_required
def admin_stats():
    category_stats = db.session.query(
        Event.category,
        db.func.count(Event.id).label('count')
    ).group_by(Event.category).all()
    
    month_stats = db.session.query(
        db.func.strftime('%Y-%m', Event.date).label('month'),
        db.func.count(Event.id).label('count')
    ).group_by('month').order_by('month').all()
    
    return render_template('admin/stats.html', 
                         category_stats=category_stats,
                         month_stats=month_stats)

@app.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect(url_for('index'))

if __name__ == '__main__':
    init_db()
    app.run(debug=True)