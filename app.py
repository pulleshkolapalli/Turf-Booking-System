"""
app.py - Main Flask Application for Turf Booking Management System.
CSE494 - Intelligent NoSQL Databases.
"""

import os
from datetime import datetime, time, timezone
from flask import Flask, render_template, request, redirect, url_for, flash
from bson import ObjectId

import db
from db import DATABASE_NAME, safe_object_id, init_indexes, get_mongo_uri

app = Flask(__name__)
app.secret_key = os.getenv("SECRET_KEY", "cse494-turf-booking-secret-key-2026")


# Helper context processor to make connection status accessible to all templates
@app.context_processor
def inject_global_data():
    uri = get_mongo_uri()
    is_uri_set = bool(uri and "<username>" not in uri and "<password>" not in uri)
    return {
        "is_uri_set": is_uri_set,
        "database_name": DATABASE_NAME,
        "now_year": datetime.now().year
    }


def parse_date_only(date_str):
    """Parses YYYY-MM-DD into a datetime at midnight UTC."""
    try:
        dt = datetime.strptime(date_str.strip(), "%Y-%m-%d")
        return dt.replace(hour=0, minute=0, second=0, microsecond=0)
    except (ValueError, TypeError, AttributeError):
        return None


def calculate_duration_and_amount(start_time_str, end_time_str, hourly_rate):
    """
    Validates times (HH:MM) and calculates total duration in hours and total price.
    Returns (duration_hours, amount, error_message).
    """
    try:
        t_start = datetime.strptime(start_time_str.strip(), "%H:%M")
        t_end = datetime.strptime(end_time_str.strip(), "%H:%M")
    except (ValueError, TypeError, AttributeError):
        return None, None, "Invalid time format. Please use HH:MM."

    duration_seconds = (t_end - t_start).total_seconds()
    if duration_seconds <= 0:
        return None, None, "End time must be later than start time."

    duration_hours = duration_seconds / 3600.0
    amount = round(duration_hours * float(hourly_rate), 2)
    return duration_hours, amount, None


def has_time_overlap(existing_start, existing_end, new_start, new_end):
    """
    Checks if two time intervals [existing_start, existing_end) and
    [new_start, new_end) overlap on the same day.
    """
    # Overlap occurs unless one ends before the other starts
    return not (new_end <= existing_start or new_start >= existing_end)


# ===================================================================
# ROUTES
# ===================================================================

@app.route("/")
def index():
    """Dashboard page showing system status, live counts, aggregations, and quick actions."""
    connected, conn_msg = db.check_connection()
    stats = {
        "turfs": 0,
        "active_turfs": 0,
        "users": 0,
        "bookings": 0,
        "confirmed_bookings": 0,
        "pending_bookings": 0
    }
    recent_bookings = []
    status_aggregation = []
    turf_aggregation = []

    if connected:
        cols = db.get_collections()
        users_col = cols["users"]
        turfs_col = cols["turfs"]
        bookings_col = cols["bookings"]

        try:
            stats["turfs"] = turfs_col.count_documents({})
            stats["active_turfs"] = turfs_col.count_documents({"isActive": True})
            stats["users"] = users_col.count_documents({})
            stats["bookings"] = bookings_col.count_documents({})
            stats["confirmed_bookings"] = bookings_col.count_documents({"status": "confirmed"})
            stats["pending_bookings"] = bookings_col.count_documents({"status": "pending"})

            # Dictionary lookup for referenced documents (easy for students to explain)
            users_map = {u["_id"]: u for u in users_col.find()}
            turfs_map = {t["_id"]: t for t in turfs_col.find()}

            # Real MongoDB Aggregation Pipeline 1: Group bookings by status
            try:
                status_aggregation = list(bookings_col.aggregate([
                    {"$group": {
                        "_id": "$status",
                        "totalCount": {"$sum": 1},
                        "totalAmount": {"$sum": "$amount"}
                    }},
                    {"$sort": {"totalCount": -1}}
                ]))
            except Exception:
                status_aggregation = []

            # Real MongoDB Aggregation Pipeline 2: Group bookings by turf facility
            try:
                raw_turf_agg = list(bookings_col.aggregate([
                    {"$group": {
                        "_id": "$turfId",
                        "bookingCount": {"$sum": 1},
                        "revenue": {"$sum": "$amount"}
                    }},
                    {"$sort": {"bookingCount": -1}},
                    {"$limit": 5}
                ]))
                for item in raw_turf_agg:
                    turf_obj = turfs_map.get(item["_id"])
                    turf_aggregation.append({
                        "turfName": turf_obj["name"] if turf_obj else "Unknown Turf",
                        "sportType": turf_obj.get("sportType", "N/A") if turf_obj else "",
                        "bookingCount": item.get("bookingCount", 0),
                        "revenue": item.get("revenue", 0)
                    })
            except Exception:
                turf_aggregation = []

            # Fetch recent 5 bookings
            raw_bookings = list(bookings_col.find().sort("createdAt", -1).limit(5))

            for b in raw_bookings:
                user = users_map.get(b.get("userId"))
                turf = turfs_map.get(b.get("turfId"))
                recent_bookings.append({
                    "_id": b["_id"],
                    "demoCode": b.get("demoCode", str(b["_id"])[-6:]),
                    "userName": user["name"] if user else "Unknown User",
                    "turfName": turf["name"] if turf else "Unknown Turf",
                    "bookingDate": b.get("bookingDate"),
                    "timeSlot": f"{b.get('startTime')} - {b.get('endTime')}",
                    "amount": b.get("amount", 0),
                    "status": b.get("status", "pending")
                })
        except Exception as e:
            flash(f"Error querying dashboard metrics: {e}", "danger")

    return render_template(
        "index.html",
        connected=connected,
        conn_msg=conn_msg,
        stats=stats,
        recent_bookings=recent_bookings,
        status_aggregation=status_aggregation,
        turf_aggregation=turf_aggregation
    )


# -------------------------------------------------------------------
# TURF ROUTES
# -------------------------------------------------------------------

@app.route("/turfs")
def list_turfs():
    """List turfs with optional filtering by sportType and city."""
    connected, _ = db.check_connection()
    if not connected:
        flash("Cannot fetch turfs: MongoDB Atlas is currently not connected.", "warning")
        return render_template("turfs.html", turfs=[], sports=[], cities=[], selected_sport="", selected_city="")

    cols = db.get_collections()
    turfs_col = cols["turfs"]

    # Filter parameters from query string
    sport_filter = request.args.get("sport", "").strip()
    city_filter = request.args.get("city", "").strip()

    # Build MongoDB query filter
    query = {}
    if sport_filter:
        query["sportType"] = sport_filter
    if city_filter:
        # Case-insensitive substring search for city
        query["city"] = {"$regex": city_filter, "$options": "i"}

    turfs = list(turfs_col.find(query).sort("name", 1))

    # Get distinct options for filter dropdowns
    sports = turfs_col.distinct("sportType")
    cities = turfs_col.distinct("city")

    return render_template(
        "turfs.html",
        turfs=turfs,
        sports=sports,
        cities=cities,
        selected_sport=sport_filter,
        selected_city=city_filter
    )


@app.route("/turfs/add", methods=["GET", "POST"])
def add_turf():
    """Form to add a new sports turf document."""
    connected, _ = db.check_connection()
    if not connected:
        flash("Cannot add turf: MongoDB Atlas is not connected.", "danger")
        return redirect(url_for("index"))

    cols = db.get_collections()
    users_col = cols["users"]
    turfs_col = cols["turfs"]

    if request.method == "POST":
        name = request.form.get("name", "").strip()
        city = request.form.get("city", "").strip()
        sport_type = request.form.get("sportType", "").strip()
        amenities_raw = request.form.get("amenities", "").strip()
        hourly_rate_raw = request.form.get("hourlyRate", "").strip()
        is_active = "isActive" in request.form
        owner_id_raw = request.form.get("ownerId", "").strip()

        # Validation
        if not name or not city or not sport_type:
            flash("Turf name, city, and sport type are required fields.", "danger")
            return redirect(url_for("add_turf"))

        try:
            hourly_rate = float(hourly_rate_raw)
            if hourly_rate <= 0:
                flash("Hourly rate must be a positive number.", "danger")
                return redirect(url_for("add_turf"))
        except (ValueError, TypeError):
            flash("Invalid hourly rate. Please enter a valid number.", "danger")
            return redirect(url_for("add_turf"))

        # Parse amenities array (comma-separated)
        amenities = [a.strip() for a in amenities_raw.split(",") if a.strip()]

        # Resolve owner ObjectId
        owner_id = safe_object_id(owner_id_raw)
        if not owner_id:
            # Fallback to first admin or first user if none selected
            default_admin = users_col.find_one({"role": "admin"}) or users_col.find_one({})
            owner_id = default_admin["_id"] if default_admin else None

        # Build document exactly following required schema
        new_turf = {
            "name": name,
            "city": city,
            "sportType": sport_type,
            "amenities": amenities,
            "hourlyRate": hourly_rate,
            "isActive": is_active,
            "ownerId": owner_id,
            "createdAt": datetime.now(timezone.utc)
        }

        turfs_col.insert_one(new_turf)
        flash(f"Turf '{name}' successfully created in MongoDB Atlas!", "success")
        return redirect(url_for("list_turfs"))

    # GET: Load users for owner selection
    users = list(users_col.find().sort("name", 1))
    return render_template("add_turf.html", users=users)


@app.route("/turfs/<turf_id>/edit", methods=["GET", "POST"])
def edit_turf(turf_id):
    """Edit an existing turf facility."""
    connected, _ = db.check_connection()
    if not connected:
        flash("Cannot edit turf: MongoDB Atlas is not connected.", "danger")
        return redirect(url_for("list_turfs"))

    cols = db.get_collections()
    turfs_col = cols["turfs"]
    users_col = cols["users"]

    t_id = safe_object_id(turf_id)
    if not t_id:
        flash("Invalid turf ID provided.", "danger")
        return redirect(url_for("list_turfs"))

    turf = turfs_col.find_one({"_id": t_id})
    if not turf:
        flash("Turf document not found in MongoDB.", "warning")
        return redirect(url_for("list_turfs"))

    if request.method == "POST":
        name = request.form.get("name", "").strip()
        city = request.form.get("city", "").strip()
        sport_type = request.form.get("sportType", "").strip()
        amenities_raw = request.form.get("amenities", "").strip()
        hourly_rate_raw = request.form.get("hourlyRate", "").strip()
        is_active = "isActive" in request.form
        owner_id_raw = request.form.get("ownerId", "").strip()

        if not name or not city or not sport_type:
            flash("Turf name, city, and sport type are required fields.", "danger")
            return redirect(url_for("edit_turf", turf_id=turf_id))

        try:
            hourly_rate = float(hourly_rate_raw)
            if hourly_rate <= 0:
                flash("Hourly rate must be a positive number.", "danger")
                return redirect(url_for("edit_turf", turf_id=turf_id))
        except (ValueError, TypeError):
            flash("Invalid hourly rate. Please enter a valid number.", "danger")
            return redirect(url_for("edit_turf", turf_id=turf_id))

        amenities = [a.strip() for a in amenities_raw.split(",") if a.strip()]
        owner_id = safe_object_id(owner_id_raw) or turf.get("ownerId")

        turfs_col.update_one(
            {"_id": t_id},
            {"$set": {
                "name": name,
                "city": city,
                "sportType": sport_type,
                "amenities": amenities,
                "hourlyRate": hourly_rate,
                "isActive": is_active,
                "ownerId": owner_id,
                "updatedAt": datetime.now(timezone.utc)
            }}
        )
        flash(f"Turf '{name}' updated successfully in MongoDB Atlas!", "success")
        return redirect(url_for("list_turfs"))

    users = list(users_col.find().sort("name", 1))
    amenities_str = ", ".join(turf.get("amenities", []))
    return render_template("edit_turf.html", turf=turf, users=users, amenities_str=amenities_str)


@app.route("/turfs/<turf_id>/delete", methods=["POST"])
def delete_turf(turf_id):
    """Delete a turf document with active booking check."""
    connected, _ = db.check_connection()
    if not connected:
        flash("Cannot delete turf: MongoDB Atlas is not connected.", "danger")
        return redirect(url_for("list_turfs"))

    cols = db.get_collections()
    turfs_col = cols["turfs"]
    bookings_col = cols["bookings"]

    t_id = safe_object_id(turf_id)
    if not t_id:
        flash("Invalid turf ID provided.", "danger")
        return redirect(url_for("list_turfs"))

    turf = turfs_col.find_one({"_id": t_id})
    if not turf:
        flash("Turf not found in database.", "warning")
        return redirect(url_for("list_turfs"))

    # Prevent deleting if active or pending bookings exist
    active_count = bookings_col.count_documents({
        "turfId": t_id,
        "status": {"$in": ["confirmed", "pending"]}
    })
    if active_count > 0:
        flash(f"Cannot delete '{turf['name']}': {active_count} active/pending booking(s) reference this venue. Cancel or complete them first.", "warning")
        return redirect(url_for("list_turfs"))

    turfs_col.delete_one({"_id": t_id})
    flash(f"Turf '{turf['name']}' was successfully deleted from MongoDB.", "success")
    return redirect(url_for("list_turfs"))


# -------------------------------------------------------------------
# USER ROUTES
# -------------------------------------------------------------------

@app.route("/users")
def list_users():
    """List all registered users from MongoDB users collection."""
    connected, _ = db.check_connection()
    if not connected:
        flash("Cannot fetch users: MongoDB Atlas is not connected.", "warning")
        return render_template("users.html", users=[])

    cols = db.get_collections()
    users = list(cols["users"].find().sort("createdAt", -1))
    return render_template("users.html", users=users)


@app.route("/users/add", methods=["GET", "POST"])
def add_user():
    """Form to register a new user in MongoDB users collection."""
    connected, _ = db.check_connection()
    if not connected:
        flash("Cannot add user: MongoDB Atlas is not connected.", "danger")
        return redirect(url_for("index"))

    cols = db.get_collections()
    users_col = cols["users"]

    if request.method == "POST":
        name = request.form.get("name", "").strip()
        email = request.form.get("email", "").strip().lower()
        role = request.form.get("role", "user").strip().lower()

        if not name or not email:
            flash("User name and email are required.", "danger")
            return redirect(url_for("add_user"))

        if "@" not in email or "." not in email:
            flash("Please enter a valid email address.", "danger")
            return redirect(url_for("add_user"))

        if role not in ["user", "admin"]:
            role = "user"

        # Check unique email
        existing = users_col.find_one({"email": email})
        if existing:
            flash(f"A user with email '{email}' already exists in MongoDB.", "warning")
            return redirect(url_for("add_user"))

        new_user = {
            "name": name,
            "email": email,
            "role": role,
            "createdAt": datetime.now(timezone.utc)
        }

        users_col.insert_one(new_user)
        flash(f"User '{name}' ({email}) successfully added!", "success")
        return redirect(url_for("list_users"))

    return render_template("add_user.html")


# -------------------------------------------------------------------
# BOOKING ROUTES
# -------------------------------------------------------------------

@app.route("/bookings")
def list_bookings():
    """
    List and filter bookings.
    Supports filtering by status, turf, booking date, and search query.
    Uses simple Python lookup dictionaries to map referenced userId and turfId
    into human-readable names for student viva clarity.
    """
    connected, _ = db.check_connection()
    if not connected:
        flash("Cannot fetch bookings: MongoDB Atlas is not connected.", "warning")
        return render_template(
            "bookings.html",
            bookings=[],
            turfs=[],
            selected_status="",
            selected_turf="",
            selected_date="",
            search_query=""
        )

    cols = db.get_collections()
    users_col = cols["users"]
    turfs_col = cols["turfs"]
    bookings_col = cols["bookings"]

    # Filter parameters from query string
    selected_status = request.args.get("status", "").strip().lower()
    selected_turf = request.args.get("turf", "").strip()
    selected_date = request.args.get("date", "").strip()
    search_query = request.args.get("search", "").strip()

    # Build MongoDB query filter
    query = {}
    if selected_status in ["pending", "confirmed", "cancelled"]:
        query["status"] = selected_status

    if selected_turf:
        turf_oid = safe_object_id(selected_turf)
        if turf_oid:
            query["turfId"] = turf_oid

    if selected_date:
        parsed_dt = parse_date_only(selected_date)
        if parsed_dt:
            query["bookingDate"] = parsed_dt

    raw_bookings = list(bookings_col.find(query).sort("bookingDate", -1))

    # Python dictionary lookup for referenced documents (easy for students to explain)
    users_map = {u["_id"]: u for u in users_col.find()}
    turfs_map = {t["_id"]: t for t in turfs_col.find()}
    all_turfs = list(turfs_col.find().sort("name", 1))

    enriched_bookings = []
    for b in raw_bookings:
        user = users_map.get(b.get("userId"))
        turf = turfs_map.get(b.get("turfId"))
        user_name = user["name"] if user else "Deleted User"
        user_email = user["email"] if user else "N/A"
        turf_name = turf["name"] if turf else "Deleted Turf"
        code = b.get("demoCode", str(b["_id"])[-6:].upper())

        # In-memory text search if query provided
        if search_query:
            sq = search_query.lower()
            if (sq not in user_name.lower() and
                sq not in user_email.lower() and
                sq not in turf_name.lower() and
                sq not in code.lower()):
                continue

        enriched_bookings.append({
            "_id": b["_id"],
            "demoCode": code,
            "user": user,
            "turf": turf,
            "userName": user_name,
            "userEmail": user_email,
            "turfName": turf_name,
            "turfCity": turf.get("city", "N/A") if turf else "",
            "sportType": turf.get("sportType", "N/A") if turf else "",
            "bookingDate": b.get("bookingDate"),
            "startTime": b.get("startTime"),
            "endTime": b.get("endTime"),
            "amount": b.get("amount", 0),
            "status": b.get("status", "pending"),
            "createdAt": b.get("createdAt")
        })

    return render_template(
        "bookings.html",
        bookings=enriched_bookings,
        turfs=all_turfs,
        selected_status=selected_status,
        selected_turf=selected_turf,
        selected_date=selected_date,
        search_query=search_query
    )


@app.route("/book", methods=["GET", "POST"])
def book_turf():
    """
    Booking creation page.
    Validates user, turf, times, calculates amount, checks slot overlap,
    and creates a booking document with status 'pending'.
    """
    connected, _ = db.check_connection()
    if not connected:
        flash("Cannot create booking: MongoDB Atlas is not connected.", "danger")
        return redirect(url_for("index"))

    cols = db.get_collections()
    users_col = cols["users"]
    turfs_col = cols["turfs"]
    bookings_col = cols["bookings"]

    if request.method == "POST":
        user_id_raw = request.form.get("userId", "").strip()
        turf_id_raw = request.form.get("turfId", "").strip()
        date_str = request.form.get("bookingDate", "").strip()
        start_time = request.form.get("startTime", "").strip()
        end_time = request.form.get("endTime", "").strip()

        # 1. Validate user reference
        user_id = safe_object_id(user_id_raw)
        user = users_col.find_one({"_id": user_id}) if user_id else None
        if not user:
            flash("Please select a valid user.", "danger")
            return redirect(url_for("book_turf"))

        # 2. Validate turf reference
        turf_id = safe_object_id(turf_id_raw)
        turf = turfs_col.find_one({"_id": turf_id}) if turf_id else None
        if not turf:
            flash("Please select a valid turf.", "danger")
            return redirect(url_for("book_turf"))

        # 3. Validate booking date
        booking_date = parse_date_only(date_str)
        if not booking_date:
            flash("Please select a valid booking date (YYYY-MM-DD).", "danger")
            return redirect(url_for("book_turf"))

        # 4. Calculate duration and amount
        duration_hours, amount, time_err = calculate_duration_and_amount(
            start_time, end_time, turf.get("hourlyRate", 0)
        )
        if time_err:
            flash(time_err, "danger")
            return redirect(url_for("book_turf"))

        # 5. Overlapping reservation check (demo-level conflict check)
        # Find active/pending bookings for the exact same turf and date
        existing_bookings = list(bookings_col.find({
            "turfId": turf_id,
            "bookingDate": booking_date,
            "status": {"$in": ["confirmed", "pending"]}
        }))

        for eb in existing_bookings:
            eb_start = eb.get("startTime", "")
            eb_end = eb.get("endTime", "")
            if has_time_overlap(eb_start, eb_end, start_time, end_time):
                flash(
                    f"Time conflict! '{turf['name']}' is already booked from {eb_start} to {eb_end} on {date_str} (Status: {eb['status']}). Please choose a different time slot.",
                    "warning"
                )
                return redirect(url_for("book_turf"))

        # 6. Insert new booking document
        new_booking = {
            "userId": user_id,
            "turfId": turf_id,
            "bookingDate": booking_date,
            "startTime": start_time,
            "endTime": end_time,
            "amount": amount,
            "status": "pending",
            "createdAt": datetime.now(timezone.utc)
        }

        result = bookings_col.insert_one(new_booking)
        flash(
            f"Booking request submitted successfully! Total Amount: Rs.{amount:,.2f} ({duration_hours:.1f} hrs @ Rs.{turf['hourlyRate']}/hr). Status is set to 'pending'.",
            "success"
        )
        return redirect(url_for("list_bookings"))

    # GET: Populate dropdowns
    preselected_turf_id = request.args.get("turf_id", "")
    users = list(users_col.find().sort("name", 1))
    turfs = list(turfs_col.find({"isActive": True}).sort("name", 1))

    return render_template(
        "book_turf.html",
        users=users,
        turfs=turfs,
        preselected_turf_id=preselected_turf_id,
        today_date=datetime.now().strftime("%Y-%m-%d")
    )


@app.route("/bookings/<booking_id>/status", methods=["POST"])
def update_booking_status(booking_id):
    """Update a booking status to 'confirmed' or 'cancelled'."""
    connected, _ = db.check_connection()
    if not connected:
        flash("Cannot update booking: MongoDB Atlas is not connected.", "danger")
        return redirect(url_for("list_bookings"))

    cols = db.get_collections()
    bookings_col = cols["bookings"]

    b_id = safe_object_id(booking_id)
    if not b_id:
        flash("Invalid booking ID provided.", "danger")
        return redirect(url_for("list_bookings"))

    new_status = request.form.get("status", "").strip().lower()
    if new_status not in ["confirmed", "cancelled", "pending"]:
        flash("Invalid status update requested.", "danger")
        return redirect(url_for("list_bookings"))

    res = bookings_col.update_one(
        {"_id": b_id},
        {"$set": {"status": new_status, "updatedAt": datetime.now(timezone.utc)}}
    )

    if res.modified_count > 0:
        flash(f"Booking status updated to '{new_status}'. Document updated in MongoDB.", "success")
    else:
        flash("Booking document found, but status was already identical.", "info")

    return redirect(url_for("list_bookings"))


# ===================================================================
# APP STARTUP
# ===================================================================

if __name__ == "__main__":
    port = int(os.getenv("PORT", 5000))
    print("\n" + "=" * 65)
    print("  CSE494 TURF BOOKING MANAGEMENT SYSTEM (FLASK + PYMONGO)")
    print("=" * 65)

    connected, msg = db.check_connection()
    if connected:
        print("  [OK] Atlas Connection: ONLINE")
        # Ensure indexes on startup
        idx_ok, idx_msg = init_indexes()
        print(f"  [OK] Indexes: {idx_msg}")
    else:
        print("  ! Atlas Connection: OFFLINE")
        print(f"    Reason: {msg}")
        print("    (Application will still launch and show setup instructions in UI)")

    print(f"\n  Starting Flask development server on: http://127.0.0.1:{port}")
    print("=" * 65 + "\n")
    app.run(host="127.0.0.1", port=port, debug=True)
