import pika
import json
import random

connection = pika.BlockingConnection(pika.ConnectionParameters(host='localhost'))
channel = connection.channel()

task_message = {
    "taskId": random.randint(1, 1000),
}

channel.basic_publish(
    exchange='task-exchange',
    routing_key='task-routing-key',
    body=json.dumps(task_message),
    properties=pika.BasicProperties(content_type='application/json', delivery_mode=2)
)

print("Task sent to RabbitMQ:", task_message)

connection.close()
