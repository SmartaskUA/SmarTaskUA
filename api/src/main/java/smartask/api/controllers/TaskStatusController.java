package smartask.api.controllers;

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
    public String getTaskStatus(@PathVariable String taskId) {
        Optional<TaskStatus> task = taskStatusRepository.findByTaskId(taskId);
        return task.map(TaskStatus::getStatus).orElse("Task not found");
    }
}
