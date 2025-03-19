package smartask.api.event;
import com.fasterxml.jackson.core.JsonProcessingException;
import org.springframework.amqp.rabbit.core.RabbitTemplate;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.stereotype.Service;
import smartask.api.models.TaskStatus;
import smartask.api.models.requests.ScheduleRequest;
import com.fasterxml.jackson.databind.ObjectMapper;
import smartask.api.repositories.TaskStatusRepository;

import java.time.LocalDateTime;
import java.util.UUID;

@Service
public class RabbitMqProducer {

    private static final String EXCHANGE_NAME = "task-exchange";
    private static final String ROUTING_KEY = "task-routing-key";

    @Autowired
    private RabbitTemplate rabbitTemplate;

    @Autowired
    private ObjectMapper objectMapper;

    @Autowired
    private TaskStatusRepository taskStatusRepository;

    public void requestScheduleMessage(ScheduleRequest schedule) {
        try {
            // Generate a unique task ID
            String taskId = UUID.randomUUID().toString();
            schedule.setTaskId(taskId); // Store Task ID in the request

            // Convert request to JSON
            String jsonMessage = objectMapper.writeValueAsString(schedule);

            // Save task status as PENDING
            TaskStatus taskStatus = new TaskStatus( taskId, "PENDING", LocalDateTime.now(), LocalDateTime.now());
            taskStatusRepository.save(taskStatus);

            // Send message to RabbitMQ
            rabbitTemplate.convertAndSend(EXCHANGE_NAME, ROUTING_KEY, jsonMessage);
            System.out.println("Sent task request: " + jsonMessage);

        } catch (JsonProcessingException e) {
            System.err.println("Error converting ScheduleRequest to JSON: " + e.getMessage());
        }
    }

    public void sendMessage(String message) {
        rabbitTemplate.convertAndSend(EXCHANGE_NAME, ROUTING_KEY, message);
        System.out.println("Sent message: " + message);
    }
}
