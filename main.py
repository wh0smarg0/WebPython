from fastapi import FastAPI, Request, Form
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from bson import ObjectId
import database
import asyncio

app = FastAPI(
    title="Система Обліку Податків (MongoDB)",
    description="Лабораторна робота №3. Варіант 12. NoSQL рішення",
    version="3.0.0"
)

templates = Jinja2Templates(directory="templates")


# --- ДОПОМІЖНІ ФУНКЦІЇ ДЛЯ КОНВЕРТАЦІЇ ДАНИХ ---
def taxpayer_helper(tp) -> dict:
    return {
        "id": str(tp["_id"]),
        "full_name": tp["full_name"],
        "tin": tp["tin"]
    }


def tax_type_helper(tt) -> dict:
    return {
        "id": str(tt["_id"]),
        "name": tt["name"],
        "rate": tt["rate"]
    }


def record_helper(rec) -> dict:
    return {
        "id": str(rec["_id"]),
        "amount": rec["amount"],
        "taxpayer_name": rec.get("taxpayer_name", "Невідомо"),
        "tax_name": rec.get("tax_name", "Невідомо"),
        "tax_rate": rec.get("tax_rate", 0)
    }


# --- МАРШРУТИ ---

@app.get("/", response_class=HTMLResponse)
async def home(request: Request, role: str = "user"):
    try:
        # 1. Отримання всіх платників
        taxpayers = []
        async for tp in database.taxpayers_collection.find().sort("full_name", 1):
            taxpayers.append(taxpayer_helper(tp))

        # 2. Отримання всіх типів податків
        tax_types = []
        async for tt in database.tax_types_collection.find().sort("name", 1):
            tax_types.append(tax_type_helper(tt))

        # 3. Отримання нарахувань (в NoSQL зберігаємо денормалізовані дані)
        tax_records = []
        async for rec in database.records_collection.find().sort("_id", -1):
            tax_records.append(record_helper(rec))

        return templates.TemplateResponse("index.html", {
            "request": request,
            "taxpayers": taxpayers,
            "tax_records": tax_records,
            "tax_types": tax_types,
            "role": role,
            "name": "Ерік"
        })
    except Exception as e:
        print(f"Помилка MongoDB: {e}")
        return HTMLResponse(content="Помилка підключення до MongoDB.", status_code=500)


@app.post("/taxpayer/add")
async def add_taxpayer(full_name: str = Form(...), tin: str = Form(...)):
    await database.taxpayers_collection.insert_one({
        "full_name": full_name,
        "tin": tin
    })
    return RedirectResponse(url="/?role=admin", status_code=303)


@app.post("/taxpayer/update/{tp_id}")
async def update_taxpayer(tp_id: str, full_name: str = Form(...)):
    await database.taxpayers_collection.update_one(
        {"_id": ObjectId(tp_id)},
        {"$set": {"full_name": full_name}}
    )
    return RedirectResponse(url="/?role=admin", status_code=303)


@app.get("/taxpayer/delete/{tp_id}")
async def delete_taxpayer(tp_id: str):
    # Видаляємо платника
    await database.taxpayers_collection.delete_one({"_id": ObjectId(tp_id)})

    await database.records_collection.delete_many({"taxpayer_id": ObjectId(tp_id)})
    return RedirectResponse(url="/?role=admin", status_code=303)


@app.post("/tax-type/add")
async def add_tax_type(name: str = Form(...), rate: float = Form(...)):
    await database.tax_types_collection.insert_one({
        "name": name,
        "rate": rate
    })
    return RedirectResponse(url="/?role=admin", status_code=303)


@app.post("/tax-record/add")
async def add_record(
        taxpayer_id: str = Form(...),
        tax_type_id: str = Form(...),
        income: float = Form(...)
):
    # Шукаємо дані платника та типу податку
    tp = await database.taxpayers_collection.find_one({"_id": ObjectId(taxpayer_id)})
    tt = await database.tax_types_collection.find_one({"_id": ObjectId(tax_type_id)})

    if tp and tt:
        amount = income * (tt['rate'] / 100)

        # В NoSQL зберігаємо копії імен (денормалізація), щоб не робити JOIN при читанні
        await database.records_collection.insert_one({
            "amount": round(amount, 2),
            "taxpayer_id": ObjectId(taxpayer_id),
            "taxpayer_name": tp["full_name"],
            "tax_name": tt["name"],
            "tax_rate": tt["rate"]
        })

    return RedirectResponse(url="/?role=admin", status_code=303)


@app.get("/tax-record/delete/{record_id}")
async def delete_record(record_id: str):
    await database.records_collection.delete_one({"_id": ObjectId(record_id)})
    return RedirectResponse(url="/?role=admin", status_code=303)


@app.post("/tax-record/update/{record_id}")
async def update_record(record_id: str, amount: float = Form(...)):
    await database.records_collection.update_one(
        {"_id": ObjectId(record_id)},
        {"$set": {"amount": amount}}
    )
    return RedirectResponse(url="/?role=admin", status_code=303)
