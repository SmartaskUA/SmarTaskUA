package smartask.api.controllers;

import org.springframework.http.HttpStatus;
import org.springframework.http.HttpHeaders;
import org.springframework.http.MediaType;
import org.springframework.http.ResponseEntity;
import org.springframework.core.io.FileSystemResource;
import org.springframework.core.io.Resource;
import org.springframework.web.bind.annotation.*;
import org.springframework.beans.factory.annotation.Autowired;
import smartask.api.models.TaskStatus;
import smartask.api.repositories.TaskStatusRepository;

import java.nio.file.Files;
import java.nio.file.Path;
import java.util.List;
import java.util.Map;
import java.util.Optional;

@RestController
@RequestMapping("/tasks")
public class TaskStatusController {

    @Autowired
    private TaskStatusRepository taskStatusRepository;

    @GetMapping("/{taskId}")
    public ResponseEntity<?> getTaskStatus(@PathVariable String taskId) {
        Optional<TaskStatus> taskOpt = taskStatusRepository.findById(taskId);

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

    @GetMapping("/{taskId}/report/json")
    public ResponseEntity<?> downloadJsonReport(@PathVariable String taskId) {
        return downloadReport(taskId, "json", MediaType.APPLICATION_JSON, taskId + "-validation-report.json");
    }

    @GetMapping("/{taskId}/report/md")
    public ResponseEntity<?> downloadMarkdownReport(@PathVariable String taskId) {
        return downloadReport(taskId, "markdown", MediaType.parseMediaType("text/markdown"), taskId + "-validation-report.md");
    }

    @GetMapping("/{taskId}/report/pdf")
    public ResponseEntity<?> downloadPdfReport(@PathVariable String taskId) {
        return downloadReport(taskId, "pdf", MediaType.APPLICATION_PDF, taskId + "-validation-report.pdf");
    }

    private ResponseEntity<?> downloadReport(String taskId, String artifactKey, MediaType contentType, String filename) {
        Optional<TaskStatus> taskOpt = taskStatusRepository.findById(taskId);

        if (taskOpt.isEmpty()) {
            System.err.println("Task not found in DB: " + taskId);
            return ResponseEntity.status(HttpStatus.NOT_FOUND).body("Task not found");
        }

        Map<String, String> artifacts = taskOpt.get().getReportArtifacts();
        if (artifacts == null || !artifacts.containsKey(artifactKey) || artifacts.get(artifactKey) == null) {
            return ResponseEntity.status(HttpStatus.NOT_FOUND).body("Report not found");
        }

        Path reportPath = Path.of(artifacts.get(artifactKey)).normalize().toAbsolutePath();
        if (!Files.exists(reportPath) || !Files.isRegularFile(reportPath)) {
            return ResponseEntity.status(HttpStatus.NOT_FOUND).body("Report file not found");
        }

        Resource resource = new FileSystemResource(reportPath);
        return ResponseEntity.ok()
                .contentType(contentType)
                .header(HttpHeaders.CONTENT_DISPOSITION, "attachment; filename=\"" + filename + "\"")
                .body(resource);
    }
}
