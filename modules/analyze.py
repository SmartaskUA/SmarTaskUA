import pika
import json
import os
from pymongo import MongoClient
from algorithm.kpiComparison import analyze as compareKpis
from algorithm.kpiVerification import analyze as verifyKpis
from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type
import pandas as pd
import holidays as hl
import csv
import io

mongo = MongoClient("mongodb://admin:password@mongo:27017/")
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

        request_id = message.get("requestId")
        files = message.get("files", [])
        vacs = message.get("vacationTemplate")
        mins  = message.get("minimunsTemplate")
        employees = message.get("employees", "[]")
        year = int(message.get("year", 2025))
        employees = json.loads(employees)

        if not files:
            print("[ERROR] No files received.")
            ch.basic_ack(delivery_tag=method.delivery_tag)
            return

        print(f"[Comparison] Processing requestId={request_id}")
        print(f"[DEBUG] Files = {files}")

        holidays = hl.country_holidays("PT", years=[year])
        dias_ano = pd.date_range(start=f'{year}-01-01', end=f'{year}-12-31').to_list()
        start_date = dias_ano[0].date()
        holidays = {(d - start_date).days + 1 for d in holidays}

        if len(files) == 1:
            print("[DEBUG] Running verifyKpis for file:", files[0])
            result = verifyKpis(files[0], holidays, vacs, mins, employees, year)
            print("[DEBUG] verifyKpis result:", result)
            try:
                verification_results.insert_one({
                    "requestId": request_id,
                    "status": "done",
                    "file": files[0],
                    "result": result
                })
                print(f"[Verification] Result saved for requestId={request_id}")
            except Exception as e:
                print(f"[ERROR] Failed to save verification result: {e}")
                raise

        elif len(files) >= 2:
            results = {}
            for f in files:
                print("[DEBUG] Running compareKpis for file:", f)
                results[f] = compareKpis(f, holidays, vacs, mins, employees, year)
            print("[DEBUG] compareKpis results:", results)
            try:
                comparison_results.insert_one({
                    "requestId": request_id,
                    "status": "done",
                    "files": files,
                    "result": results
                })
                print(f"[Comparison] Results saved for requestId={request_id}")
            except Exception as e:
                print(f"[ERROR] Failed to save comparison results: {e}")
                raise

        ch.basic_ack(delivery_tag=method.delivery_tag)

    except Exception as e:
        print(f"[Comparison] Error: {e}")
        ch.basic_nack(delivery_tag=method.delivery_tag, requeue=False)

@retry(
    stop=stop_after_attempt(10),
    wait=wait_exponential(multiplier=1, min=2, max=10),
    retry=retry_if_exception_type(pika.exceptions.AMQPConnectionError)
)
def connect_to_rabbitmq():
    rabbit_host = os.getenv("RABBITMQ_HOST", "localhost")
    rabbit_username = os.getenv("RABBITMQ_USERNAME", "guest")
    rabbit_password = os.getenv("RABBITMQ_PASSWORD", "guest")
    print(f"[DEBUG] Attempting to connect to RabbitMQ at {rabbit_host}")
    credentials = pika.PlainCredentials(rabbit_username, rabbit_password)
    return pika.BlockingConnection(
        pika.ConnectionParameters(
            host=rabbit_host,
            credentials=credentials
        )
    )

def start_consumer():
    print("[BOOT] Analyzer worker started and listening...")
    connection = connect_to_rabbitmq()
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