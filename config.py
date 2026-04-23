import os

# Визначення кореневої папки проєкту [cite: 670]
app_dir = os.path.abspath(os.path.dirname(__file__))

class BaseConfig:
    """Базові налаштування, спільні для всіх середовищ [cite: 666]"""
    SECRET_KEY = os.environ.get('SECRET_KEY') or 'your_very_secret_key_123'
    SQLALCHEMY_TRACK_MODIFICATIONS = False

class DevelopmentConfig(BaseConfig):
    """Налаштування для середовища розробки [cite: 659, 667]"""
    DEBUG = True
    # Використовуємо твою адресу PostgreSQL [cite: 675, 684]
    SQLALCHEMY_DATABASE_URI = os.environ.get('DEVELOPMENT_DATABASE_URI') or \
        'postgresql+psycopg2://postgres:masterkey@127.0.0.1:5432/taxes_db'

class TestingConfig(BaseConfig):
    """Налаштування для середовища тестування [cite: 660]"""
    DEBUG = True
    SQLALCHEMY_DATABASE_URI = os.environ.get('TESTING_DATABASE_URI') or \
        'postgresql+psycopg2://postgres:masterkey@127.0.0.1:5432/taxes_db_test'

class ProductionConfig(BaseConfig):
    """Налаштування для робочого режиму (Production) [cite: 661]"""
    DEBUG = False
    # У робочому режимі дані зазвичай беруться зі змінних середовища
    SQLALCHEMY_DATABASE_URI = os.environ.get('PRODUCTION_DATABASE_URI') or \
        'postgresql+psycopg2://admin:password@localhost/prod_db'