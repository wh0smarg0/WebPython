import os

# Визначення кореневої папки проєкту
app_dir = os.path.abspath(os.path.dirname(__file__))

class BaseConfig:
    """Базові налаштування, спільні для всіх середовищ"""
    SECRET_KEY = os.environ.get('SECRET_KEY') or 'your_very_secret_key_123'
    SQLALCHEMY_TRACK_MODIFICATIONS = False

    # Налаштування Flask-Mail
    MAIL_SERVER = 'smtp.googlemail.com'
    MAIL_PORT = 587
    MAIL_USE_TLS = True
    MAIL_USERNAME = 'wh0smarg0.s@gmail.com'
    MAIL_PASSWORD = 'lnrqylggzokegrkh'
    MAIL_DEFAULT_SENDER = os.environ.get('Електронний кабінет платника', 'wh0smarg0.s@gmail.com')

class DevelopmentConfig(BaseConfig):
    """Налаштування для середовища розробки"""
    DEBUG = True
    SQLALCHEMY_DATABASE_URI = os.environ.get('DEVELOPMENT_DATABASE_URI') or \
        'postgresql+psycopg2://postgres:masterkey@127.0.0.1:5432/taxes_db'

class TestingConfig(BaseConfig):
    """Налаштування для середовища тестування"""
    DEBUG = True
    SQLALCHEMY_DATABASE_URI = os.environ.get('TESTING_DATABASE_URI') or \
        'postgresql+psycopg2://postgres:masterkey@127.0.0.1:5432/taxes_db_test'

class ProductionConfig(BaseConfig):
    """Налаштування для робочого режиму"""
    DEBUG = False
    # У робочому режимі дані беруться зі змінних середовища
    SQLALCHEMY_DATABASE_URI = os.environ.get('PRODUCTION_DATABASE_URI') or \
        'postgresql+psycopg2://admin:password@localhost/prod_db'