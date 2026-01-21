import pika
import json
import os
import re
import sys
import threading
import time
from datetime import datetime
from concurrent.futures import ThreadPoolExecutor
from MongoDBClient import MongoDBClient
from TaskManager import TaskManager


class ThreadLocalStream:
    def __init__(self, base_stream):
        self._base_stream = base_stream
        self._local = threading.local()

    def set_thread_file(self, file_obj):
        self._local.file_obj = file_obj

    def clear_thread_file(self):
        self._local.file_obj = None

    def write(self, data):
        if data is None:
            return
        if isinstance(data, bytes):
            data = data.decode(self.encoding, errors="replace")
        file_obj = getattr(self._local, "file_obj", None)
        if file_obj is not None:
            file_obj.write(data)
            file_obj.flush()
        self._base_stream.write(data)
        self._base_stream.flush()

    def flush(self):
        file_obj = getattr(self._local, "file_obj", None)
        if file_obj is not None:
            file_obj.flush()
        self._base_stream.flush()

    def isatty(self):
        return self._base_stream.isatty()

    def fileno(self):
        return self._base_stream.fileno()

    @property
    def encoding(self):
        return getattr(self._base_stream, "encoding", "utf-8")

    def __getattr__(self, name):
        return getattr(self._base_stream, name)


class RabbitMQClient:
    def __init__(self, host='rabbitmq', task_exchange='task-exchange', status_exchange='status-exchange',
                 task_queue='task-queue', task_routing_key='task-routing-key', status_routing_key='status-routing-key'):
        if isinstance(sys.stdout, ThreadLocalStream):
            self.stdout_router = sys.stdout
        else:
            self.stdout_router = ThreadLocalStream(sys.stdout)
            sys.stdout = self.stdout_router

        if isinstance(sys.stderr, ThreadLocalStream):
            self.stderr_router = sys.stderr
        else:
            self.stderr_router = ThreadLocalStream(sys.stderr)
            sys.stderr = self.stderr_router

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

                # Configuração da fila e exchange para "task-queue"
                self.channel.exchange_declare(exchange=self.task_exchange, exchange_type='direct', durable=True)
                self.channel.queue_declare(queue=self.task_queue, durable=True)
                self.channel.queue_bind(queue=self.task_queue, exchange=self.task_exchange,
                                        routing_key=self.task_routing_key)

                # Configuração da fila e exchange para "status-queue"
                self.channel.exchange_declare(exchange=self.status_exchange, exchange_type='direct', durable=True)
                self.channel.queue_declare(queue='status-queue', durable=True)  # Fila de status
                self.channel.queue_bind(queue='status-queue', exchange=self.status_exchange, routing_key=self.status_routing_key)  # Bind

                # Configuração de QoS (Controle de quantidade de mensagens por consumidor)
                self.channel.basic_qos(prefetch_count=5)

                print(f"Connected to RabbitMQ - Task Exchange: {self.task_exchange}, Queue: {self.task_queue}")
                print(f"Connected to RabbitMQ - Status Exchange: {self.status_exchange}, Queue: status-queue")
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
                print(f"Type of message: {type(message)}")
                print(f"Message content: {message}")

                task_id = message.get("taskId", "No Task ID")
                title = message.get("title")

                # -------- Vacation template --------
                vacation_template_name = message.get("vacationTemplate")
                fetched_vacation = self.mongodb_client.fetch_vacation_by_name(vacation_template_name)
                vacations_data = fetched_vacation.get("vacations", {}) if fetched_vacation else {}

                # Names in vacation template (first column of each row)
                vacation_rows = vacations_data if isinstance(vacations_data, list) else []
                employee_names_in_template = set()
                for row in vacation_rows:
                    if isinstance(row, list) and row:
                        name = str(row[0]).replace("\uFEFF", "").strip()
                        if name:
                            employee_names_in_template.add(name)
                print(f"[INFO] Employees in vacation template: {employee_names_in_template}")

                # -------- Minimums --------
                minimuns = message.get("minimuns")
                fetched_reference = self.mongodb_client.fetch_reference_by_name(minimuns)
                minimuns_data = fetched_reference.get("minimuns", {}) if fetched_reference else {}

                # -------- Group filtering (NEW) --------
                group_name = message.get("groupName")  # <-- comes from your producer
                print(f"[INFO] groupName in message: {group_name}")

                all_employees = self.mongodb_client.fetch_employees()

                if group_name:
                    # 1) get all teams in the group
                    teams_in_group = self.mongodb_client.fetch_teams_by_group(group_name)
                    team_emp_ids = set()
                    for t in teams_in_group:
                        for eid in t.get("employeeIds", []):
                            team_emp_ids.add(eid)

                    # 2) restrict employees to that group
                    employees_in_group = [
                        e for e in all_employees if str(e.get("_id")) in {str(eid) for eid in team_emp_ids}
                    ]
                    print(f"[INFO] Found {len(employees_in_group)} employees in group '{group_name}'.")

                    # 3) finally intersect with the vacation template names
                    employees_data = [
                        e for e in employees_in_group
                        if e.get("name", "").strip() in employee_names_in_template
                    ]

                    print(f"[INFO] Using {len(employees_data)} employees from group '{group_name}' (intersected with vacation template).")
                else:
                    employees_data = [
                        emp for emp in all_employees
                        if emp.get("name", "").strip() in employee_names_in_template
                    ]
                    print(f"[INFO] Using {len(employees_data)} employees (no groupName provided; filtered only by template).")

                year = message.get("year")
                shifts = message.get("shifts", [])
                maxTime = message.get("maxTime")
                algorithm_name = message.get("algorithm", "CSP Scheduling")
                rules = message.get("rules")

                print(f"\n[Received Task] Task ID: {task_id}")
                print(f"Algorithm: {algorithm_name}, Shifts: {shifts}, Year: {year}")

                # --- Submit task to executor ---
                self.executor.submit(
                    self.handle_task_processing,
                    task_id,
                    title,
                    algorithm_name,
                    vacations_data,
                    minimuns_data,
                    employees_data, 
                    vacation_template_name,
                    minimuns,
                    year,
                    maxTime,
                    shifts,
                    rules
                )

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

    def handle_task_processing(
            self,
            task_id,
            title,
            algorithm_name,
            vacations_data,
            minimuns_data,
            employees_data,
            vacation_template_name,
            minimuns_template_name,
            year,
            maxTime,
            shifts,
            rules
    ):
        log_file = None
        log_path = None
        try:
            log_path = self._init_task_log_path(task_id, title, algorithm_name)
            log_file = open(log_path, "w", encoding="utf-8")
            self.stdout_router.set_thread_file(log_file)
            self.stderr_router.set_thread_file(log_file)
            self._write_task_log_header(
                log_file,
                task_id,
                title,
                algorithm_name,
                vacation_template_name,
                minimuns_template_name,
                year,
                shifts,
                maxTime
            )

            self.send_task_status(task_id, "IN_PROGRESS")
            print(f"[RabbitMQClient] Delegando execução da task {task_id} para TaskManager...")
            schedule_data, elapsed_time = self.task_manager.run_task(
                task_id=task_id,
                title=title,
                algorithm_name=algorithm_name,
                vacations=vacations_data,
                minimuns=minimuns_data,
                employees=employees_data,
                maxTime=maxTime,
                year=year,
                shifts=shifts,
                rules=rules
            )

            print("ELAPSED TIME:", elapsed_time)
            metadata = {
                "scheduleName": title,
                "algorithmType": algorithm_name,
                "year": year,
                "maxTime": maxTime,
                "vacationTemplateName": vacation_template_name,
                "minimunsTemplateName": minimuns_template_name,
                "employeesTeamInfo": employees_data,
                "vacationTemplateData": vacations_data,
                "minimunsTemplateData": minimuns_data,
                "shifts": shifts,
                "rules": rules
            }

            self.mongodb_client.insert_schedule(
                data=schedule_data,
                title=title,
                algorithm=algorithm_name,
                metadata=metadata,
                elapsed_time=elapsed_time
            )

            print(f"[RabbitMQClient] Schedule complete for Task ID: {task_id}")
            self.send_task_status(task_id, "COMPLETED")

        except Exception as e:
            import traceback
            print("======== TRACEBACK ========")
            traceback.print_exc()
            print("======== END TRACE ========")
            print(f"Error during schedule execution: {e}")
            self.send_task_status(task_id, "FAILED")
        finally:
            if log_file is not None:
                try:
                    self._write_task_log_footer(log_file)
                except Exception:
                    pass
                self.stdout_router.clear_thread_file()
                self.stderr_router.clear_thread_file()
                try:
                    log_file.close()
                except Exception:
                    pass
            if log_path is not None:
                sys.__stdout__.write(f"Saved task log: {log_path}\n")
                sys.__stdout__.flush()

    def send_task_status(self, task_id, status):
        updated_at = datetime.now().isoformat()
        print("UpdatedAt:", updated_at)  # Verifica o formato da data
        task_status_message = {
            "taskId": task_id,
            "status": status,
            "updatedAt": datetime.now().isoformat()
        }
        print(json.dumps(task_status_message))

        while True:
            try:
                # Confirmação do estado da conexão do publisher
                if self.publisher_channel is None or self.publisher_channel.is_open is False:
                    print("Publisher channel is closed, creating a new connection...")
                    self.publisher_connection, self.publisher_channel = self.create_publisher_connection()

                # Envio da mensagem
                self.publisher_channel.basic_publish(
                    exchange=self.status_exchange,
                    routing_key=self.status_routing_key,
                    body=json.dumps(task_status_message),
                    properties=pika.BasicProperties(content_type='application/json', delivery_mode=2)
                )

                print(f"Sent task status update: {task_status_message}")
                break  # Sucesso, então sai do loop

            except pika.exceptions.AMQPConnectionError as e:
                print(f"[send_task_status] Connection error while sending status: {e}. Reconnecting and retrying in 5 seconds...")
                time.sleep(5)
                # Tentando reconectar
                self.publisher_connection, self.publisher_channel = self.create_publisher_connection()

            except Exception as e:
                print(f"[send_task_status] Unexpected error: {e}. Retrying in 5 seconds...")
                time.sleep(5)



    def close_connection(self):
        self.executor.shutdown(wait=True)
        self.connection.close()
        self.publisher_connection.close()
        print("Connections closed.")

    def _init_task_log_path(self, task_id, title, algorithm_name):
        base_dir = os.path.dirname(os.path.abspath(__file__))
        log_dir = os.path.join(base_dir, "logs", "scheduler-runs")
        os.makedirs(log_dir, exist_ok=True)
        safe_title = self._sanitize_log_token(title or "task")
        safe_algo = self._sanitize_log_token(algorithm_name or "algorithm")
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"{timestamp}_{safe_algo}_{safe_title}_{task_id}.log"
        return os.path.join(log_dir, filename)

    def _sanitize_log_token(self, value):
        return re.sub(r"[^A-Za-z0-9._-]+", "_", value)

    def _write_task_log_header(
        self,
        log_file,
        task_id,
        title,
        algorithm_name,
        vacation_template_name,
        minimuns_template_name,
        year,
        shifts,
        maxTime
    ):
        log_file.write("TASK LOG START\n")
        log_file.write(f"Timestamp: {datetime.now().isoformat()}\n")
        log_file.write(f"Task ID: {task_id}\n")
        log_file.write(f"Title: {title}\n")
        log_file.write(f"Algorithm: {algorithm_name}\n")
        log_file.write(f"Vacation template: {vacation_template_name}\n")
        log_file.write(f"Minimums template: {minimuns_template_name}\n")
        log_file.write(f"Year: {year}\n")
        log_file.write(f"Shifts: {shifts}\n")
        log_file.write(f"MaxTime: {maxTime}\n")
        log_file.write("-" * 80 + "\n")
        log_file.flush()

    def _write_task_log_footer(self, log_file):
        log_file.write("-" * 80 + "\n")
        log_file.write(f"Timestamp: {datetime.now().isoformat()}\n")
        log_file.write("TASK LOG END\n")
        log_file.flush()


if __name__ == "__main__":
    client = RabbitMQClient()
    client.consume_messages()
