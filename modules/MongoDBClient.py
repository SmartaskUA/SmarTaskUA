from pymongo import MongoClient
from pymongo.errors import ConnectionError
import os


class MongoDBClient:
    def __init__(self, db_name="smartask_db", collection_name="task_status"):
        """Initialize connection to MongoDB."""
        try:
            # MongoDB connection parameters (change if needed)
            self.host = os.getenv("MONGO_HOST", "localhost")
            self.port = int(os.getenv("MONGO_PORT", 27017))
            self.username = os.getenv("MONGO_INITDB_ROOT_USERNAME", "admin")
            self.password = os.getenv("MONGO_INITDB_ROOT_PASSWORD", "password")

            # Create MongoDB client and connect to the database
            self.client = MongoClient(
                host=self.host,
                port=self.port,
                username=self.username,
                password=self.password,
                authSource="admin"  # Authenticate against the admin DB
            )
            self.db = self.client[db_name]
            self.collection = self.db[collection_name]
            print(f"Connected to MongoDB database '{db_name}' and collection '{collection_name}'")

        except ConnectionError as e:
            print(f"Failed to connect to MongoDB: {e}")

    def insert_task_status(self, task_status):
        """Insert a task status document into the collection."""
        result = self.collection.insert_one(task_status)
        print(f"Inserted task with ID: {result.inserted_id}")
        return result.inserted_id

    def get_task_status_by_id(self, task_id):
        """Retrieve a task status document by taskId."""
        task_status = self.collection.find_one({"taskId": task_id})
        if task_status:
            print(f"Found task status: {task_status}")
        else:
            print(f"No task status found with taskId: {task_id}")
        return task_status

    def update_task_status(self, task_id, new_status):
        """Update the status of a task by taskId."""
        result = self.collection.update_one(
            {"taskId": task_id},
            {"$set": {"status": new_status}}
        )
        if result.matched_count > 0:
            print(f"Updated task status for taskId '{task_id}' to '{new_status}'")
        else:
            print(f"No task status found to update for taskId: {task_id}")
        return result.modified_count

    def get_all_task_statuses(self):
        """Retrieve all task status documents."""
        task_statuses = list(self.collection.find())
        print(f"Retrieved {len(task_statuses)} task statuses")
        return task_statuses

    def delete_task_status(self, task_id):
        """Delete a task status document by taskId."""
        result = self.collection.delete_one({"taskId": task_id})
        if result.deleted_count > 0:
            print(f"Deleted task status with taskId: {task_id}")
        else:
            print(f"No task status found to delete for taskId: {task_id}")
        return result.deleted_count

    def close_connection(self):
        """Close the connection to the MongoDB database."""
        self.client.close()
        print("Closed connection to MongoDB")


if __name__ == "__main__":
    # Example usage
    mongo_client = MongoDBClient()

    # Sample task status to insert
    task_status = {
        "taskId": "12345-abcde",
        "status": "PENDING",
        "createdAt": "2025-03-30T10:00:00",
        "updatedAt": "2025-03-30T10:15:00"
    }

    # Perform some CRUD operations
    mongo_client.insert_task_status(task_status)
    mongo_client.get_task_status_by_id("12345-abcde")
    mongo_client.update_task_status("12345-abcde", "IN_PROGRESS")
    mongo_client.get_all_task_statuses()
    mongo_client.delete_task_status("12345-abcde")

    # Close the connection when done
    mongo_client.close_connection()
