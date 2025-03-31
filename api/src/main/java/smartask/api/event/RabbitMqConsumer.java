package smartask.api.event;

import org.springframework.amqp.rabbit.annotation.RabbitListener;
import org.springframework.stereotype.Component;
import org.springframework.beans.factory.annotation.Autowired;
import com.fasterxml.jackson.databind.ObjectMapper;
import smartask.api.models.TaskStatus;
import smartask.api.models.requests.ScheduleRequest;
import smartask.api.repositories.TaskStatusRepository;
import java.time.LocalDateTime;
import java.util.Optional;

@Component
public class RabbitMqConsumer {

    @Autowired
    private TaskStatusRepository taskStatusRepository;

    @Autowired
    private ObjectMapper objectMapper;

    @RabbitListener(queues = "task-queue")
    public void receiveTaskMessage(String message) {
        try {
            // Parse JSON para extrair taskId e ScheduleRequest
            ScheduleRequest scheduleRequest = objectMapper.readValue(message, ScheduleRequest.class);
            String taskId = scheduleRequest.getTaskId();

            System.out.println("Received new task: " + taskId);

            // Verifica se a tarefa já existe no banco
            Optional<TaskStatus> existingTask = taskStatusRepository.findByTaskId(taskId);
            if (existingTask.isPresent()) {
                TaskStatus task = existingTask.get();
                task.setStatus("RECEIVED");
                task.setUpdatedAt(LocalDateTime.now());
                taskStatusRepository.save(task);
            } else {
                // Criar um novo registro para a tarefa
                TaskStatus newTaskStatus = new TaskStatus(
                        taskId,
                        "RECEIVED",
                        LocalDateTime.now(),
                        LocalDateTime.now(),
                        scheduleRequest
                );
                taskStatusRepository.save(newTaskStatus);
            }

        } catch (Exception e) {
            System.err.println("Error processing task message: " + e.getMessage());
        }
    }
}
