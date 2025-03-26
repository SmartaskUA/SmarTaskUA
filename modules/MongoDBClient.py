from pymongo import MongoClient, errors
import os


class MongoDBClient:
    def __init__(self, db_name="mydatabase", employees_collection="employees", schedules_collection="schedules"):
        """Initialize connection to MongoDB."""
        try:
            # MongoDB connection parameters (change if needed)
            self.host = os.getenv("MONGO_HOST", "localhost")
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
            print(schedule["title"], ", ",schedule["algorithm"])
        return schedules

    def close_connection(self):
        """Close the connection to the MongoDB database."""
        self.client.close()
        print("Closed connection to MongoDB")


if __name__ == "__main__":
    # Create a MongoDB client with the correct database "mydatabase"
    mongo_client = MongoDBClient()

    # Fetch and display employees and schedules
    print("\n------------Employees-----------------------\n")
    mongo_client.fetch_employees()

    print("\n------------Schedules-----------------------\n")
    mongo_client.fetch_schedules()

    # Close the connection when done
    mongo_client.close_connection()
