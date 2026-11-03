# Turf Booking Management System Using MongoDB
**CSE494 – Intelligent NoSQL Databases | Academic Mini-Project (CA2)**

A complete, beginner-friendly, and runnable individual web application built with **Python 3**, **Flask**, and **PyMongo**, backed by **MongoDB Atlas** (cloud database) and inspected via **MongoDB Compass**.

---

## 📌 Project Overview
The **Turf Booking Management System** demonstrates how real-world facility discovery and reservation workflows are designed using a NoSQL document database.

Users can browse available sports turfs (by sport, city, amenities, and hourly pricing) and book time slots. The administrator can register new venues, manage users, and review/update reservation statuses.

### Key Highlights
- **Real Database CRUD**: Direct PyMongo integration with MongoDB Atlas (no fake localStorage or mocked data).
- **Full Facility Management**: Add, View, Edit, and safely Delete sports turfs with active booking checks.
- **Relational Referencing in NoSQL**: `bookings` documents link to `users._id` and `turfs._id` using BSON `ObjectId`.
- **Embedded Document Data**: `amenities` are embedded directly inside `turfs` as an array of strings.
- **Server-Side Validation**: Checks required fields, valid positive hourly rates, non-overlapping time intervals, and ensures end time is after start time.
- **Dynamic Search & Filtering**: Filter turfs by sport/city and filter bookings by status, turf venue, date, and keyword search.
- **Live Aggregation Insights**: Real-time MongoDB `$group` aggregation pipeline calculations displayed directly on the dashboard.
- **Academic Viva Ready**: Includes `compass_demo_commands.js` to execute and explain queries, aggregations (`$group`, `$lookup`), and indexing (`explain("executionStats")`).
- **Production & Cloud Deployable**: Pre-configured with `render.yaml`, `Procfile`, and `gunicorn` for hosting on Render.

---

## 🛠️ Technology Stack
| Layer | Technology | Role |
| :--- | :--- | :--- |
| **Backend** | Python 3 + Flask 3.1 | Application routes, server-side validation, business logic |
| **Driver** | PyMongo 4.19 + dnspython | Official MongoDB Python driver for Atlas connections |
| **Database** | MongoDB Atlas (Cloud) | Multi-collection NoSQL document database (`turf_booking_db`) |
| **Inspection** | MongoDB Compass & `mongosh` | GUI tool to inspect documents, run pipelines, and test indexes |
| **Frontend** | Semantic HTML5 + Custom CSS3 | Modern, responsive sports-themed UI (Navy `#0b192c`, Emerald `#059669`, White) |
| **Config** | python-dotenv | Secure `.env` environment variable management |

---

## 🗄️ Database Schema Design
Database Name: **`turf_booking_db`**

### 1. `users` Collection
Stores customer and administrator profiles.
```json
{
  "_id": ObjectId("654a1b2c3d4e5f6a7b8c9d01"),
  "name": "Rahul Sharma",
  "email": "rahul@example.com",
  "role": "user",
  "createdAt": ISODate("2026-11-03T06:00:00Z")
}
```
*Index*: Unique index on `email` (`idx_users_email_unique`).

### 2. `turfs` Collection
Stores sports facility listings with embedded amenities.
```json
{
  "_id": ObjectId("654a1b2c3d4e5f6a7b8c9d02"),
  "name": "Green Arena",
  "city": "Phagwara",
  "sportType": "Football",
  "amenities": ["Parking", "Washroom", "Floodlights"],
  "hourlyRate": 1200,
  "isActive": true,
  "ownerId": ObjectId("654a1b2c3d4e5f6a7b8c9d01"),
  "createdAt": ISODate("2026-11-03T06:00:00Z")
}
```
*Index*: Compound index on `(sportType, isActive)` for fast catalog filtering.

### 3. `bookings` Collection
Stores reservation transactions referencing `userId` and `turfId`.
```json
{
  "_id": ObjectId("654a1b2c3d4e5f6a7b8c9d03"),
  "demoCode": "BK-1001",
  "userId": ObjectId("654a1b2c3d4e5f6a7b8c9d01"),
  "turfId": ObjectId("654a1b2c3d4e5f6a7b8c9d02"),
  "bookingDate": ISODate("2026-11-10T00:00:00Z"),
  "startTime": "18:00",
  "endTime": "19:00",
  "amount": 1200,
  "status": "confirmed",
  "createdAt": ISODate("2026-11-03T06:00:00Z")
}
```
*Index*: Compound index on `(bookingDate, status)` and single index on `turfId` for rapid conflict checking.

---

## 📁 Project Directory Structure
```text
turf-booking-system/
│
├── app.py                      # Main Flask application and URL routing
├── db.py                       # PyMongo client initialization, index creation, safety helpers
├── seed_data.py                # Idempotent script to insert initial demo records
├── requirements.txt            # Python dependencies (Flask, PyMongo, dnspython, python-dotenv)
├── .env.example                # Sample environment template (NEVER commit your .env!)
├── .gitignore                  # Excludes .env, virtual environment, and python caches
├── compass_demo_commands.js    # 14 step-by-step mongosh viva commands for MongoDB Compass
├── README.md                   # Complete documentation and run instructions
│
├── static/
│   └── style.css               # Clean navy & emerald green sports styling
│
└── templates/
    ├── base.html               # Shared layout, navbar, footer, flash alerts
    ├── index.html              # Dashboard with live MongoDB counters and status indicator
    ├── turfs.html              # Turf cards gallery with sport & city search filters
    ├── add_turf.html           # Form to add a new turf facility
    ├── users.html              # List of registered users with role badges
    ├── add_user.html           # Form to register a user profile
    ├── book_turf.html          # Reservation form with live client fee estimator
    └── bookings.html           # Booking management table with Confirm/Cancel actions
```

---

## 🚀 Setup & Execution Guide (Windows PowerShell)

Follow these exact beginner-friendly steps to run the application on your computer:

### Step 1: Open Terminal in Project Folder
Open VS Code, press `Ctrl + ~` to open the integrated PowerShell terminal, and confirm your directory:
```powershell
pwd
```

### Step 2: Create a Virtual Environment
```powershell
python -m venv .venv
```
*(If `python` points to the Microsoft Store alias, you can also use `py -m venv .venv`)*

### Step 3: Activate the Virtual Environment
```powershell
.\.venv\Scripts\Activate.ps1
```
> **Note**: If PowerShell shows a script execution policy error, run this command once and try again:
> ```powershell
> Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass
> ```

### Step 4: Install Dependencies
```powershell
pip install -r requirements.txt
```

### Step 5: Configure Your MongoDB Atlas Connection
1. Duplicate `.env.example` to create `.env`:
   ```powershell
   Copy-Item .env.example .env
   ```
2. Open `.env` in VS Code and paste your own MongoDB Atlas connection URI:
   ```env
   MONGO_URI=mongodb+srv://<your_username>:<your_password>@cluster0.abcde.mongodb.net/?retryWrites=true&w=majority
   SECRET_KEY=cse494-turf-booking-secret-key-2026
   PORT=5000
   ```
   > 🔒 **Security Warning**: Keep your `.env` private. Never push `.env` to GitHub!

### Step 6: Populate Initial Demonstration Records
Run the idempotent seed script to populate users, turfs, and bookings:
```powershell
python seed_data.py
```
*Output will confirm the creation/update of 2 users, 3 sports turfs, and 2 bookings.*

### Step 7: Launch the Web Application
```powershell
python app.py
```
Open your browser and navigate to:
👉 **`http://127.0.0.1:5000`**

---

## 🧭 MongoDB Compass Demonstration Guide

During your viva or class presentation, use MongoDB Compass alongside the web application:

1. **Connect Compass to Atlas**:
   - Open MongoDB Compass.
   - Paste the same connection string from your `.env` and click **Connect**.
2. **Select Database**:
   - In the left sidebar, click on **`turf_booking_db`**.
3. **Inspect Collections**:
   - Click `users`, `turfs`, and `bookings` to see documents in JSON or Table view.
4. **Live Verification**:
   - Go to the website (`http://127.0.0.1:5000/turfs/add`) and submit a new turf.
   - Return to Compass, click the **Refresh** button, and show the examiner that your new document appeared in the `turfs` collection!
5. **Run Advanced Shell Queries**:
   - Click the **`_mongosh`** bar at the bottom of MongoDB Compass.
   - Open [compass_demo_commands.js](file:///compass_demo_commands.js) and copy-paste the queries to show:
     - Filtering with `$lt` and `$in`
     - Aggregation with `$group` to calculate total revenue per booking status
     - `$lookup` to join bookings with user and turf documents
     - Query execution plan using `.explain("executionStats")`

---

## 🌐 Online Deployment Guide (Render)

[![Deploy to Render](https://render.com/images/deploy-to-render-button.svg)](https://render.com/deploy?repo=https://github.com/pullrd/Turf-Booking-System)

This project is pre-configured for one-click hosting on [Render](https://render.com) using [`render.yaml`](file:///render.yaml), [`Procfile`](file:///Procfile), and [`gunicorn`](file:///requirements.txt):

1. **Push Repository to GitHub**:
   Ensure your code is pushed to your GitHub repository `https://github.com/pullrd/Turf-Booking-System`.
2. **Create Web Service on Render**:
   - Log in to your Render Dashboard.
   - Click **New +** &rarr; **Web Service**.
   - Select your GitHub repository **`Turf-Booking-System`**.
3. **Configure Build & Start**:
   - **Environment**: `Python 3`
   - **Build Command**: `pip install -r requirements.txt`
   - **Start Command**: `gunicorn app:app`
4. **Set Production Environment Variables**:
   Under the **Environment** tab on Render, add:
   - `MONGO_URI`: Your MongoDB Atlas cluster connection string.
   - `SECRET_KEY`: A secure random secret key (e.g., `cse494-turf-booking-secret-key-2026`).
   - `PYTHON_VERSION`: `3.11.9` or `3.14.0`
5. **Deploy**:
   Click **Create Web Service**. Render will install packages and launch the app at your assigned public HTTPS URL (e.g., `https://turf-booking-system.onrender.com`).

---

## ❓ Troubleshooting Common Errors

### 1. `ServerSelectionTimeoutError` / Connection Timeout
- **Cause**: MongoDB Atlas has not allowed network traffic from your current IP address.
- **Fix**: Go to [MongoDB Atlas](https://cloud.mongodb.com/) &rarr; **Network Access** &rarr; **Add IP Address** &rarr; click **Allow Access from Anywhere** (`0.0.0.0/0`) for the demo, then save.

### 2. `AuthenticationFailed`
- **Cause**: Incorrect username or password in `MONGO_URI`.
- **Fix**: Check Atlas &rarr; **Database Access**. Verify the database user has `readWriteAnyDatabase` or read/write privileges on `turf_booking_db`. If your password contains special characters (like `@`, `#`), URL-encode them.

### 3. `ModuleNotFoundError: No module named 'flask'`
- **Cause**: The terminal is using the global Python instead of the virtual environment.
- **Fix**: Run `.\.venv\Scripts\Activate.ps1` and verify `(.venv)` appears at the start of your command prompt, then run `pip install -r requirements.txt`.

---

## 🎓 Academic Viva Questions & Answers (CSE494)

**Q1: Why did you choose separate collections for users, turfs, and bookings instead of embedding everything in one collection?**  
> *Answer*: Users and turfs have independent lifecycles. A turf exists even if it has no bookings, and a user can book multiple turfs over time. Embedding bookings directly inside users would cause unbounded document growth and make querying turf availability inefficient. Therefore, referencing via `ObjectId` is the appropriate normalized NoSQL design.

**Q2: Where did you use embedded data in your schema?**  
> *Answer*: We embedded `amenities` as an array of strings inside each `turfs` document (`["Parking", "Floodlights", "Washroom"]`). This is optimal because amenities are always viewed together with the turf and never queried as standalone entities.

**Q3: What indexes did you create and why?**  
> *Answer*:
> 1. `users.email` (unique): Enforces account uniqueness and provides $O(1)$ lookups.
> 2. `turfs (sportType, isActive)` (compound): Speeds up filtering for active venues of a specific sport.
> 3. `bookings (bookingDate, status)` (compound): Rapidly identifies active reservations for scheduling and conflict detection.

**Q4: How does your application prevent double booking?**  
> *Answer*: Before inserting a booking document, the Flask backend queries the `bookings` collection for the requested `turfId` on the specified `bookingDate` where status is `confirmed` or `pending`. It checks whether any existing slot `[startTime, endTime)` overlaps with the requested interval.

---

## 📜 Submission Alignment
- **Student Name**: Kolapalli Hema Pulleswara Rao
- **Reg No**: 12318165
- **Course**: CSE494 - Intelligent NoSQL Databases
- **Task**: CA2 Practical Prototype

