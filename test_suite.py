"""
test_suite.py - Academic Verification & Validation Suite
CSE494 - Intelligent NoSQL Databases: Turf Booking Management System
"""

import unittest
from datetime import datetime, timezone
import mongomock
from bson import ObjectId

# Import app modules
import db
import app
from app import (
    calculate_duration_and_amount,
    has_time_overlap,
    parse_date_only
)
from db import safe_object_id


class TestBusinessLogic(unittest.TestCase):
    """Test core algorithmic and business logic functions."""

    def test_duration_and_amount_calculation(self):
        # 1. Standard 1-hour booking at Rs.1200/hr
        dur, amount, err = calculate_duration_and_amount("18:00", "19:00", 1200)
        self.assertIsNone(err)
        self.assertEqual(dur, 1.0)
        self.assertEqual(amount, 1200.0)

        # 2. 2.5 hours booking at Rs.1500/hr
        dur, amount, err = calculate_duration_and_amount("16:00", "18:30", 1500)
        self.assertIsNone(err)
        self.assertEqual(dur, 2.5)
        self.assertEqual(amount, 3750.0)

        # 3. Invalid: End time before start time
        dur, amount, err = calculate_duration_and_amount("19:00", "18:00", 1200)
        self.assertIsNotNone(err)
        self.assertIn("End time must be later", err)

        # 4. Invalid time format
        dur, amount, err = calculate_duration_and_amount("not_a_time", "19:00", 1200)
        self.assertIsNotNone(err)

    def test_time_overlap_detection(self):
        # Slot A: 18:00 - 19:00

        # Overlapping inside
        self.assertTrue(has_time_overlap("18:00", "19:00", "18:15", "18:45"))

        # Overlapping start
        self.assertTrue(has_time_overlap("18:00", "19:00", "17:30", "18:30"))

        # Overlapping end
        self.assertTrue(has_time_overlap("18:00", "19:00", "18:30", "19:30"))

        # Non-overlapping: strictly before
        self.assertFalse(has_time_overlap("18:00", "19:00", "16:00", "17:00"))

        # Non-overlapping: strictly after
        self.assertFalse(has_time_overlap("18:00", "19:00", "20:00", "21:00"))

        # Adjacent boundary (ends exactly when next starts) -> No overlap
        self.assertFalse(has_time_overlap("18:00", "19:00", "19:00", "20:00"))
        self.assertFalse(has_time_overlap("18:00", "19:00", "17:00", "18:00"))

    def test_safe_object_id_conversion(self):
        # Valid 24-char hex string
        valid_hex = "654a1b2c3d4e5f6a7b8c9d01"
        res = safe_object_id(valid_hex)
        self.assertIsInstance(res, ObjectId)
        self.assertEqual(str(res), valid_hex)

        # Already an ObjectId
        obj_id = ObjectId()
        self.assertEqual(safe_object_id(obj_id), obj_id)

        # Invalid string
        self.assertIsNone(safe_object_id("invalid-hex-id"))
        self.assertIsNone(safe_object_id(""))
        self.assertIsNone(safe_object_id(None))

    def test_parse_date_only(self):
        dt = parse_date_only("2026-11-10")
        self.assertIsNotNone(dt)
        self.assertEqual(dt.year, 2026)
        self.assertEqual(dt.month, 11)
        self.assertEqual(dt.day, 10)
        self.assertEqual(dt.hour, 0)

        # Invalid date
        self.assertIsNone(parse_date_only("invalid-date"))


class TestFlaskDisconnectedGracefulness(unittest.TestCase):
    """Verify application renders gracefully without crashing when Atlas URI is not configured."""

    def setUp(self):
        app.app.config["TESTING"] = True
        self.client = app.app.test_client()

    def test_dashboard_offline_state(self):
        response = self.client.get("/")
        self.assertEqual(response.status_code, 200)
        html = response.data.decode("utf-8")
        self.assertIn("Turf Booking Management System", html)
        self.assertIn("Atlas", html)

    def test_routes_load_without_crash(self):
        for route in ["/turfs", "/users", "/bookings"]:
            response = self.client.get(route, follow_redirects=True)
            self.assertEqual(response.status_code, 200)


class TestFullMongoDBFlowWithMock(unittest.TestCase):
    """Verify real MongoDB CRUD, schema references, and updates using in-memory MongoDB mock."""

    def setUp(self):
        self.mock_client = mongomock.MongoClient()
        self.mock_db = self.mock_client["turf_booking_db"]
        self.mock_cols = {
            "users": self.mock_db["users"],
            "turfs": self.mock_db["turfs"],
            "bookings": self.mock_db["bookings"]
        }

        # Monkey-patch get_collections and check_connection in db & app
        self.orig_get_cols = db.get_collections
        self.orig_check = db.check_connection

        db.get_collections = lambda: self.mock_cols
        db.check_connection = lambda: (True, "Mocked Database Connected")

        app.app.config["TESTING"] = True
        self.client = app.app.test_client()

    def tearDown(self):
        db.get_collections = self.orig_get_cols
        db.check_connection = self.orig_check

    def test_full_crud_and_referencing_lifecycle(self):
        # 1. Create User
        user_res = self.client.post("/users/add", data={
            "name": "Test Customer",
            "email": "customer@example.com",
            "role": "user"
        }, follow_redirects=True)
        self.assertEqual(user_res.status_code, 200)

        created_user = self.mock_cols["users"].find_one({"email": "customer@example.com"})
        self.assertIsNotNone(created_user)
        user_id = created_user["_id"]

        # 2. Create Turf with embedded amenities
        turf_res = self.client.post("/turfs/add", data={
            "name": "Super Stadium Turf",
            "city": "Phagwara",
            "sportType": "Football",
            "amenities": "Floodlights, Parking, Changing Room",
            "hourlyRate": "1400",
            "isActive": "true",
            "ownerId": str(user_id)
        }, follow_redirects=True)
        self.assertEqual(turf_res.status_code, 200)

        created_turf = self.mock_cols["turfs"].find_one({"name": "Super Stadium Turf"})
        self.assertIsNotNone(created_turf)
        turf_id = created_turf["_id"]
        # Verify embedded amenities
        self.assertEqual(created_turf["amenities"], ["Floodlights", "Parking", "Changing Room"])
        self.assertEqual(created_turf["hourlyRate"], 1400.0)

        # 3. Create Booking referencing user and turf
        book_res = self.client.post("/book", data={
            "userId": str(user_id),
            "turfId": str(turf_id),
            "bookingDate": "2026-11-20",
            "startTime": "18:00",
            "endTime": "20:00"
        }, follow_redirects=True)
        self.assertEqual(book_res.status_code, 200)

        created_booking = self.mock_cols["bookings"].find_one({"userId": user_id, "turfId": turf_id})
        self.assertIsNotNone(created_booking)
        self.assertEqual(created_booking["amount"], 2800.0)  # 2 hours * 1400
        self.assertEqual(created_booking["status"], "pending")
        booking_id = created_booking["_id"]

        # 4. Attempt overlapping booking for same turf, same date, overlapping time (19:00 - 21:00)
        conflict_res = self.client.post("/book", data={
            "userId": str(user_id),
            "turfId": str(turf_id),
            "bookingDate": "2026-11-20",
            "startTime": "19:00",
            "endTime": "21:00"
        }, follow_redirects=True)
        self.assertEqual(conflict_res.status_code, 200)
        self.assertIn("Time conflict", conflict_res.data.decode("utf-8"))

        # Verify only 1 booking was created
        self.assertEqual(self.mock_cols["bookings"].count_documents({}), 1)

        # 5. Update booking status to 'confirmed'
        update_res = self.client.post(f"/bookings/{booking_id}/status", data={
            "status": "confirmed"
        }, follow_redirects=True)
        self.assertEqual(update_res.status_code, 200)

        updated_booking = self.mock_cols["bookings"].find_one({"_id": booking_id})
        self.assertEqual(updated_booking["status"], "confirmed")

        # 6. Edit Turf Information (Task 2 Requirement)
        edit_turf_res = self.client.post(f"/turfs/{turf_id}/edit", data={
            "name": "Super Stadium Turf - Renamed",
            "city": "Phagwara",
            "sportType": "Football",
            "amenities": "Floodlights, Parking, Changing Room, Cafeteria",
            "hourlyRate": "1600",
            "isActive": "true",
            "ownerId": str(user_id)
        }, follow_redirects=True)
        self.assertEqual(edit_turf_res.status_code, 200)

        edited_turf = self.mock_cols["turfs"].find_one({"_id": turf_id})
        self.assertEqual(edited_turf["name"], "Super Stadium Turf - Renamed")
        self.assertEqual(edited_turf["hourlyRate"], 1600.0)
        self.assertIn("Cafeteria", edited_turf["amenities"])

        # 7. Delete Turf with Protection (Task 2 Requirement)
        # Attempt deleting turf while active booking exists -> should be blocked
        del_blocked_res = self.client.post(f"/turfs/{turf_id}/delete", follow_redirects=True)
        self.assertEqual(del_blocked_res.status_code, 200)
        self.assertIn("Cannot delete", del_blocked_res.data.decode("utf-8"))
        self.assertIsNotNone(self.mock_cols["turfs"].find_one({"_id": turf_id}))

        # Create an unused turf and delete it safely
        temp_turf_res = self.mock_cols["turfs"].insert_one({
            "name": "Temporary Turf",
            "city": "Phagwara",
            "sportType": "Tennis",
            "amenities": ["Parking"],
            "hourlyRate": 900,
            "isActive": True,
            "ownerId": user_id,
            "createdAt": datetime.now(timezone.utc)
        })
        temp_id = temp_turf_res.inserted_id

        del_ok_res = self.client.post(f"/turfs/{temp_id}/delete", follow_redirects=True)
        self.assertEqual(del_ok_res.status_code, 200)
        self.assertIsNone(self.mock_cols["turfs"].find_one({"_id": temp_id}))

        # 8. Bookings Search & Filter (Task 2 Requirement)
        filter_res = self.client.get(f"/bookings?status=confirmed&turf={turf_id}")
        self.assertEqual(filter_res.status_code, 200)
        self.assertIn("Super Stadium Turf - Renamed", filter_res.data.decode("utf-8"))

        # 9. Dashboard Aggregations (Task 3 Requirement)
        dash_res = self.client.get("/")
        self.assertEqual(dash_res.status_code, 200)
        html = dash_res.data.decode("utf-8")
        self.assertIn("Aggregation Pipeline Insights", html)

        # 10. Verify seed data idempotency
        import seed_data
        seed_data.seed_database()
        user_count_1 = self.mock_cols["users"].count_documents({})
        turf_count_1 = self.mock_cols["turfs"].count_documents({})
        booking_count_1 = self.mock_cols["bookings"].count_documents({})

        # Run seed a second time - counts must remain identical (no duplicates)
        seed_data.seed_database()
        user_count_2 = self.mock_cols["users"].count_documents({})
        turf_count_2 = self.mock_cols["turfs"].count_documents({})
        booking_count_2 = self.mock_cols["bookings"].count_documents({})

        self.assertEqual(user_count_1, user_count_2)
        self.assertEqual(turf_count_1, turf_count_2)
        self.assertEqual(booking_count_1, booking_count_2)


if __name__ == "__main__":
    unittest.main()
