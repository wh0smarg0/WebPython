from . import db, login_manager # Імпорт бази та менеджера з __init__.py
from datetime import datetime
from flask_login import UserMixin
from werkzeug.security import generate_password_hash, check_password_hash

# 1. Завантажувач користувача (має бути тут або в __init__.py) [cite: 241, 859]
@login_manager.user_loader
def load_user(user_id):
    return db.session.get(User, int(user_id))

# 2. Твої моделі платників та нарахувань
class Taxpayer(db.Model):
    __tablename__ = 'taxpayers'
    id = db.Column(db.Integer, primary_key=True)
    full_name = db.Column(db.String(255), nullable=False)
    tin = db.Column(db.String(10), unique=True, nullable=False)

    # НОВЕ ПОЛЕ: Зв'язок із користувачем
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=True)

    records = db.relationship('TaxRecord', backref='taxpayer', lazy=True, cascade="all, delete-orphan")

class TaxType(db.Model):
    __tablename__ = 'tax_types'
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    rate = db.Column(db.Float, nullable=False)
    records = db.relationship('TaxRecord', backref='tax_type', lazy=True)

class TaxRecord(db.Model):
    __tablename__ = 'tax_records'
    id = db.Column(db.Integer, primary_key=True)
    taxpayer_id = db.Column(db.Integer, db.ForeignKey('taxpayers.id'), nullable=False)
    tax_type_id = db.Column(db.Integer, db.ForeignKey('tax_types.id'), nullable=False)
    amount = db.Column(db.Float, nullable=False)
    is_paid = db.Column(db.Boolean, default=False)
    paid_at = db.Column(db.DateTime, nullable=True)

# 3. Модель користувача з методами безпеки [cite: 40-48, 107-110, 237]
class User(db.Model, UserMixin):
    __tablename__ = 'users'
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100))
    username = db.Column(db.String(50), nullable=False, unique=True)
    email = db.Column(db.String(100), nullable=False, unique=True)
    password_hash = db.Column(db.String(256), nullable=False)
    created_on = db.Column(db.DateTime(), default=datetime.utcnow)
    updated_on = db.Column(db.DateTime(), default=datetime.utcnow, onupdate=datetime.utcnow)

    def set_password(self, password):
        # Хешування пароля перед збереженням [cite: 83, 108]
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        # Перевірка введеного пароля з хешем у базі [cite: 83, 110]
        return check_password_hash(self.password_hash, password)