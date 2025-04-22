import pika
import json
from pymongo import MongoClient
from algorithm.kpiComparison import analyze
import os

holidays = [1, 107, 109, 114, 121, 161, 170, 226, 276, 303, 333, 340, 357]

mongo = MongoClient("mongodb://mongo:27017/")
db = mongo["mydatabase"]
comparison_results = db["comparisons"]

def callback(ch, method, properties, body):
    try:
        message = json.loads(body)
        request_id = message["requestId"]
        file1 = message["file1Path"]
        file2 = message["file2Path"]

        print(f"[DEBUG] file1 = {file1}")
        print(f"[DEBUG] file2 = {file2}")


        print(f"[Comparison] Processing requestId={request_id}")

        result1 = analyze(file1, holidays)
        result2 = analyze(file2, holidays)

        result_doc = {
            "requestId": request_id,
            "status": "done",
            "file1": file1,
            "file2": file2,
            "result": {
                "file1": result1,
                "file2": result2
            }
        }

        comparison_results.insert_one(result_doc)
        print(f"[Comparison] Result saved for requestId={request_id}")

        os.remove(file1)
        os.remove(file2)

        ch.basic_ack(delivery_tag=method.delivery_tag)
    except Exception as e:
        print(f"[Comparison] Error: {e}")
        ch.basic_nack(delivery_tag=method.delivery_tag, requeue=False)

def start_consumer():
    rabbit_host = os.getenv("rabbitmq", "localhost")
    connection = pika.BlockingConnection(pika.ConnectionParameters(rabbit_host))
    channel = connection.channel()
    channel.exchange_declare(
        exchange="comparison-exchange",
        exchange_type="direct",
        durable=True
    )
    channel.queue_declare(queue="comparison-queue", durable=True)
    channel.queue_bind(
        exchange="comparison-exchange",
        queue="comparison-queue",
        routing_key="comparison-queue"
    )
    channel.basic_qos(prefetch_count=1)
    channel.basic_consume(queue="comparison-queue", on_message_callback=callback)
    print("[Comparison] Waiting for messages...")
    channel.start_consuming()

if __name__ == "__main__":
    start_consumer()
