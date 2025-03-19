package smartask.api.controllers;

import org.springframework.http.ResponseEntity;
import org.springframework.scheduling.config.Task;
import org.springframework.web.bind.annotation.*;
import org.springframework.beans.factory.annotation.Autowired;
import smartask.api.models.TaskStatus;
import smartask.api.repositories.TaskStatusRepository;

import java.util.Optional;

@RestController
@RequestMapping("/tasks")
public class TaskStatusController {

    @Autowired
    private TaskStatusRepository taskStatusRepository;

    @GetMapping("/{taskId}")
    public ResponseEntity<TaskStatus> getTaskStatus(@PathVariable String taskId) {
        Optional<TaskStatus> task = taskStatusRepository.findByTaskId(taskId);

        if (task.isPresent()) {
            return ResponseEntity.ok(task.get());
        } else {
            System.err.println("Task not found in DB: " + taskId);
            return ResponseEntity.notFound().build();
        }
    }
}
