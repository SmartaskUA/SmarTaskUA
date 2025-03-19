package smartask.api.event;

import org.springframework.amqp.rabbit.annotation.RabbitListener;
import org.springframework.stereotype.Component;

@Component
public class RabbitMqConsumer {

    @RabbitListener(queues = "task-queue")
    public void receiveMessage(String message) {
        System.out.println("Received message: " + message);
    }
}
