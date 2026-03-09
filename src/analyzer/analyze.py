from datetime import datetime, date
import time
import pika
import json
import os
from pymongo import MongoClient
from kpiVerification import analyze as verifyKpis                                                        
from kpiVerification_unified_v3 import analyze as verifyKpis_Unified
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
def detect_schedule_format(file_path, mins_text=None):
    found_shift = False
    found_hours = False
    found_half_hour = False
    found_off = False
    found_zero = False

    pattern_shift = re.compile(r'^\s*[MTN]\s*[_-]\s*[A-Za-z]\s*$', re.IGNORECASE)
    pattern_hours = re.compile(
        r'^\s*\d{1,2}(?:\.\d+)?\s*-\s*\d{1,2}(?:\.\d+)?(?:\s*-\s*\d{1,2}(?:\.\d+)?)?\s*[_-]\s*[A-Za-z]\s*$',
        re.IGNORECASE
    )
    half_hour_marker = re.compile(r'(\d+\.\d)|(\d{1,2}:\d{2})')

    def scan_values(df):
        nonlocal found_shift, found_hours, found_half_hour, found_off, found_zero
        for col in df.columns:
            for val in df[col].dropna():
                text = str(val).strip()
                if not text:
                    continue
                upper = text.upper()
                if upper == "OFF":
                    found_off = True
                    continue
                if text == "0":
                    found_zero = True
                    continue
                if pattern_shift.match(text):
                    found_shift = True
                    continue
                if pattern_hours.match(text):
                    found_hours = True
                if half_hour_marker.search(text):
                    found_hours = True
                    found_half_hour = True

    try:
        df = pd.read_csv(file_path, encoding="ISO-8859-1", dtype=str, nrows=200)
        scan_values(df)
        if not (found_shift or found_hours):
            df = pd.read_csv(file_path, encoding="ISO-8859-1", dtype=str)
            scan_values(df)
    except Exception as e:
        print(f"[detect_schedule_format] Failed to analyze {file_path}: {e}")

    # Fallback: infer from minimums template content (if present)
    if mins_text:
        mins_lower = str(mins_text).lower()
        mins_has_turno = "turno" in mins_lower
        mins_has_hora = "hora" in mins_lower
        mins_has_half = bool(re.search(r'\d{1,2}:\d{2}', mins_lower) or re.search(r'\d+\.\d', mins_lower))
        if mins_has_half and not found_shift:
            found_half_hour = True
            found_hours = True
        if mins_has_hora and not found_shift:
            found_hours = True
        if mins_has_turno and not found_hours:
            found_shift = True

    if not (found_shift or found_hours):
        if found_off and not found_zero:
            found_hours = True
        elif found_zero and not found_off:
            found_shift = True

    if found_shift and found_hours:
        print("[WARN] Mixed shift/hour markers detected; defaulting to shifts.")
        problem_type = "shifts"
    elif found_shift:
        problem_type = "shifts"
    elif found_hours:
        problem_type = "hours"
    else:
        problem_type = "unknown"

    hour_granularity = None
    if problem_type == "hours":
        hour_granularity = "30min" if found_half_hour else "hour"

    print(
        f"[DEBUG] Detected markers: shifts={found_shift}, hours={found_hours}, "
        f"half_hour={found_half_hour}, off={found_off}, zero={found_zero}"
    )

    return problem_type, hour_granularity

def select_kpi_verifier(problem_type, hour_granularity):                                                 
    if problem_type == "hours":                                                                          
        # Retorna uma função wrapper que passa a granularidade correta                                   
        granularity = 30 if hour_granularity == "30min" else 60                                          
        return lambda f, h, m, e, y: verifyKpis_Unified(f, h, m, e, y, granularity=granularity)          
    return verifyKpis

def normalize_schedule_type(value):
    if not value:
        return None
    normalized = str(value).strip().lower()
    if normalized in {"turno", "turnos", "shift", "shifts"}:
        return "shifts"
    if normalized in {"hora", "horas", "hour", "hours"}:
        return "hours"
    return None

def normalize_hour_granularity(value):
    if not value:
        return None
    normalized = str(value).strip().lower()
    if normalized in {"30min", "30-min", "30", "half", "half-hour", "half_hour"}:
        return "30min"
    if normalized in {"hour", "hours", "1h", "1hr", "60min", "60"}:
        return "hour"
    return None

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
        rules = message.get("rules")
        if isinstance(rules, str):
            try:
                rules = json.loads(rules)
            except Exception:
                print("[WARN] Failed to parse rules payload for KPI analysis; ignoring.")
                rules = None

        if not files:
            print("[ERROR] No files received.")
            ch.basic_ack(delivery_tag=method.delivery_tag)
            return

        print(f"[Comparison] Processing requestId={request_id}")
        print(f"[DEBUG] Files = {files}")

        # 🔍 Detectar tipo de problema (usa o primeiro ficheiro)
        problem_type, hour_granularity = detect_schedule_format(files[0], mins)
        schedule_type_override = normalize_schedule_type(
            message.get("scheduleType") or message.get("schedule_type")
        )
        hour_granularity_override = normalize_hour_granularity(
            message.get("hourGranularity") or message.get("hour_granularity")
        )

        if schedule_type_override:
            problem_type = schedule_type_override
            if problem_type != "hours":
                hour_granularity = None
        if hour_granularity_override and problem_type == "hours":
            hour_granularity = hour_granularity_override

        if problem_type == "unknown":
            print("[WARN] Unknown schedule type; defaulting to shifts.")
            problem_type = "shifts"
            hour_granularity = None
        print(f"[DEBUG] Detected problem type: {problem_type} (hour granularity: {hour_granularity})")
        verifier = select_kpi_verifier(problem_type, hour_granularity)


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
            else:
                print(f"[DEBUG] Preparing holidays for shifts verification for year {year}")
                holidays = hl.country_holidays("PT", years=[year])

            if problem_type == "shifts":
                result = verifier(files[0], holidays, mins, employees, year, rules=rules)
            else:
                result = verifier(files[0], holidays, mins, employees, year)

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

            # 1️⃣ PRIMEIRO: Calcular resultados para todos os ficheiros
            results = {}
            print(f"[DEBUG] Running KPI comparison for {len(files)} files...")

            for f in files:
                print(f"[DEBUG] Comparing file: {f}")
                results[f] = verifier(f, holidays, mins, employees, year)

            print("[DEBUG] KPI comparison results:", results)

            # 2️⃣ DEPOIS: Enviar resultado via WebSocket
            try:
                websocket_channel = ch.connection.channel()
                websocket_channel.exchange_declare(exchange="websocket-exchange", exchange_type="fanout", durable=True)

                payload = json.dumps({
                    "requestId": request_id,
                    "result": results
                })

                websocket_channel.basic_publish(
                    exchange="websocket-exchange",
                    routing_key="",
                    body=payload
                )

                print(f"[WebSocket] Sent result for requestId={request_id} to websocket-exchange")
            except Exception as e:
                print(f"[ERROR] Failed to send WebSocket message: {e}")

            # 3️⃣ POR FIM: Guardar no MongoDB
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
