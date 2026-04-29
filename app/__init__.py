from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate
from flask_login import LoginManager
import os
from flask_mail import Mail

# Екземпляри розширень глобально
db = SQLAlchemy()
migrate = Migrate()
login_manager = LoginManager()
mail = Mail()


def create_app():
    """Фабрика для створення та налаштування екземпляра додатка"""
    app = Flask(__name__)

    # Завантаження конфігурації з об'єкта
    app.config.from_object(os.environ.get('FLASK_ENV') or 'config.DevelopmentConfig')

    # Ініціалізація розширень для створеного додатка
    db.init_app(app)
    migrate.init_app(app, db)
    login_manager.init_app(app)
    mail.init_app(app)

    # Налаштування перенаправлення для неавторизованих користувачів
    login_manager.login_view = 'main.login'
    login_manager.login_message = "Будь ласка, увійдіть, щоб отримати доступ до цієї сторінки."

    with app.app_context():
        # Реєстрація Blueprint
        from .views import main
        app.register_blueprint(main)

        # Імпорт моделей для роботи з базою даних
        from . import models

        # Функція для завантаження користувача з бази даних за ID
        @login_manager.user_loader
        def load_user(user_id):
            return db.session.get(models.User, int(user_id))

    return app