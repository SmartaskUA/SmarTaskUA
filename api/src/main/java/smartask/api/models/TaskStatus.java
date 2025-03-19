package smartask.api.models;

import org.springframework.data.annotation.Id;
import org.springframework.data.mongodb.core.mapping.Document;
import smartask.api.models.requests.ScheduleRequest;
import java.time.LocalDateTime;

@Document(collection = "task_status")
public class TaskStatus {

    @Id
    private String id; // MongoDB generates this automatically

    private String taskId; // Unique ID for the task
    private String status = "PENDING"; // PENDING, IN_PROGRESS, COMPLETED, FAILED
    private LocalDateTime createdAt;
    private LocalDateTime updatedAt;

    private ScheduleRequest scheduleRequest; // Store the original request

    // Default constructor
    public TaskStatus() {}

    // Constructor including the request
    public TaskStatus(String taskId, String status, LocalDateTime createdAt, LocalDateTime updatedAt, ScheduleRequest scheduleRequest) {
        this.id = taskId; // Use taskId as MongoDB's _id
        this.taskId = taskId;
        this.status = status;
        this.createdAt = createdAt;
        this.updatedAt = updatedAt;
        this.scheduleRequest = scheduleRequest;
    }

    // Getters & Setters
    public String getId() { return id; }
    public void setId(String id) { this.id = id; }

    public String getTaskId() { return taskId; }
    public void setTaskId(String taskId) { this.taskId = taskId; }

    public String getStatus() { return status; }
    public void setStatus(String status) { this.status = status; }

    public LocalDateTime getCreatedAt() { return createdAt; }
    public void setCreatedAt(LocalDateTime createdAt) { this.createdAt = createdAt; }

    public LocalDateTime getUpdatedAt() { return updatedAt; }
    public void setUpdatedAt(LocalDateTime updatedAt) { this.updatedAt = updatedAt; }

    public ScheduleRequest getScheduleRequest() { return scheduleRequest; }
    public void setScheduleRequest(ScheduleRequest scheduleRequest) { this.scheduleRequest = scheduleRequest; }
}
