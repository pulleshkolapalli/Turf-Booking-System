/**
 * ===================================================================
 * CSE494 - INTELLIGENT NOSQL DATABASES: CA2 PRACTICAL DEMONSTRATION
 * Project: Turf Booking Management System
 * Database: turf_booking_db
 * Collections: users, turfs, bookings
 *
 * INSTRUCTIONS FOR VIVA / COMPASS DEMO:
 * 1. Open MongoDB Compass.
 * 2. Connect to your MongoDB Atlas cluster.
 * 3. At the bottom of Compass, open the "_mongosh" terminal bar.
 * 4. Run the commands below in this exact order to demonstrate:
 *    - Schema creation & collection verification
 *    - Sample document insertion with ObjectId references
 *    - Read, filter, projection, and sorting
 *    - Document updates ($set)
 *    - Safe deletion
 *    - Compound indexing
 *    - Aggregation pipelines ($group, $sum, $sort)
 *    - Collection joins via $lookup
 *    - Execution statistics via explain("executionStats")
 * ===================================================================
 */

// STEP 1: Select and switch to the project database
use("turf_booking_db");

// STEP 2: Create the three collections if required
if (!db.getCollectionNames().includes("users")) {
  db.createCollection("users");
}
if (!db.getCollectionNames().includes("turfs")) {
  db.createCollection("turfs");
}
if (!db.getCollectionNames().includes("bookings")) {
  db.createCollection("bookings");
}
show collections;

// STEP 3: Insert sample users (upsert pattern to prevent duplicate records)
db.users.updateOne(
  { email: "admin@example.com" },
  {
    $set: {
      name: "Turf Admin",
      email: "admin@example.com",
      role: "admin",
      createdAt: new Date()
    }
  },
  { upsert: true }
);

db.users.updateOne(
  { email: "rahul@example.com" },
  {
    $set: {
      name: "Rahul Sharma",
      email: "rahul@example.com",
      role: "user",
      createdAt: new Date()
    }
  },
  { upsert: true }
);

// STEP 4: Insert sample turfs (with embedded amenities and ownerId reference)
const adminUser = db.users.findOne({ email: "admin@example.com" });

db.turfs.updateOne(
  { name: "Green Arena" },
  {
    $set: {
      name: "Green Arena",
      city: "Phagwara",
      sportType: "Football",
      amenities: ["Parking", "Washroom", "Floodlights"],
      hourlyRate: 1200,
      isActive: true,
      ownerId: adminUser._id,
      createdAt: new Date()
    }
  },
  { upsert: true }
);

db.turfs.updateOne(
  { name: "City Cricket Ground" },
  {
    $set: {
      name: "City Cricket Ground",
      city: "Phagwara",
      sportType: "Cricket",
      amenities: ["Parking", "Dressing Room", "Pitch Covers"],
      hourlyRate: 1500,
      isActive: true,
      ownerId: adminUser._id,
      createdAt: new Date()
    }
  },
  { upsert: true }
);

db.turfs.updateOne(
  { name: "Apex Badminton Arena" },
  {
    $set: {
      name: "Apex Badminton Arena",
      city: "Phagwara",
      sportType: "Badminton",
      amenities: ["Indoor Court", "Locker Room", "Drinking Water"],
      hourlyRate: 800,
      isActive: true,
      ownerId: adminUser._id,
      createdAt: new Date()
    }
  },
  { upsert: true }
);

// STEP 5: Insert sample bookings with correct ObjectId references
const demoCustomer = db.users.findOne({ email: "rahul@example.com" });
const footballTurf = db.turfs.findOne({ name: "Green Arena" });
const cricketTurf = db.turfs.findOne({ name: "City Cricket Ground" });

db.bookings.updateOne(
  { demoCode: "BK-1001" },
  {
    $set: {
      demoCode: "BK-1001",
      userId: demoCustomer._id,
      turfId: footballTurf._id,
      bookingDate: new Date("2026-11-10"),
      startTime: "18:00",
      endTime: "19:00",
      amount: 1200,
      status: "confirmed",
      createdAt: new Date()
    }
  },
  { upsert: true }
);

db.bookings.updateOne(
  { demoCode: "BK-1002" },
  {
    $set: {
      demoCode: "BK-1002",
      userId: demoCustomer._id,
      turfId: cricketTurf._id,
      bookingDate: new Date("2026-11-11"),
      startTime: "17:00",
      endTime: "18:00",
      amount: 1500,
      status: "pending",
      createdAt: new Date()
    }
  },
  { upsert: true }
);

// STEP 6: Find documents in all collections
db.users.find().pretty();
db.turfs.find().pretty();
db.bookings.find().pretty();

// Complex Filter: Football turfs with rate < 1500
db.turfs.find({
  sportType: "Football",
  hourlyRate: { $lt: 1500 }
});

// Inclusion Filter with Projection and Sort
db.turfs.find(
  { isActive: true },
  { _id: 0, name: 1, city: 1, sportType: 1, hourlyRate: 1 }
).sort({ hourlyRate: -1 });

// STEP 7: Update a turf price
db.turfs.updateOne(
  { name: "Green Arena" },
  { $set: { hourlyRate: 1300, updatedAt: new Date() } }
);

// Verify turf rate update
db.turfs.find({ name: "Green Arena" }, { name: 1, hourlyRate: 1 });

// STEP 8: Update a booking status
db.bookings.updateOne(
  { demoCode: "BK-1002" },
  { $set: { status: "confirmed", updatedAt: new Date() } }
);

// Verify booking status update
db.bookings.find({ demoCode: "BK-1002" }, { demoCode: 1, status: 1 });

// STEP 9: Insert and delete only a temporary test record
db.turfs.insertOne({
  name: "Temporary Demo Facility",
  city: "Phagwara",
  sportType: "Tennis",
  amenities: ["Parking"],
  hourlyRate: 900,
  isActive: true,
  demoRecord: true,
  createdAt: new Date()
});

// Verify inserted temporary document
db.turfs.find({ name: "Temporary Demo Facility" });

// Delete only the marked temporary document
db.turfs.deleteOne({ name: "Temporary Demo Facility", demoRecord: true });

// Confirm deletion
db.turfs.find({ name: "Temporary Demo Facility" });

// STEP 10: Create indexes for query optimization
db.users.createIndex({ email: 1 }, { unique: true, name: "idx_users_email_unique" });
db.turfs.createIndex({ sportType: 1, isActive: 1 }, { name: "idx_turfs_sport_active" });
db.bookings.createIndex({ bookingDate: 1, status: 1 }, { name: "idx_bookings_date_status" });
db.bookings.createIndex({ turfId: 1 }, { name: "idx_bookings_turf_id" });

// Inspect all created indexes
db.users.getIndexes();
db.turfs.getIndexes();
db.bookings.getIndexes();

// STEP 11: Run aggregation pipelines
// 11.1 - Group bookings by status and calculate total count and revenue
db.bookings.aggregate([
  {
    $group: {
      _id: "$status",
      totalBookings: { $sum: 1 },
      totalRevenue: { $sum: "$amount" }
    }
  },
  { $sort: { totalBookings: -1 } }
]);

// 11.2 - Group bookings by turfId to see total reservations and revenue per turf
db.bookings.aggregate([
  {
    $group: {
      _id: "$turfId",
      reservationCount: { $sum: 1 },
      totalRevenue: { $sum: "$amount" }
    }
  },
  { $sort: { reservationCount: -1 } }
]);

// STEP 12: Demonstrate $lookup (join bookings with users and turfs)
db.bookings.aggregate([
  {
    $lookup: {
      from: "users",
      localField: "userId",
      foreignField: "_id",
      as: "customer"
    }
  },
  {
    $lookup: {
      from: "turfs",
      localField: "turfId",
      foreignField: "_id",
      as: "turf"
    }
  },
  {
    $project: {
      _id: 1,
      demoCode: 1,
      bookingDate: 1,
      startTime: 1,
      endTime: 1,
      amount: 1,
      status: 1,
      "customer.name": 1,
      "customer.email": 1,
      "turf.name": 1,
      "turf.sportType": 1,
      "turf.city": 1
    }
  }
]);

// STEP 13: Query optimization & explain plan executionStats
db.bookings.find({
  status: "confirmed",
  bookingDate: {
    $gte: new Date("2026-01-01"),
    $lt: new Date("2026-12-31")
  }
}).explain("executionStats");
