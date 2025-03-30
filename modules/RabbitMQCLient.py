import pika
import json
import time
from datetime import datetime
from concurrent.futures import ThreadPoolExecutor
from MongoDBClient import MongoDBClient

class RabbitMQClient:
    def __init__(self, host='localhost', task_exchange='task-exchange', status_exchange='status-exchange',
                 task_queue='task-queue', task_routing_key='task-routing-key', status_routing_key='status-routing-key'):
        self.host = host
        self.task_exchange = task_exchange
        self.status_exchange = status_exchange
        self.task_queue = task_queue
        self.task_routing_key = task_routing_key
        self.status_routing_key = status_routing_key
        self.executor = ThreadPoolExecutor(max_workers=5)

        # Initialize MongoDBClient
        self.mongodb_client = MongoDBClient()

        # Establish RabbitMQ connections
        self.connect_to_rabbitmq()
        self.publisher_connection, self.publisher_channel = self.create_publisher_connection()

    def connect_to_rabbitmq(self):
        """Establish connection to RabbitMQ with auto-reconnect."""
        while True:
            try:
                self.connection = pika.BlockingConnection(pika.ConnectionParameters(host=self.host))
                self.channel = self.connection.channel()

                # Declare the task exchange and queue
                self.channel.exchange_declare(exchange=self.task_exchange, exchange_type='direct', durable=True)
                self.channel.queue_declare(queue=self.task_queue, durable=True)
                self.channel.queue_bind(queue=self.task_queue, exchange=self.task_exchange, routing_key=self.task_routing_key)

                # Declare a separate exchange for status updates
                self.channel.exchange_declare(exchange=self.status_exchange, exchange_type='direct', durable=True)

                print(f"Connected to RabbitMQ - Task Exchange: {self.task_exchange}, Queue: {self.task_queue}")
                break
            except pika.exceptions.AMQPConnectionError as e:
                print(f"RabbitMQ connection failed: {e}. Retrying in 5 seconds...")
                time.sleep(5)

    def create_publisher_connection(self):
        """Create a separate persistent connection and channel for publishing messages."""
        connection = pika.BlockingConnection(pika.ConnectionParameters(host=self.host))
        channel = connection.channel()
        return connection, channel

    def consume_messages(self):
        """Consume messages with error handling."""
        def callback(ch, method, properties, body):
            try:
                message = json.loads(body)
                task_id = message.get("taskId", "No Task ID")

                print(f"\n[Received Task] Task ID: {task_id}")

                # Update status to IN_PROGRESS
                self.send_task_status(task_id, "IN_PROGRESS")

                # Start schedule generation asynchronously
                self.executor.submit(self.simulate_schedule_generation, task_id)

                # Acknowledge message
                ch.basic_ack(delivery_tag=method.delivery_tag)
            except Exception as e:
                print(f"Error processing message: {e}")
                ch.basic_nack(delivery_tag=method.delivery_tag, requeue=True)

        while True:
            try:
                print("Waiting for messages. To exit, press CTRL+C.")
                self.channel.basic_consume(queue=self.task_queue, on_message_callback=callback, auto_ack=False)
                self.channel.start_consuming()
            except pika.exceptions.StreamLostError as e:
                print(f"Stream lost: {e}. Reconnecting...")
                self.connect_to_rabbitmq()
            except pika.exceptions.AMQPConnectionError as e:
                print(f"Connection error: {e}. Reconnecting...")
                self.connect_to_rabbitmq()
            except KeyboardInterrupt:
                print("Shutting down...")
                self.close_connection()
                break

    def simulate_schedule_generation(self, task_id):
        """Simulate schedule generation."""
        print(f"Processing schedule for Task ID: {task_id}")
        time.sleep(10)  # Simulate processing time
        print(f"Schedule complete for Task ID: {task_id}")

        # Send completion status
        self.send_task_status(task_id, "COMPLETED")

    def send_task_status(self, task_id, status):
        """Send task status using a separate exchange."""
        try:
            task_status_message = {
                "taskId": task_id,
                "status": status,
                "updatedAt": datetime.now().isoformat()
            }

            self.publisher_channel.basic_publish(
                exchange=self.status_exchange,  # Enviando para um exchange separado
                routing_key=self.status_routing_key,
                body=json.dumps(task_status_message),
                properties=pika.BasicProperties(content_type='application/json', delivery_mode=2)
            )
            print(f"Sent task status update: {task_status_message}")
        except pika.exceptions.AMQPConnectionError as e:
            print(f"Error sending status: {e}. Reconnecting...")
            self.publisher_connection, self.publisher_channel = self.create_publisher_connection()

    def close_connection(self):
        """Close RabbitMQ connections and shutdown executor."""
        self.executor.shutdown(wait=True)
        self.connection.close()
        self.publisher_connection.close()
        print("Connections closed.")

if __name__ == "__main__":
    client = RabbitMQClient()
    client.consume_messages()
