from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate
from flask_login import LoginManager
import os

# Створюємо екземпляри розширень глобально, але не прив'язуємо до конкретного додатка [cite: 695, 701-703]
db = SQLAlchemy()
migrate = Migrate()
login_manager = LoginManager()


def create_app():
    """Фабрика для створення та налаштування екземпляра додатка [cite: 696-698]"""
    app = Flask(__name__)

    # Завантаження конфігурації з об'єкта (DevelopmentConfig за замовчуванням) [cite: 699, 705]
    app.config.from_object(os.environ.get('FLASK_ENV') or 'config.DevelopmentConfig')

    # Ініціалізація розширень для створеного додатка [cite: 700-703]
    db.init_app(app)
    migrate.init_app(app, db)
    login_manager.init_app(app)

    # Налаштування перенаправлення для неавторизованих користувачів [cite: 365, 367, 703]
    # Оскільки ми використовуємо Blueprint з назвою 'main', вказуємо 'main.login'
    login_manager.login_view = 'main.login'
    # Можна також змінити стандартне повідомлення [cite: 417]
    login_manager.login_message = "Будь ласка, увійдіть, щоб отримати доступ до цієї сторінки."

    with app.app_context():
        # Реєстрація Blueprint (це виправляє помилку циклічного імпорту)
        from .views import main
        app.register_blueprint(main)

        # Імпорт моделей для роботи з базою даних [cite: 704, 707]
        from . import models

        # Функція для завантаження користувача з бази даних за ID [cite: 241-243, 859-861]
        @login_manager.user_loader
        def load_user(user_id):
            return db.session.get(models.User, int(user_id))

    return app