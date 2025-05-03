from pymongo import MongoClient, errors
import os
import datetime
import pytz
import csv
from datetime import datetime

class MongoDBClient:
    def __init__(self, db_name="mydatabase", employees_collection="employees",
                 schedules_collection="schedules"
                 ,vacations_collection="vacations"
                 ,reference_collection="reference"):
        """Initialize connection to MongoDB."""
        try:
            # MongoDB connection parameters (change if needed)
            self.host = os.getenv("MONGO_HOST", "mongo")
            self.port = int(os.getenv("MONGO_PORT", 27017))
            self.username = os.getenv("MONGO_INITDB_ROOT_USERNAME", "admin")
            self.password = os.getenv("MONGO_INITDB_ROOT_PASSWORD", "password")

            # Create MongoDB client and connect to the database named "mydatabase"
            self.client = MongoClient(
                host=self.host,
                port=self.port,
                username=self.username,
                password=self.password,
                authSource="admin"  # Authenticate against the admin DB
            )
            self.db = self.client[db_name]
            self.employees_collection = self.db[employees_collection]
            self.schedules_collection = self.db[schedules_collection]
            self.vacations_collection = self.db[vacations_collection]
            self.reference_collection = self.db[reference_collection]
            print(f"Connected to MongoDB database '{db_name}'")

        except errors.PyMongoError as e:
            print(f"Failed to connect to MongoDB: {e}")

    def fetch_employees(self):
        """Fetch all employees from the employees collection."""
        employees = list(self.employees_collection.find())
        print(f"Retrieved {len(employees)} employees.")
        for employee in employees:
            print(employee)
        return employees

    def fetch_schedules(self):
        """Fetch all schedules from the schedules collection."""
        schedules = list(self.schedules_collection.find())
        print(f"Retrieved {len(schedules)} schedules.")
        for schedule in schedules:
            print(schedule["title"], ", ", schedule["algorithm"])
        return schedules

    def insert_schedule(self, data, title, algorithm, timestamp=None):
        """Insert a new schedule document into the schedules collection."""
        try:
            # Convert timestamp to datetime object if it's a string and ensure timezone awareness.
            timestamp = timestamp if isinstance(timestamp, datetime) else datetime.now(tz=pytz.UTC)

            schedule_document = {
                "data": data,
                "title": title,
                "algorithm": algorithm,
                "timestamp": timestamp  # Store as datetime object for proper ISODate in MongoDB
            }
            result = self.schedules_collection.insert_one(schedule_document)
            print(f"Schedule inserted successfully with ID: {result.inserted_id}")
            return result.inserted_id

        except errors.PyMongoError as e:
            print(f"Failed to insert schedule: {e}")
            return None

    def fetch_vacation_by_name(self, name):
        """Fetch a vacation template by its name."""
        try:
            result = self.vacations_collection.find_one({"name": name})
            if result:
                print(f"Found vacation template: {result}")
            else:
                print(f"No vacation template found with name '{name}'")
            return result
        except errors.PyMongoError as e:
            print(f"Failed to fetch vacation by name: {e}")
            return None

    def fetch_reference_by_name(self, name):
        """Fetch a reference template by its name."""
        try:
            result = self.reference_collection.find_one({"name": name})
            if result:
                print(f"Found reference template: {result}")
            else:
                print(f"No reference template found with name '{name}'")
            return result
        except errors.PyMongoError as e:
            print(f"Failed to fetch reference by name: {e}")
            return None

    def close_connection(self):
        """Close the connection to the MongoDB database."""
        self.client.close()
        print("Closed connection to MongoDB")


# NOTE : use this main only for test porpuse :
if __name__ == "__main__":
    # Create a MongoDB client with the correct database "mydatabase"
    mongo_client = MongoDBClient()

    print("\n------------Employees-----------------------\n")
    mongo_client.fetch_employees()

    print("\n------------Schedules-----------------------\n")
    mongo_client.fetch_schedules()

    print("\n------------Fetching Vacation Template by name='v1'-----------------------\n")
    mongo_client.fetch_vacation_by_name("v1")

    print("\n------------Fetching Reference Template by name='m1'-----------------------\n")
    mongo_client.fetch_reference_by_name("m1")
    # Close the connection when done
    mongo_client.close_connection()
