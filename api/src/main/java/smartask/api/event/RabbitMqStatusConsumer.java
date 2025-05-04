package smartask.api.event;

import org.springframework.amqp.rabbit.annotation.RabbitListener;
import org.springframework.stereotype.Component;
import org.springframework.beans.factory.annotation.Autowired;
import com.fasterxml.jackson.databind.ObjectMapper;
import smartask.api.models.TaskStatus;
import smartask.api.repositories.TaskStatusRepository;
import java.util.Optional;

@Component
public class RabbitMqStatusConsumer {

    @Autowired
    private TaskStatusRepository taskStatusRepository;

    @Autowired
    private ObjectMapper objectMapper;

    @RabbitListener(queues = "status-queue")
    public void receiveStatusUpdate(TaskStatus receivedStatus) {
        System.out.println("Mensagem recebida: " + receivedStatus);

        try {
            String taskId = receivedStatus.getTaskId();
            String newStatus = receivedStatus.getStatus();

            System.out.println("Received status update: " + taskId + " -> " + newStatus);

            updateTaskStatus(taskId, newStatus);
        } catch (Exception e) {
            System.err.println("Error processing status message: " + e.getMessage());
            e.printStackTrace();
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
