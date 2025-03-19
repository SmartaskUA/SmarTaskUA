package smartask.api.event;

import org.springframework.amqp.rabbit.annotation.RabbitListener;
import org.springframework.stereotype.Component;
import org.springframework.beans.factory.annotation.Autowired;
import com.fasterxml.jackson.databind.ObjectMapper;
import smartask.api.models.TaskStatus;
import smartask.api.repositories.TaskStatusRepository;
import java.util.Optional;

@Component
public class RabbitMqConsumer {

    @Autowired
    private TaskStatusRepository taskStatusRepository;

    @Autowired
    private ObjectMapper objectMapper;

    @RabbitListener(queues = "task-queue")
    public void receiveMessage(String message) {
        try {
            // Parse JSON message to retrieve taskId and status update
            TaskStatus receivedStatus = objectMapper.readValue(message, TaskStatus.class);
            String taskId = receivedStatus.getTaskId();
            String newStatus = receivedStatus.getStatus();

            System.out.println("Received update for task: " + taskId + " with status: " + newStatus);

            // Update task status in the database
            updateTaskStatus(taskId, newStatus);

        } catch (Exception e) {
            System.err.println("Error processing message: " + e.getMessage());
        }
    }

    private void updateTaskStatus(String taskId, String status) {
        Optional<TaskStatus> taskOpt = taskStatusRepository.findByTaskId(taskId);
        if (taskOpt.isPresent()) {
            TaskStatus task = taskOpt.get();
            task.setStatus(status);
            task.setUpdatedAt(java.time.LocalDateTime.now());
            taskStatusRepository.save(task);
        } else {
            System.err.println("Task not found in database: " + taskId);
        }
    }
}
