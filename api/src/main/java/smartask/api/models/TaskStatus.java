package smartask.api.models;

import org.springframework.data.annotation.Id;
import org.springframework.data.mongodb.core.mapping.Document;
import java.time.LocalDateTime;

@Document(collection = "task_status") // Change to MongoDB document
public class TaskStatus {

    @Id
    private String id; // MongoDB generates this automatically

    private String taskId; // Unique ID for the task
    private String status; // PENDING, IN_PROGRESS, COMPLETED, FAILED
    private LocalDateTime createdAt;
    private LocalDateTime updatedAt;

    // Default constructor
    public TaskStatus() {}

    // Constructor including ID (MongoDB will generate if null)
    public TaskStatus(String taskId, String status, LocalDateTime createdAt, LocalDateTime updatedAt) {
        this.id = taskId; // Use taskId as MongoDB's _id
        this.taskId = taskId;
        this.status = status;
        this.createdAt = createdAt;
        this.updatedAt = updatedAt;
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
}
