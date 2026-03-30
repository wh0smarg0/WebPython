from fastapi import FastAPI, Request, Form, Depends, HTTPException
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session
import models
from database import SessionLocal, engine

# Створення таблиць
models.Base.metadata.create_all(bind=engine)

# Після створення таблиць додаємо початкові дані
db_sync = SessionLocal()
if not db_sync.query(models.TaxType).first():
    # Додаємо стандартні типи податків для Варіанту 12
    db_sync.add(models.TaxType(name="ПДВ", rate=20.0))
    db_sync.add(models.TaxType(name="Військовий збір", rate=1.5))
    db_sync.add(models.TaxType(name="ПДФО", rate=18.0))
    db_sync.commit()
db_sync.close()

app = FastAPI(
    title="Система Обліку Податків",
    description="Лабораторна робота №1. Варіант 12. Платники, податки та нарахування.",
    version="1.2.0" # Зміна в OpenAPI
)

templates = Jinja2Templates(directory=".")

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

# --- МАРШРУТИ ---

@app.get("/", response_class=HTMLResponse)
async def home(request: Request, role: str = "user", db: Session = Depends(get_db)):
    taxpayers = db.query(models.Taxpayer).all()
    tax_records = db.query(models.TaxRecord).all()
    tax_types = db.query(models.TaxType).all()

    return templates.TemplateResponse("index.html", {
        "request": request,
        "taxpayers": taxpayers,
        "tax_records": tax_records,
        "tax_types": tax_types,
        "role": role
    })

# CREATE
@app.post("/taxpayer/add")
async def add_taxpayer(full_name: str = Form(...), tin: str = Form(...), db: Session = Depends(get_db)):
    new_tp = models.Taxpayer(full_name=full_name, tin=tin)
    db.add(new_tp)
    db.commit()
    return RedirectResponse(url="/?role=admin", status_code=303)

# UPDATE (Оновлення імені)
@app.post("/taxpayer/update/{tp_id}")
async def update_taxpayer(tp_id: int, full_name: str = Form(...), db: Session = Depends(get_db)):
    tp = db.query(models.Taxpayer).filter(models.Taxpayer.id == tp_id).first()
    if tp:
        tp.full_name = full_name
        db.commit()
    return RedirectResponse(url="/?role=admin", status_code=303)

# DELETE
@app.get("/taxpayer/delete/{tp_id}")
async def delete_taxpayer(tp_id: int, db: Session = Depends(get_db)):
    tp = db.query(models.Taxpayer).filter(models.Taxpayer.id == tp_id).first()
    if tp:
        db.delete(tp)
        db.commit()
    return RedirectResponse(url="/?role=admin", status_code=303)

@app.post("/tax-record/add")
async def add_record(
        taxpayer_id: int = Form(...),
        tax_type_id: int = Form(...),
        income: float = Form(...),
        db: Session = Depends(get_db)
):
    # Тип налогу
    tax_type = db.query(models.TaxType).filter(models.TaxType.id == tax_type_id).first()
    if tax_type:
        # Сума налогу: дохід * (ставка / 100)
        calculated_amount = income * (tax_type.rate / 100)

        new_record = models.TaxRecord(
            amount=round(calculated_amount, 2),
            taxpayer_id=taxpayer_id,
            tax_type_id=tax_type_id
        )
        db.add(new_record)
        db.commit()
    return RedirectResponse(url="/?role=admin", status_code=303)

# Видалення нарахування
@app.get("/tax-record/delete/{rec_id}")
async def delete_record(rec_id: int, db: Session = Depends(get_db)):
    record = db.query(models.TaxRecord).filter(models.TaxRecord.id == rec_id).first()
    if record:
        db.delete(record)
        db.commit()
    return RedirectResponse(url="/?role=admin", status_code=303)

# Оновлення суми нарахування (якщо адмін помилився при введенні)
@app.post("/tax-record/update/{rec_id}")
async def update_record(rec_id: int, amount: float = Form(...), db: Session = Depends(get_db)):
    record = db.query(models.TaxRecord).filter(models.TaxRecord.id == rec_id).first()
    if record:
        record.amount = amount
        db.commit()
    return RedirectResponse(url="/?role=admin", status_code=303)
