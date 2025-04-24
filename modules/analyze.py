import pika
import json
import os
from pymongo import MongoClient
from algorithm.kpiComparison import analyze as compareKpis
from algorithm.kpiVerification import analyze as verifyKpis

holidays = [1, 107, 109, 114, 121, 161, 170, 226, 276, 303, 333, 340, 357]

mongo = MongoClient("mongodb://mongo:27017/")
db = mongo["mydatabase"]
comparison_results = db["comparisons"]
verification_results = db["verifications"]

def callback(ch, method, properties, body):
    try:
        try:
            print("[DEBUG] Raw body:", body)
            message = json.loads(body.decode('utf-8'))
        except UnicodeDecodeError as e:
            print(f"[Comparison] Failed to decode message body: {e}")
            ch.basic_ack(delivery_tag=method.delivery_tag)
            return

        request_id = message["requestId"]
        files = message.get("files", [])

        if not files:
            print("[ERROR] No files received.")
            ch.basic_ack(delivery_tag=method.delivery_tag)
            return

        print(f"[Comparison] Processing requestId={request_id}")
        print(f"[DEBUG] Files = {files}")

        if len(files) == 1:
            # Verification mode (one file)
            result = verifyKpis(files[0], holidays)
            verification_results.insert_one({
                "requestId": request_id,
                "status": "done",
                "file": files[0],
                "result": result
            })
            print(f"[Verification] Result saved for requestId={request_id}")
            os.remove(files[0])

        elif len(files) >= 2:
            # Comparison mode (multiple files)
            results = {}
            for f in files:
                results[f] = compareKpis(f, holidays)
                os.remove(f)

            comparison_results.insert_one({
                "requestId": request_id,
                "status": "done",
                "files": files,
                "result": results
            })
            print(f"[Comparison] Results saved for requestId={request_id}")

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
