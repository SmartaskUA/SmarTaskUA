import pika
import json

class RabbitMQClient:
    def __init__(self, host='localhost', exchange='task-exchange', queue='task-queue', routing_key='task-routing-key'):
        self.host = host
        self.exchange = exchange
        self.queue = queue
        self.routing_key = routing_key

        # Connect to RabbitMQ without redeclaring the exchange and queue
        self.connection = pika.BlockingConnection(pika.ConnectionParameters(host=self.host))
        self.channel = self.connection.channel()

    def consume_messages(self):
        """Consume messages from the queue and print task and request info separately."""
        def callback(ch, method, properties, body):
            print("\n[Received message]")

            # Decode the message (expected to be JSON)
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
            except json.JSONDecodeError:
                print("Failed to decode message as JSON")

        # Start consuming messages (note: queue must already exist)
        print("Waiting for messages. To exit, press CTRL+C.")
        self.channel.basic_consume(queue=self.queue, on_message_callback=callback, auto_ack=True)
        self.channel.start_consuming()

    def close_connection(self):
        """Close the RabbitMQ connection."""
        self.connection.close()

# Instantiate and run the consumer
if __name__ == "__main__":
    rabbitmq_client = RabbitMQClient()
    try:
        rabbitmq_client.consume_messages()
    except KeyboardInterrupt:
        print("\nClosing connection...")
        rabbitmq_client.close_connection()
