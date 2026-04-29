from . import db, login_manager # Імпорт бази та менеджера з __init__.py
from datetime import datetime
from flask_login import UserMixin
from werkzeug.security import generate_password_hash, check_password_hash

# Завантажувач користувача
@login_manager.user_loader
def load_user(user_id):
    return db.session.get(User, int(user_id))

# Моделі платників та нарахувань
class Taxpayer(db.Model):
    __tablename__ = 'taxpayers'
    id = db.Column(db.Integer, primary_key=True)
    full_name = db.Column(db.String(255), nullable=False)
    tin = db.Column(db.String(10), unique=True, nullable=False)

    # Зв'язок із користувачем
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

# 3. Модель користувача з методами безпеки
class User(db.Model, UserMixin):
    __tablename__ = 'users'
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100))
    username = db.Column(db.String(50), nullable=False, unique=True)
    email = db.Column(db.String(100), nullable=False, unique=True)
    password_hash = db.Column(db.String(256), nullable=False)

    # Флаг для адмін-панелі
    is_admin = db.Column(db.Boolean, default=False)

    created_on = db.Column(db.DateTime(), default=datetime.utcnow)
    updated_on = db.Column(db.DateTime(), default=datetime.utcnow, onupdate=datetime.utcnow)

    # Зв'язок з платником (якщо один юзер = один платник)
    taxpayer_profile = db.relationship('Taxpayer', backref='user', uselist=False)

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)


class AuditLog(db.Model):
    __tablename__ = 'audit_logs'
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=True)
    action = db.Column(db.String(255), nullable = False) # Напр: "Сплатив податок", "Додав платника"
    details = db.Column(db.Text, nullable=True)         # Додаткова інфа (сума, ПІБ платника)
    timestamp = db.Column(db.DateTime, default=db.func.current_timestamp())

    # Зв'язок, щоб знати ім'я того, хто вчинив дію
    actor = db.relationship('User', backref='logs')