from pymongo import MongoClient, errors
import os
import datetime
import pytz
import csv
from datetime import datetime

class MongoDBClient:
    def __init__(self, db_name="mydatabase", employees_collection="employees", schedules_collection="schedules"):
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

    # Insert a new schedule from 'schedule.csv'
    print("\n------------Inserting New Schedule from CSV-----------------------\n")
    try:
        csv_file = "schedule.csv"
        schedule_data = []

        with open(csv_file, mode="r") as file:
            csv_reader = csv.reader(file)
            for row in csv_reader:
                schedule_data.append(row)  # Each row becomes a list of strings

        # Insert the new schedule into the database with title, algorithm, and timestamp
        title = "S5"
        algorithm = "Imported Algorithm"
        timestamp = datetime.now().isoformat()  # Adding timestamp
        inserted_id = mongo_client.insert_schedule(data=schedule_data, title=title, algorithm=algorithm,
                                                   timestamp=timestamp)
        print(f"New schedule inserted with ID: {inserted_id}")

    except FileNotFoundError:
        print(f"Error: The file '{csv_file}' was not found.")
    except Exception as e:
        print(f"An error occurred while processing the CSV file: {e}")

    # Close the connection when done
    mongo_client.close_connection()
