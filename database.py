import psycopg2
from psycopg2.extras import RealDictCursor

# Налаштування підключення до PostgreSQL
DB_CONFIG = {
    "dbname": "taxes_db",
    "user": "postgres",
    "password": "masterkey",
    "host": "127.0.0.1",
    "port": "5432"
}

def get_db_connection():
    conn = psycopg2.connect(**DB_CONFIG)
    return conn

def init_db():
    """Створення таблиць при завантаженні застосунку"""
    conn = get_db_connection()
    with conn.cursor() as cur:
        # Створення таблиці Платників
        cur.execute("""
            CREATE TABLE IF NOT EXISTS taxpayers (
                id SERIAL PRIMARY KEY,
                full_name VARCHAR(255) NOT NULL,
                tin VARCHAR(10) UNIQUE NOT NULL
            );
        """)
        # Створення таблиці Типів податків
        cur.execute("""
            CREATE TABLE IF NOT EXISTS tax_types (
                id SERIAL PRIMARY KEY,
                name VARCHAR(100) NOT NULL,
                rate FLOAT NOT NULL
            );
        """)
        # Створення таблиці Нарахувань
        cur.execute("""
            CREATE TABLE IF NOT EXISTS tax_records (
                id SERIAL PRIMARY KEY,
                amount FLOAT NOT NULL,
                taxpayer_id INTEGER REFERENCES taxpayers(id) ON DELETE CASCADE,
                tax_type_id INTEGER REFERENCES tax_types(id)
            );
        """)
        conn.commit()
    conn.close()
