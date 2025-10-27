import pika
import json
import time
from datetime import datetime
from concurrent.futures import ThreadPoolExecutor
from modules.MongoDBClient import MongoDBClient
from modules.TaskManager import TaskManager


class RabbitMQClient:
    def __init__(self, host='rabbitmq', task_exchange='task-exchange', status_exchange='status-exchange',
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

        self.send_task_status(task_id, "IN_PROGRESS")
        try:
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


if __name__ == "__main__":
    client = RabbitMQClient()
    client.consume_messages()
