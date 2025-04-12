import pika
import json
import time
from datetime import datetime
from concurrent.futures import ThreadPoolExecutor
from modules.MongoDBClient import MongoDBClient
from modules.TaskManager import TaskManager  # ✅ NOVO


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
        self.mongodb_client = MongoDBClient()
        self.task_manager = TaskManager()
        self.connect_to_rabbitmq()
        self.publisher_connection, self.publisher_channel = self.create_publisher_connection()

    def connect_to_rabbitmq(self):
        while True:
            try:
                self.connection = pika.BlockingConnection(
                    pika.ConnectionParameters(
                        host=self.host,
                        heartbeat=30,  # Mantém a conexão ativa
                        blocked_connection_timeout=7200  # Evita bloqueios longos
                    )
                )
                self.channel = self.connection.channel()

                self.channel.exchange_declare(exchange=self.task_exchange, exchange_type='direct', durable=True)
                self.channel.queue_declare(queue=self.task_queue, durable=True)
                self.channel.queue_bind(queue=self.task_queue, exchange=self.task_exchange,
                                        routing_key=self.task_routing_key)

                self.channel.exchange_declare(exchange=self.status_exchange, exchange_type='direct', durable=True)

                self.channel.basic_qos(prefetch_count=5)

                print(f"Connected to RabbitMQ - Task Exchange: {self.task_exchange}, Queue: {self.task_queue}")
                return
            except pika.exceptions.AMQPConnectionError as e:
                print(f"RabbitMQ connection failed: {e}. Retrying in 5 seconds...")
                time.sleep(5)  # Espera antes de tentar novamente

    def create_publisher_connection(self):
        connection = pika.BlockingConnection(pika.ConnectionParameters(host=self.host))
        channel = connection.channel()
        return connection, channel

    def consume_messages(self):
        def callback(ch, method, properties, body):
            try:
                message = json.loads(body)
                print(f"\n Request : {message}")
                task_id = message.get("taskId", "No Task ID")
                title = message.get("title")
                algorithm_name = message.get("algorithm", "CSP Scheduling")

                print(f"\n[Received Task] Task ID: {task_id}")

                self.executor.submit(self.handle_task_processing, task_id, title, algorithm_name)
                ch.basic_ack(delivery_tag=method.delivery_tag)
            except Exception as e:
                print(f"Error processing message: {e}")
                ch.basic_nack(delivery_tag=method.delivery_tag, requeue=True)

        while True:
            try:
                print("Waiting for messages. To exit, press CTRL+C.")
                self.channel.basic_consume(queue=self.task_queue, on_message_callback=callback, auto_ack=False)
                self.channel.start_consuming()
            except (pika.exceptions.StreamLostError, pika.exceptions.AMQPConnectionError) as e:
                print(f"RabbitMQ error: {e}. Reconnecting...")
                self.connect_to_rabbitmq()
            except KeyboardInterrupt:
                print("Shutting down...")
                self.close_connection()
                break

    def handle_task_processing(self, task_id, title, algorithm_name):
        self.send_task_status(task_id, "IN_PROGRESS")
        try:
            print(f"[RabbitMQClient] Delegando execução da task {task_id} para TaskManager...")
            schedule_data = self.task_manager.run_task(task_id, title, algorithm_name)

            self.mongodb_client.insert_schedule(
                data=schedule_data,
                title=title,
                algorithm=algorithm_name
            )

            print(f"[RabbitMQClient] Schedule complete for Task ID: {task_id}")
            self.send_task_status(task_id, "COMPLETED")
        except Exception as e:
            print(f"Error during schedule execution: {e}")
            self.send_task_status(task_id, "FAILED")

    def send_task_status(self, task_id, status):
        task_status_message = {
            "taskId": task_id,
            "status": status,
            "updatedAt": datetime.now().isoformat()
        }

        while True:
            try:
                self.publisher_channel.basic_publish(
                    exchange=self.status_exchange,
                    routing_key=self.status_routing_key,
                    body=json.dumps(task_status_message),
                    properties=pika.BasicProperties(content_type='application/json', delivery_mode=2)
                )
                print(f"Sent task status update: {task_status_message}")
                break  # Sucesso, então sair do loop
            except pika.exceptions.AMQPConnectionError as e:
                print(f"[send_task_status] Connection error while sending status: {e}. Retrying in 5 seconds...")
                time.sleep(5)
                self.publisher_connection, self.publisher_channel = self.create_publisher_connection()
            except Exception as e:
                print(f"[send_task_status] Unexpected error: {e}. Retrying in 5 seconds...")
                time.sleep(5)

    def close_connection(self):
        self.executor.shutdown(wait=True)
        self.connection.close()
        self.publisher_connection.close()
        print("Connections closed.")


if __name__ == "__main__":
    client = RabbitMQClient()
    client.consume_messages()
