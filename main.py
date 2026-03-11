import psycopg2
from psycopg2.extras import RealDictCursor
from fastapi import FastAPI, Request, Form, Depends
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
import database

app = FastAPI(
    title="Система Обліку Податків (PostgreSQL)",
    description="Лабораторна робота №2. Варіант 12. Платники, податки та нарахування",
    version="2.0.0"
)

templates = Jinja2Templates(directory="templates")

# Ініціалізація БД при старті
database.init_db()


@app.get("/", response_class=HTMLResponse)
async def home(request: Request, role: str = "user"):
    conn = database.get_db_connection()
    cur = conn.cursor(cursor_factory=RealDictCursor)

    try:
        # 1. Отримання всіх платників
        cur.execute("SELECT * FROM taxpayers ORDER BY id ASC")
        taxpayers = cur.fetchall()

        # 2. Отримання Типів податків
        cur.execute("SELECT * FROM tax_types ORDER BY id ASC")
        tax_types = cur.fetchall()

        # 3. Отримання нарахувань з назвами податків та іменами платників
        cur.execute("""
            SELECT 
                tr.id, 
                tr.amount, 
                tp.full_name as taxpayer_name, 
                tp.tin,
                tt.name as tax_name,
                tt.rate as tax_rate
            FROM tax_records tr
            JOIN taxpayers tp ON tr.taxpayer_id = tp.id
            LEFT JOIN tax_types tt ON tr.tax_type_id = tt.id
            ORDER BY tr.id DESC
        """)
        tax_records = cur.fetchall()

        cur.close()
        conn.close()

        return templates.TemplateResponse("index.html", {
            "request": request,
            "taxpayers": taxpayers,
            "tax_records": tax_records,
            "tax_types": tax_types,
            "role": role,
            "name": "Ерік"
        })
    except Exception as e:
        print(f"Помилка БД: {e}")
        return HTMLResponse(content="Помилка підключення до PostgreSQL.", status_code=500)


@app.post("/taxpayer/add")
async def add_taxpayer(full_name: str = Form(...), tin: str = Form(...)):
    conn = database.get_db_connection()
    cur = conn.cursor()
    try:
        # Додавання нового платника через параметризований запит
        cur.execute("INSERT INTO taxpayers (full_name, tin) VALUES (%s, %s)", (full_name, tin))
        conn.commit()
    finally:
        cur.close()
        conn.close()
    return RedirectResponse(url="/?role=admin", status_code=303)


@app.post("/taxpayer/update/{tp_id}")
async def update_taxpayer(tp_id: int, full_name: str = Form(...)):
    conn = database.get_db_connection()
    cur = conn.cursor()
    try:
        # Оновлення даних платника
        cur.execute("UPDATE taxpayers SET full_name = %s WHERE id = %s", (full_name, tp_id))
        conn.commit()
    finally:
        cur.close()
        conn.close()
    return RedirectResponse(url="/?role=admin", status_code=303)


@app.get("/taxpayer/delete/{tp_id}")
async def delete_taxpayer(tp_id: int):
    conn = database.get_db_connection()
    cur = conn.cursor()
    try:
        # Видалення платника
        cur.execute("DELETE FROM taxpayers WHERE id = %s", (tp_id,))
        conn.commit()
    finally:
        cur.close()
        conn.close()
    return RedirectResponse(url="/?role=admin", status_code=303)


@app.post("/tax-record/add")
async def add_record(
        taxpayer_id: int = Form(...),
        tax_type_id: int = Form(...),
        income: float = Form(...)
):
    conn = database.get_db_connection()
    cur = conn.cursor(cursor_factory=RealDictCursor)

    # Спочатку дізнаємося ставку податку з бази
    cur.execute("SELECT rate FROM tax_types WHERE id = %s", (tax_type_id,))
    tax_type = cur.fetchone()

    if tax_type:
        amount = income * (tax_type['rate'] / 100)

        cur.execute(
            "INSERT INTO tax_records (amount, taxpayer_id, tax_type_id) VALUES (%s, %s, %s)",
            (amount, taxpayer_id, tax_type_id)
        )
        conn.commit()

    cur.close()
    conn.close()
    return RedirectResponse(url="/?role=admin", status_code=303)


@app.get("/tax-record/delete/{record_id}")
async def delete_record(record_id: int):
    conn = database.get_db_connection()
    cur = conn.cursor()
    try:
        cur.execute("DELETE FROM tax_records WHERE id = %s", (record_id,))
        conn.commit()
    finally:
        cur.close()
        conn.close()
    return RedirectResponse(url="/?role=admin", status_code=303)


@app.post("/tax-type/add")
async def add_tax_type(name: str = Form(...), rate: float = Form(...)):
    conn = database.get_db_connection()
    cur = conn.cursor()
    try:
        cur.execute("INSERT INTO tax_types (name, rate) VALUES (%s, %s)", (name, rate))
        conn.commit()
    finally:
        cur.close()
        conn.close()
    return RedirectResponse(url="/?role=admin", status_code=303)


@app.post("/tax-record/update/{record_id}")
async def update_record(record_id: int, amount: float = Form(...)):
    conn = database.get_db_connection()
    cur = conn.cursor()
    cur.execute("UPDATE tax_records SET amount = %s WHERE id = %s", (amount, record_id))
    conn.commit()
    cur.close()
    conn.close()
    return RedirectResponse(url="/?role=admin", status_code=303)
