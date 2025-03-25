import pika
import json
import uuid
from datetime import datetime

class RabbitMQClient:
    def __init__(self, host='localhost', exchange='task-exchange', queue='task-queue', routing_key='task-routing-key'):
        self.host = host
        self.exchange = exchange
        self.queue = queue
        self.routing_key = routing_key

        # Connect to RabbitMQ and set up channel
        self.connection = pika.BlockingConnection(pika.ConnectionParameters(host=self.host))
        self.channel = self.connection.channel()

    def consume_messages(self):
        """Consume messages from the queue and send an IN_PROGRESS status back to the queue."""
        def callback(ch, method, properties, body):
            print("\n[Received message]")

            # Decode the incoming message (expected to be JSON)
            try:
                message = json.loads(body)
                print(f"Full message: {message}")

                # Extract task and ScheduleRequest information
                task_id = message.get("taskId", "No Task ID")
                print(f"Task ID: {task_id}")

                schedule_request = {
                    "init": message.get("init"),
                    "end": message.get("end"),
                    "algorithm": message.get("algorithm"),
                    "title": message.get("title"),
                    "maxTime": message.get("maxTime"),
                    "requestedAt": message.get("requestedAt"),
                }
                print(f"ScheduleRequest details: {schedule_request}")
                # todo : should manage the generation of the request here

                # Update task status to IN_PROGRESS and send it back to the queue
                self.send_task_status(task_id, "IN_PROGRESS")

            except json.JSONDecodeError:
                print("Failed to decode message as JSON")

        # Start consuming messages
        print("Waiting for messages. To exit, press CTRL+C.")
        self.channel.basic_consume(queue=self.queue, on_message_callback=callback, auto_ack=True)
        self.channel.start_consuming()

    def send_task_status(self, task_id, status):
        """Send the task status (IN_PROGRESS) back to the queue."""
        task_status_message = {
            "taskId": task_id,
            "status": status,
            "updatedAt": datetime.now().isoformat()  # Add timestamp for when status was updated
        }

        # Convert the task status to JSON and send to the queue
        self.channel.basic_publish(
            exchange=self.exchange,
            routing_key=self.routing_key,
            body=json.dumps(task_status_message),
            properties=pika.BasicProperties(
                content_type='application/json',
                delivery_mode=2,  # Make message persistent
            ),
        )
        print(f"Sent task status update: {task_status_message}")

    def close_connection(self):
        """Close the RabbitMQ connection."""
        self.connection.close()


if __name__ == "__main__":
    rabbitmq_client = RabbitMQClient()
    try:
        rabbitmq_client.consume_messages()
    except KeyboardInterrupt:
        print("\nClosing connection...")
        rabbitmq_client.close_connection()
