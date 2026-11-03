"""
db.py - Database connection and utility module for Turf Booking Management System.
CSE494 - Intelligent NoSQL Databases.
"""

import os
from dotenv import load_dotenv
from pymongo import MongoClient, ASCENDING
from pymongo.errors import ConnectionFailure, ConfigurationError, PyMongoError
from bson import ObjectId
from bson.errors import InvalidId

# Load environment variables from .env file
load_dotenv()

# Fixed academic database name as specified in project report
DATABASE_NAME = "turf_booking_db"

# Cached client and database instances
_client = None
_db = None


def get_mongo_uri():
    """Retrieve MongoDB URI from environment variables."""
    return os.getenv("MONGO_URI", "").strip()


def get_client():
    """
    Creates or returns an existing PyMongo MongoClient.
    Uses a 3-second server selection timeout to avoid long hangs when Atlas is unreachable.
    """
    global _client
    uri = get_mongo_uri()
    if not uri:
        return None

    if _client is None:
        try:
            _client = MongoClient(
                uri,
                serverSelectionTimeoutMS=3000,
                connectTimeoutMS=3000,
                appName="TurfBookingSystem"
            )
        except (ConfigurationError, PyMongoError) as err:
            print(f"[Database Error] Failed to initialize MongoClient: {err}")
            return None
    return _client


def get_db():
    """
    Returns the turf_booking_db database handle.
    Returns None if connection string is missing or invalid.
    """
    global _db
    client = get_client()
    if client is None:
        return None
    if _db is None:
        _db = client[DATABASE_NAME]
    return _db


def check_connection():
    """
    Tests MongoDB Atlas connectivity by pinging the admin database.
    Returns (is_connected: bool, message: str).
    """
    uri = get_mongo_uri()
    if not uri or "<username>" in uri or "<password>" in uri:
        return False, "MONGO_URI is not configured in .env file. Please add your Atlas connection string."

    client = get_client()
    if client is None:
        return False, "Could not initialize PyMongo MongoClient. Check URI format."

    try:
        # The ping command is cheap and does not require auth on admin DB in Atlas
        client.admin.command("ping")
        return True, "Successfully connected to MongoDB Atlas."
    except ConnectionFailure as err:
        return False, f"Connection to MongoDB Atlas failed. Check internet access and Atlas IP Whitelist (0.0.0.0/0). Detail: {err}"
    except Exception as err:
        return False, f"Database connection error: {err}"


def get_collections():
    """
    Returns a dictionary of the 3 required project collections:
    users, turfs, bookings.
    Returns None if database handle is unavailable.
    """
    db = get_db()
    if db is None:
        return None
    return {
        "users": db["users"],
        "turfs": db["turfs"],
        "bookings": db["bookings"]
    }


def safe_object_id(id_val):
    """
    Safely converts a string or ObjectId into a valid bson.ObjectId.
    Returns ObjectId or None if conversion fails.
    """
    if not id_val:
        return None
    if isinstance(id_val, ObjectId):
        return id_val
    try:
        return ObjectId(str(id_val).strip())
    except (InvalidId, TypeError):
        return None


def init_indexes():
    """
    Creates recommended MongoDB indexes idempotently.
    Called on startup if connection is successful.
    - users: unique index on email
    - turfs: compound index on (sportType, isActive)
    - bookings: compound index on (bookingDate, status)
    - bookings: single index on (turfId)
    """
    cols = get_collections()
    if not cols:
        return False, "Database not connected."

    try:
        # Unique index on users.email
        cols["users"].create_index([("email", ASCENDING)], unique=True, name="idx_users_email_unique")

        # Compound index on turfs (sportType, isActive) for fast filtering
        cols["turfs"].create_index(
            [("sportType", ASCENDING), ("isActive", ASCENDING)],
            name="idx_turfs_sport_active"
        )

        # Compound index on bookings (bookingDate, status) for schedule checks
        cols["bookings"].create_index(
            [("bookingDate", ASCENDING), ("status", ASCENDING)],
            name="idx_bookings_date_status"
        )

        # Lookup index on turfId for overlapping checks
        cols["bookings"].create_index(
            [("turfId", ASCENDING)],
            name="idx_bookings_turf_id"
        )

        return True, "Indexes initialized successfully."
    except Exception as err:
        return False, f"Failed to initialize indexes: {err}"

