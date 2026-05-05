import os
from datetime import datetime, timedelta

from dotenv import load_dotenv
from pymongo import MongoClient
from werkzeug.security import generate_password_hash

from services.encryption import encrypt_data
from services.mongo_utils import normalize_mongo_uri, get_database_name, get_mongo_client_kwargs

load_dotenv()

MONGO_URI = normalize_mongo_uri(
    os.environ.get("MONGO_URI", "mongodb://localhost:27017/hospital_management"),
    get_database_name(),
)
DB_NAME = get_database_name()
DEFAULT_ADMIN_USERNAME = os.environ.get("DEFAULT_ADMIN_USERNAME", "sabihaadmin")
DEFAULT_ADMIN_PASSWORD = os.environ.get("DEFAULT_ADMIN_PASSWORD", "Sabiha@123")
DEFAULT_ADMIN_NAME = os.environ.get("DEFAULT_ADMIN_NAME", "Sabiha Admin")
ADMIN_EMAIL = os.environ.get("ADMIN_EMAIL", "admin@example.com").strip().lower()


def _now():
    return datetime.now()


def _encrypt_patient(doc: dict) -> dict:
    payload = dict(doc)
    for key in ["name", "contactNo", "cnic", "guardianName", "guardianPhone"]:
        if payload.get(key):
            payload[key] = encrypt_data(str(payload[key]))
    return payload


def _upsert_user(db, user: dict):
    now = _now()
    db.users.update_one(
        {"username": user["username"]},
        {
            "$set": {
                "password": generate_password_hash(user["password"]),
                "role": user["role"],
                "name": user["name"],
                "email": user["email"].strip().lower(),
                "updated_at": now,
            },
            "$setOnInsert": {
                "created_at": now,
            },
            "$unset": {
                "deleted_at": "",
            },
        },
        upsert=True,
    )


def _upsert_patient(db, patient: dict):
    now = _now()
    encrypted = _encrypt_patient(patient)
    db.patients.update_one(
        {"cnic": encrypted["cnic"]},
        {
            "$set": {
                **encrypted,
                "updated_at": now,
            },
            "$setOnInsert": {
                "created_at": patient.get("created_at", now),
            },
            "$unset": {
                "deleted_at": "",
            },
        },
        upsert=True,
    )


def _ensure_employee(db, employee: dict):
    now = _now()
    db.employees.update_one(
        {"name": employee["name"]},
        {
            "$set": {
                **employee,
                "updated_at": now,
            },
            "$setOnInsert": {"created_at": now},
            "$unset": {"deleted_at": ""},
        },
        upsert=True,
    )


def _insert_if_empty(db, collection_name: str, docs: list[dict]):
    collection = db[collection_name]
    if collection.count_documents({}) == 0 and docs:
        collection.insert_many(docs)
        print(f"Seeded {collection_name}: {len(docs)} docs")
    else:
        print(f"Skipped {collection_name}: existing data present")


def seed():
    client = MongoClient(MONGO_URI, **get_mongo_client_kwargs(MONGO_URI))
    db = client[DB_NAME]

    print(f"Seeding database: {db.name}")

    users = [
        {
            "username": DEFAULT_ADMIN_USERNAME,
            "password": DEFAULT_ADMIN_PASSWORD,
            "role": "Admin",
            "name": DEFAULT_ADMIN_NAME,
            "email": ADMIN_EMAIL,
        },
        {
            "username": "sabiha.doctor",
            "password": "Doctor@123",
            "role": "Doctor",
            "name": "Dr. Sabiha Ashraf",
            "email": "doctor@sabiha.example",
        },
        {
            "username": "sabiha.psych",
            "password": "Psych@123",
            "role": "Psychologist",
            "name": "Dr. Hina Psychologist",
            "email": "psych@sabiha.example",
        },
        {
            "username": "sabiha.staff",
            "password": "Staff@123",
            "role": "General Staff",
            "name": "Ali Raza Staff",
            "email": "staff@sabiha.example",
        },
    ]
    for user in users:
        _upsert_user(db, user)
    print(f"Users upserted: {len(users)}")

    patients = [
        {
            "name": "Sajid Hussain",
            "fatherName": "Ghulam Hussain",
            "contactNo": "0300-1234567",
            "guardianName": "Nadeem Hussain",
            "guardianPhone": "0301-9876543",
            "cnic": "35202-1234567-1",
            "admissionDate": (_now() - timedelta(days=18)).isoformat(),
            "monthlyFee": "45,000",
            "monthlyAllowance": "5,000",
            "receivedAmount": "25,000",
            "drug": "Ice",
            "isDischarged": False,
            "gender": "Male",
            "age": "29",
            "laundryStatus": True,
            "laundryAmount": 3500,
        },
        {
            "name": "Ahsan Raza",
            "fatherName": "Muhammad Raza",
            "contactNo": "0312-4567890",
            "guardianName": "Imran Raza",
            "guardianPhone": "0313-1231234",
            "cnic": "35201-7654321-9",
            "admissionDate": (_now() - timedelta(days=7)).isoformat(),
            "monthlyFee": "40,000",
            "monthlyAllowance": "4,000",
            "receivedAmount": "15,000",
            "drug": "Heroin",
            "isDischarged": False,
            "gender": "Male",
            "age": "25",
            "laundryStatus": False,
            "laundryAmount": 0,
        },
        {
            "name": "Zubair Qureshi",
            "fatherName": "Abdul Qureshi",
            "contactNo": "0333-9876543",
            "guardianName": "Noman Qureshi",
            "guardianPhone": "0331-1112233",
            "cnic": "35202-9876543-5",
            "admissionDate": (_now() - timedelta(days=102)).isoformat(),
            "dischargeDate": (_now() - timedelta(days=4)).isoformat(),
            "monthlyFee": "35,000",
            "monthlyAllowance": "3,000",
            "receivedAmount": "65,000",
            "drug": "Alcohol",
            "isDischarged": True,
            "gender": "Male",
            "age": "35",
            "laundryStatus": True,
            "laundryAmount": 3500,
        },
    ]
    for patient in patients:
        _upsert_patient(db, patient)
    print(f"Patients upserted: {len(patients)}")

    employees = [
        {"name": "Muhammad Rizwan", "designation": "Security Guard", "salary": 25000, "phone": "0305-1111111"},
        {"name": "Abdul Hafeez", "designation": "Kitchen Staff", "salary": 20000, "phone": "0305-2222222"},
        {"name": "Sajid Mahmood", "designation": "Sweeper", "salary": 18000, "phone": "0305-3333333"},
    ]
    for employee in employees:
        _ensure_employee(db, employee)
    print(f"Employees upserted: {len(employees)}")

    _insert_if_empty(
        db,
        "utility_bills",
        [
            {"type": "Electricity", "amount": 15000, "month": _now().month, "year": _now().year, "status": "Paid", "date": _now() - timedelta(days=5)},
            {"type": "Gas", "amount": 4000, "month": _now().month, "year": _now().year, "status": "Pending", "date": _now() - timedelta(days=2)},
        ],
    )

    _insert_if_empty(
        db,
        "report_config",
        [{"_id": "main_config", "updated_at": _now(), "day_columns": [], "night_columns": []}],
    )

    print("\n--- Sabiha seed completed successfully ---")
    print(f"Admin username: {DEFAULT_ADMIN_USERNAME}")
    print(f"Admin password: {DEFAULT_ADMIN_PASSWORD}")


if __name__ == "__main__":
    seed()
