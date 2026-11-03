"""
seed_data.py - Seed demonstration records into MongoDB Atlas turf_booking_db.
CSE494 - Intelligent NoSQL Databases

Usage:
    python seed_data.py

This script is idempotent: running it multiple times updates existing demo
records rather than creating duplicate entries.
"""

import sys
from datetime import datetime, timedelta, timezone
from db import check_connection, get_collections, init_indexes


def seed_database():
    print("=" * 65)
    print("  CSE494 TURF BOOKING MANAGEMENT SYSTEM - SEED DATA SCRIPT")
    print("=" * 65)

    # 1. Verify connection
    print("\n[Step 1/4] Checking MongoDB Atlas connection...")
    connected, msg = check_connection()
    if not connected:
        print(f"\n[ERROR] Could not connect to MongoDB Atlas:\n  {msg}")
        print("\nPlease ensure you have:")
        print("  1. Created a '.env' file from '.env.example'")
        print("  2. Added your valid MONGO_URI in '.env'")
        print("  3. Allowed your IP address in Atlas Network Access (or 0.0.0.0/0)")
        sys.exit(1)

    print("  [OK] Atlas connection verified successfully.")

    # 2. Initialize Indexes
    print("\n[Step 2/4] Ensuring required database indexes...")
    idx_ok, idx_msg = init_indexes()
    print(f"  [OK] {idx_msg}")

    cols = get_collections()
    users_col = cols["users"]
    turfs_col = cols["turfs"]
    bookings_col = cols["bookings"]

    now = datetime.now(timezone.utc)

    # 3. Seed Users
    print("\n[Step 3/4] Seeding demonstration users...")
    demo_users = [
        {
            "email": "admin@example.com",
            "name": "Turf Admin",
            "role": "admin",
            "createdAt": now
        },
        {
            "email": "rahul@example.com",
            "name": "Rahul Sharma",
            "role": "user",
            "createdAt": now
        }
    ]

    user_ids = {}
    for u in demo_users:
        res = users_col.update_one(
            {"email": u["email"]},
            {"$set": u},
            upsert=True
        )
        doc = users_col.find_one({"email": u["email"]})
        user_ids[u["email"]] = doc["_id"]
        action = "Created" if res.upserted_id else "Updated"
        print(f"  + [{action}] User: {u['name']} ({u['email']}) [Role: {u['role']}] ID: {doc['_id']}")

    admin_id = user_ids["admin@example.com"]
    customer_id = user_ids["rahul@example.com"]

    # 4. Seed Turfs
    print("\n[Step 4/4] Seeding demonstration turfs...")
    demo_turfs = [
        {
            "name": "Green Arena",
            "city": "Phagwara",
            "sportType": "Football",
            "amenities": ["Parking", "Washroom", "Floodlights"],
            "hourlyRate": 1200,
            "isActive": True,
            "ownerId": admin_id,
            "createdAt": now
        },
        {
            "name": "City Cricket Ground",
            "city": "Phagwara",
            "sportType": "Cricket",
            "amenities": ["Parking", "Dressing Room", "Pitch Covers"],
            "hourlyRate": 1500,
            "isActive": True,
            "ownerId": admin_id,
            "createdAt": now
        },
        {
            "name": "Apex Badminton Arena",
            "city": "Phagwara",
            "sportType": "Badminton",
            "amenities": ["Indoor Court", "Locker Room", "Drinking Water"],
            "hourlyRate": 800,
            "isActive": True,
            "ownerId": admin_id,
            "createdAt": now
        }
    ]

    turf_ids = {}
    for t in demo_turfs:
        res = turfs_col.update_one(
            {"name": t["name"]},
            {"$set": t},
            upsert=True
        )
        doc = turfs_col.find_one({"name": t["name"]})
        turf_ids[t["name"]] = doc["_id"]
        action = "Created" if res.upserted_id else "Updated"
        print(f"  + [{action}] Turf: {t['name']} ({t['sportType']}) [Rate: Rs.{t['hourlyRate']}/hr] ID: {doc['_id']}")

    # 5. Seed Bookings
    print("\n[Step 5/5] Seeding demonstration bookings...")
    # Calculate upcoming dates for demo
    tomorrow = (now + timedelta(days=1)).replace(hour=0, minute=0, second=0, microsecond=0)
    day_after = (now + timedelta(days=2)).replace(hour=0, minute=0, second=0, microsecond=0)

    demo_bookings = [
        {
            "demoCode": "BK-1001",
            "userId": customer_id,
            "turfId": turf_ids["Green Arena"],
            "bookingDate": tomorrow,
            "startTime": "18:00",
            "endTime": "19:00",
            "amount": 1200,
            "status": "confirmed",
            "createdAt": now
        },
        {
            "demoCode": "BK-1002",
            "userId": customer_id,
            "turfId": turf_ids["City Cricket Ground"],
            "bookingDate": day_after,
            "startTime": "17:00",
            "endTime": "18:00",
            "amount": 1500,
            "status": "pending",
            "createdAt": now
        }
    ]

    for b in demo_bookings:
        res = bookings_col.update_one(
            {"demoCode": b["demoCode"]},
            {"$set": b},
            upsert=True
        )
        doc = bookings_col.find_one({"demoCode": b["demoCode"]})
        action = "Created" if res.upserted_id else "Updated"
        print(f"  + [{action}] Booking: Code={b['demoCode']} Date={b['bookingDate'].strftime('%Y-%m-%d')} Slot={b['startTime']}-{b['endTime']} [Status: {b['status']}]")

    print("\n" + "=" * 65)
    print("  SEEDING COMPLETE!")
    print(f"  Database 'turf_booking_db' is now populated with:")
    print(f"   - Users:    {users_col.count_documents({})} documents")
    print(f"   - Turfs:    {turfs_col.count_documents({})} documents")
    print(f"   - Bookings: {bookings_col.count_documents({})} documents")
    print("  You can now start the web application by running: python app.py")
    print("  and inspect documents in MongoDB Compass!")
    print("=" * 65)


if __name__ == "__main__":
    seed_database()
