import os
from urllib.parse import urlsplit, urlunsplit
import certifi


def get_database_name(default: str = "hospital_management") -> str:
    return (os.getenv("MONGO_DB_NAME") or default).strip() or default


def normalize_mongo_uri(uri: str | None, default_db_name: str | None = None) -> str | None:
    """Ensure a Mongo URI includes a database path when one is configured."""
    if not uri:
        return uri

    db_name = (default_db_name or get_database_name()).strip()
    if not db_name:
        return uri

    parsed = urlsplit(uri)
    if parsed.scheme not in {"mongodb", "mongodb+srv"}:
        return uri

    if parsed.path and parsed.path not in {"", "/"}:
        return uri

    return urlunsplit((parsed.scheme, parsed.netloc, f"/{db_name}", parsed.query, parsed.fragment))


def get_mongo_client_kwargs(uri: str | None) -> dict:
    """Return stable client kwargs for local Mongo and Atlas connections."""
    if not uri:
        return {}

    parsed = urlsplit(uri)
    if parsed.scheme == "mongodb+srv":
        return {
            "tls": True,
            "tlsCAFile": certifi.where(),
            "serverSelectionTimeoutMS": 30000,
            "connectTimeoutMS": 30000,
            "socketTimeoutMS": 30000,
            "retryWrites": True,
        }

    return {
        "serverSelectionTimeoutMS": 30000,
        "connectTimeoutMS": 30000,
        "socketTimeoutMS": 30000,
    }
