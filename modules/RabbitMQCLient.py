import pika
import json
from datetime import datetime

class RabbitMQClient:
    def __init__(self, host='localhost', exchange='task-exchange', queue='task-queue', routing_key='task-routing-key'):
        self.host = host
        self.exchange = exchange
        self.queue = queue
        self.routing_key = routing_key

        # Connect to RabbitMQ
        self.connection = pika.BlockingConnection(pika.ConnectionParameters(host=self.host))
        self.channel = self.connection.channel()

        # Declare the exchange (Direct)
        self.channel.exchange_declare(exchange=self.exchange, exchange_type='direct', durable=True)

        # Declare the queue
        self.channel.queue_declare(queue=self.queue, durable=True)

        # Bind the queue to the exchange with the routing key
        self.channel.queue_bind(queue=self.queue, exchange=self.exchange, routing_key=self.routing_key)

        print(f"Queue '{self.queue}' and exchange '{self.exchange}' are ready!")

    def consume_messages(self):
        """Consume messages from the queue and send an IN_PROGRESS status back to the queue."""

        def callback(ch, method, properties, body):
            try:
                print("\n[Received message]")
                message = json.loads(body)
                print(f"Full message: {message}")

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

                # Update task status to IN_PROGRESS and send it back to the queue
                self.send_task_status(task_id, "IN_PROGRESS")

                # Acknowledge the message
                ch.basic_ack(delivery_tag=method.delivery_tag)
            except Exception as e:
                print(f"Error processing message: {e}")
                ch.basic_nack(delivery_tag=method.delivery_tag,
                              requeue=True)  # Re-enqueue the message in case of failure

        # Start consuming messages
        print("Waiting for messages. To exit, press CTRL+C.")
        self.channel.basic_consume(queue=self.queue, on_message_callback=callback, auto_ack=False)
        try:
            self.channel.start_consuming()
        except Exception as e:
            print(f"Error in consumer: {e}")
            self.close_connection()

    def send_task_status(self, task_id, status):
        """Send the task status back to the queue."""
        task_status_message = {
            "taskId": task_id,
            "status": status,
            "updatedAt": datetime.now().isoformat()
        }

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
        print("RabbitMQ connection closed.")


if __name__ == "__main__":
    rabbitmq_client = RabbitMQClient()
    try:
        rabbitmq_client.consume_messages()
    except KeyboardInterrupt:
        print("\nClosing connection...")
        rabbitmq_client.close_connection()
