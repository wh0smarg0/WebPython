from motor.motor_asyncio import AsyncIOMotorClient
from bson import ObjectId

# Налаштування підключення
MONGO_DETAILS = "mongodb://localhost:27017"

client = AsyncIOMotorClient(MONGO_DETAILS)
db = client.taxes_nosql_db  # Назва нової бази даних

# Колекції (аналог таблиць у PostgreSQL)
taxpayers_collection = db.get_collection("taxpayers")
records_collection = db.get_collection("tax_records")
tax_types_collection = db.get_collection("tax_types")

# Функція для перетворення MongoDB-документа у зручний для Python словник
def taxpayer_helper(taxpayer) -> dict:
    return {
        "id": str(taxpayer["_id"]),
        "full_name": taxpayer["full_name"],
        "tin": taxpayer["tin"],
    }

def record_helper(record) -> dict:
    return {
        "id": str(record["_id"]),
        "amount": record["amount"],
        "taxpayer_name": record.get("taxpayer_name"), # Дані тепер можуть бути вкладеними
        "tax_name": record.get("tax_name"),
        "rate": record.get("rate")
    }
