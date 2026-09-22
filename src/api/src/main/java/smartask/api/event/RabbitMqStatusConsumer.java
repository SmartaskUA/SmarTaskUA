package smartask.api.event;

import org.springframework.amqp.rabbit.annotation.RabbitListener;
import org.springframework.stereotype.Component;
import org.springframework.beans.factory.annotation.Autowired;
import smartask.api.models.TaskStatus;
import smartask.api.repositories.TaskStatusRepository;
import java.util.Optional;

@Component
public class RabbitMqStatusConsumer {

    @Autowired
    private TaskStatusRepository taskStatusRepository;

    @RabbitListener(queues = "status-queue")
    public void receiveStatusUpdate(TaskStatus receivedStatus) {
        System.out.println("Mensagem recebida: " + receivedStatus);

        try {
            if (receivedStatus == null) {
                System.err.println("Ignoring null status message.");
                return;
            }

            String taskId = receivedStatus.getTaskId();
            String newStatus = receivedStatus.getStatus();

            if (taskId == null || taskId.isBlank()) {
                System.err.println("Ignoring status message with missing taskId.");
                return;
            }

            if (newStatus == null || newStatus.isBlank()) {
                System.err.println("Ignoring status message with missing status for taskId: " + taskId);
                return;
            }

            System.out.println("Received status update: " + taskId + " -> " + newStatus);

            updateTaskStatus(taskId, receivedStatus);
        } catch (Exception e) {
            System.err.println("Error processing status message: " + e.getMessage());
            e.printStackTrace();
        }
    }



    private void updateTaskStatus(String taskId, TaskStatus receivedStatus) {
        Optional<TaskStatus> taskOpt = taskStatusRepository.findById(taskId);
        if (taskOpt.isPresent()) {
            TaskStatus task = taskOpt.get();
            task.setStatus(receivedStatus.getStatus());
            task.setFailureType(receivedStatus.getFailureType());
            task.setFailureSummary(receivedStatus.getFailureSummary());
            task.setReportArtifacts(receivedStatus.getReportArtifacts());
            task.setUpdatedAt(java.time.LocalDateTime.now());
            taskStatusRepository.save(task);
        } else {
            System.err.println("Task not found in database: " + taskId);
        }
    }
}
