package smartask.api.controllers;

import org.springframework.http.HttpStatus;
import org.springframework.http.ResponseEntity;
import org.springframework.scheduling.config.Task;
import org.springframework.web.bind.annotation.*;
import org.springframework.beans.factory.annotation.Autowired;
import smartask.api.models.TaskStatus;
import smartask.api.repositories.TaskStatusRepository;

import java.util.List;
import java.util.Optional;

@RestController
@RequestMapping("/tasks")
public class TaskStatusController {

    @Autowired
    private TaskStatusRepository taskStatusRepository;

    @GetMapping("/{taskId}")
    public ResponseEntity<?> getTaskStatus(@PathVariable String taskId) {
        Optional<TaskStatus> taskOpt = taskStatusRepository.findByTaskId(taskId);

        if (taskOpt.isPresent()) {
            return ResponseEntity.ok(taskOpt.get());
        } else {
            System.err.println("Task not found in DB: " + taskId);
            return ResponseEntity.status(HttpStatus.NOT_FOUND).body("Task not found");
        }
    }

    @GetMapping
    public ResponseEntity<List<TaskStatus>> getAllTasks() {
        List<TaskStatus> tasks = taskStatusRepository.findAll();
        return ResponseEntity.ok(tasks);
    }
}

