package smartask.api.models;

import jakarta.persistence.*;
import java.time.LocalDateTime;

@Entity
@Table(name = "task_status")
public class TaskStatus {

    @Id
    private String id;

    private String taskId; // Unique ID for the task
    private String status; // PENDING, IN_PROGRESS, COMPLETED, FAILED
    private LocalDateTime createdAt;
    private LocalDateTime updatedAt;

    // Default constructor (no-args)
    public TaskStatus() {
    }

    // Constructor with all fields
    public TaskStatus( String taskId, String status, LocalDateTime createdAt, LocalDateTime updatedAt) {
        this.taskId = taskId;
        this.status = status;
        this.createdAt = createdAt;
        this.updatedAt = updatedAt;
    }

    // Getters
    public String getId() {
        return id;
    }

    public String getTaskId() {
        return taskId;
    }

    public String getStatus() {
        return status;
    }

    public LocalDateTime getCreatedAt() {
        return createdAt;
    }

    public LocalDateTime getUpdatedAt() {
        return updatedAt;
    }

    // Setters
    public void setId(String id) {
        this.id = id;
    }

    public void setTaskId(String taskId) {
        this.taskId = taskId;
    }

    public void setStatus(String status) {
        this.status = status;
    }

    public void setCreatedAt(LocalDateTime createdAt) {
        this.createdAt = createdAt;
    }

    public void setUpdatedAt(LocalDateTime updatedAt) {
        this.updatedAt = updatedAt;
    }
}
