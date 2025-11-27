from datetime import datetime, date
import time
import pika
import json
import os
from pymongo import MongoClient
from algorithm.kpiComparison import analyze as compareKpis
from algorithm.kpiVerification import analyze as verifyKpis
from algorithm.kpiComparison_Hours import analyze as compareKpis_Hours
from algorithm.kpiVerification_Hours import analyze as verifyKpis_Hours
from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type
import pandas as pd
import holidays as hl
import csv
import io
import re

mongo = MongoClient("mongodb://admin:password@mongo:27017/")
db = mongo["mydatabase"]
comparison_results = db["comparisons"]
verification_results = db["verifications"]

# ------------------------------------------------------------------------
# 🔍 Helper: detectar tipo de problema (shifts vs hours)
# ------------------------------------------------------------------------
def detect_problem_type(file_path):
    try:
        df = pd.read_csv(file_path, encoding="ISO-8859-1", nrows=5)
        pattern_shift = re.compile(r'^\s*[MTN]\s*_\s*[A-Za-z]\s*$')
        pattern_hour = re.compile(r'^\s*\d{1,2}-\d{1,2}(?:-[0-9]{1,2})?[_\-][A-Za-z]\s*$')

        print(f"[DEBUG] Detecting problem type for file: {file_path}")
        print(f"[DEBUG] Pattern Shift: {pattern_shift.pattern}")
        print(f"[DEBUG] Pattern Hour: {pattern_hour.pattern}")

        for col in df.columns:
            for val in df[col].dropna():
                val = str(val).strip()
                if pattern_shift.match(val):
                    return "shifts"
                if pattern_hour.match(val):
                    return "hours"
        return "unknown"
    except Exception as e:
        print(f"[detect_problem_type] Failed to analyze {file_path}: {e}")
        return "unknown"

# ------------------------------------------------------------------------
# 📦 Callback principal
# ------------------------------------------------------------------------
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
        mins = message.get("minimunsTemplate")
        print(f"[DEBUG] Received message for requestId={request_id} with {len(files)} files.")
        print(f"[DEBUG] Minimums Template: {mins}")
        employees = message.get("employees", "[]")
        year = int(message.get("year", 2025))
        employees = json.loads(employees)

        if not files:
            print("[ERROR] No files received.")
            ch.basic_ack(delivery_tag=method.delivery_tag)
            return

        print(f"[Comparison] Processing requestId={request_id}")
        print(f"[DEBUG] Files = {files}")

        # 🔍 Detectar tipo de problema (usa o primeiro ficheiro)
        #TODO resolver problema de detecção de tipo.
        # problem_type = detect_problem_type(files[0])
        problem_type = "hours"
        print(f"[DEBUG] Detected problem type: {problem_type}")


        # -----------------------------------------------------------------
        # Caso 1️⃣: Apenas um ficheiro → KPI Verification
        # -----------------------------------------------------------------
        # -----------------------------------------------------------------

        if len(files) == 1:
            print("[DEBUG] Running KPI verification for file:", files[0])

            if problem_type == "hours":
                print(f"[DEBUG] Preparing holidays for hours verification for year {year}")
                holidays = {
                    date(2022, 1, 1): "New Year's Day", 
                    date(2022, 1, 6): 'Epiphany', 
                    date(2022, 3, 1): 'Day of Baleares', 
                    date(2022, 4, 14): 'Maundy Thursday', 
                    date(2022, 4, 15): 'Good Friday', 
                    date(2022, 5, 1): 'Labor Day', 
                    date(2022, 5, 2): 'Madrid Day', 
                    date(2022, 6, 29): 'Folga', 
                    date(2022, 7, 8): 'Folga', 
                    date(2022, 8, 15): 'Assumption Day', 
                    date(2022, 9, 8): 'Regional Holiday', 
                    date(2022, 10, 12): 'National Day',
                    date(2021, 11, 1): "All Saints' Day", 
                    date(2021, 12, 6): 'Constitution Day',
                    date(2021, 12, 8): 'Immaculate Conception',
                    date(2021, 12, 25): 'Christmas Day'
                }
                #print(f"[DEBUG] Holidays prepared: {holidays}")
                result = verifyKpis_Hours(files[0], holidays, mins, employees, year)
            else:
                print(f"[DEBUG] Preparing holidays for shifts verification for year {year}")
                holidays = hl.country_holidays("PT", years=[year])
                result = verifyKpis(files[0], holidays, mins, employees, year)

            print("[DEBUG] KPI verification result:", result)

            # 👉 Enviar resultado via WebSocket **DEPOIS** de obter o result
            try:
                websocket_channel = ch.connection.channel()
                websocket_channel.exchange_declare(exchange="websocket-exchange", exchange_type="fanout", durable=True)

                payload = json.dumps({
                    "requestId": request_id,
                    "result": result
                })

                websocket_channel.basic_publish(
                    exchange="websocket-exchange",
                    routing_key="",
                    body=payload
                )

                print(f"[WebSocket] Sent result for requestId={request_id} to websocket-exchange")
            except Exception as e:
                print(f"[ERROR] Failed to send WebSocket message: {e}")

            # Salvar no MongoDB
            try:
                verification_results.insert_one({
                    "requestId": request_id,
                    "status": "done",
                    "file": files[0],
                    "problemType": problem_type,
                    "result": result
                })
                print(f"[Verification] Result saved for requestId={request_id}")
            except Exception as e:
                print(f"[ERROR] Failed to save verification result: {e}")
                raise


        # -----------------------------------------------------------------
        # Caso 2️⃣: Dois ou mais ficheiros → KPI Comparison
        # -----------------------------------------------------------------
        elif len(files) >= 2:

            # 🔹 Definir holidays com base no problem_type
            if problem_type == "hours":
                holidays = {
                    date(2022, 1, 1): "New Year's Day", 
                    date(2022, 1, 6): 'Epiphany', 
                    date(2022, 3, 1): 'Day of Baleares', 
                    date(2022, 4, 14): 'Maundy Thursday', 
                    date(2022, 4, 15): 'Good Friday', 
                    date(2022, 5, 1): 'Labor Day', 
                    date(2022, 5, 2): 'Madrid Day', 
                    date(2022, 6, 29): 'Folga', 
                    date(2022, 7, 8): 'Folga', 
                    date(2022, 8, 15): 'Assumption Day', 
                    date(2022, 9, 8): 'Regional Holiday', 
                    date(2022, 10, 12): 'National Day',
                    date(2021, 11, 1): "All Saints' Day", 
                    date(2021, 12, 6): 'Constitution Day',
                    date(2021, 12, 8): 'Immaculate Conception',
                    date(2021, 12, 25): 'Christmas Day'
                }
            else:
                holidays = hl.country_holidays("PT", years=[year])

            # Enviar resultado via RabbitMQ para o WebSocket
            try:
                websocket_channel = ch.connection.channel()
                websocket_channel.exchange_declare(exchange="websocket-exchange", exchange_type="fanout", durable=True)
            
                payload = json.dumps({
                    "requestId": request_id,
                    "result": results if len(files) >= 2 else result
                })
            
                websocket_channel.basic_publish(
                    exchange="websocket-exchange",
                    routing_key="",
                    body=payload
                )
            
                print(f"[WebSocket] Sent result for requestId={request_id} to websocket-exchange")
            except Exception as e:
                print(f"[ERROR] Failed to send WebSocket message: {e}")
            
            results = {}
            print(f"[DEBUG] Running KPI comparison for {len(files)} files...")

            for f in files:
                print(f"[DEBUG] Comparing file: {f}")
                if problem_type == "hours":
                    results[f] = compareKpis_Hours(f, holidays, vacs, mins, employees, year)
                else:
                    results[f] = compareKpis(f, holidays, vacs, mins, employees, year)

            print("[DEBUG] KPI comparison results:", results)

            try:
                comparison_results.insert_one({
                    "requestId": request_id,
                    "status": "done",
                    "files": files,
                    "problemType": problem_type,
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

# ------------------------------------------------------------------------
# 🔁 RabbitMQ Setup
# ------------------------------------------------------------------------
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
