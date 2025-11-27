package smartask.api.controllers;

import io.swagger.v3.oas.annotations.Operation;
import io.swagger.v3.oas.annotations.tags.Tag;
import lombok.RequiredArgsConstructor;

import org.slf4j.LoggerFactory;
import org.springframework.amqp.rabbit.core.RabbitTemplate;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.http.ResponseEntity;
import org.springframework.web.bind.annotation.*;
import org.springframework.web.multipart.MultipartFile;

import org.slf4j.Logger;
import smartask.api.models.Schedule;
import smartask.api.models.requests.ScheduleRequest;
import smartask.api.services.SchedulesService;
import java.nio.file.Files;
import java.util.ArrayList;
import java.util.HashMap;
import java.util.List;
import java.util.Map;
import java.util.Optional;
import java.util.UUID;
import java.nio.file.Path;
import java.nio.file.Paths;


@RestController
@CrossOrigin(origins = "http://localhost:5173")
@RequestMapping("/schedules")
@RequiredArgsConstructor
@Tag(name = "Schedule Management", description = "Endpoints for managing work schedules")
public class SchedulesController {
    private static final Logger log = LoggerFactory.getLogger(SchedulesController.class);

    @Autowired
    private SchedulesService service;

    @Autowired
    private RabbitTemplate rabbitTemplate;

    /**
     * Initiates the generation of a new schedule based on the given title.
     *
     * @param scheduleRequest the minimal info for generating the new schedule.
     * @return A response indicating whether the schedule generation was started successfully.
     */
    @Operation(
            summary = "Generate a new schedule",
            description = "Starts a new schedule generation process based on the given title. If a schedule with the same title already exists, returns a bad request response."
    )
    @PostMapping("/generate")
    public ResponseEntity<String> generateNewSchedule(@RequestBody ScheduleRequest scheduleRequest) {
        final String res= service.requestScheduleGeneration(scheduleRequest) ;
        if (res.equals("Sent task request")) {
            return ResponseEntity.ok("Schedule generation started for: " + scheduleRequest);
        } else {
            return ResponseEntity.badRequest().body("Failed to start schedule generation for: " + scheduleRequest + ". Caused by: "+res);
        }
    }

    /**
     * Retrieves a schedule by its title.
     *
     * @param title The title of the schedule.
     * @return The schedule details if found, otherwise a 404 Not Found response.
     */
    @Operation(
            summary = "Get a schedule by title",
            description = "Fetches details of a schedule using its title. If the schedule is not found, returns a 404 response."
    )
    @GetMapping("/{title}")
    public ResponseEntity<Optional<Schedule>> fetchByTitle(@PathVariable String title) {
        if (service.getByTitle(title).isPresent()) {
            return ResponseEntity.ok(service.getByTitle(title));
        }
        return ResponseEntity.notFound().build();
    }

    /**
     * Retrieves all available schedules.
     *
     * @return A list of all schedules.
     */
    @Operation(
            summary = "Get all schedules",
            description = "Returns a list of all generated schedules."
    )
    @GetMapping("/fetch")
    public ResponseEntity<List<Schedule>> fetchAll() {
        return ResponseEntity.ok(service.getAllSchedules());
    }

    /**
     * Retrieves a schedule by its id.
     *
     * @param id the id of the schedule.
     * @return The schedule if found, otherwise 404.
     */
    @GetMapping("/fetch/{id}")
    public ResponseEntity<Schedule> fetchScheduleById(@PathVariable String id) {
        Optional<Schedule> optionalSchedule = service.getScheduleById(id);
        if (optionalSchedule.isPresent()) {
            return ResponseEntity.ok(optionalSchedule.get());
        } else {
            return ResponseEntity.notFound().build();
        }
    }


    @PostMapping("/analyze")
    public ResponseEntity<?> analyzeSchedules(@RequestParam("files") List<MultipartFile> files,
                                              @RequestParam("vacationTemplate") String vacationTemplate,
                                              @RequestParam("minimunsTemplate") String minimunsTemplate,
                                              @RequestParam("employees") String employees,
                                              @RequestParam("year") String year) {
        try {
            log.info("Received request to analyze {} files", files.size());
            String requestId = UUID.randomUUID().toString();
            List<String> filePaths = new ArrayList<>();

            for (MultipartFile file : files) {
                if (file.isEmpty()) {
                    log.error("Received empty file: {}", file.getOriginalFilename());
                    return ResponseEntity.badRequest().body(Map.of("error", "Empty file uploaded"));
                }
                String fileName = file.getOriginalFilename();
                Path filePath = Paths.get("/shared_tmp", fileName);
                log.info("Saving file to: {}", filePath);
                if (file.getBytes() == null) {
                    log.error("File is empty: {}", fileName);
                    return ResponseEntity.badRequest().body(Map.of("error", "File is empty"));
                }
                log.info("Uploaded file {} size(before)={} bytes", fileName, file.getSize());
                Files.write(filePath, file.getBytes());
                log.info("Saved file {} size(after)={} bytes", fileName, Files.size(filePath));
                filePaths.add(filePath.toString());
            }

            Map<String, Object> message = new HashMap<>();
            message.put("requestId", requestId);
            message.put("files", filePaths);
            message.put("vacationTemplate", vacationTemplate);
            message.put("minimunsTemplate", minimunsTemplate);
            message.put("employees", employees);
            message.put("year", year);
            log.info("Publishing message to comparison-exchange: {}", message);
            log.info("Year: {}", year);
            log.info("Vacation Template: {}", vacationTemplate);
            log.info("Minimuns Template: {}", minimunsTemplate);
            log.info("Employees: {}", employees);
            rabbitTemplate.convertAndSend("comparison-exchange", "comparison-queue", message);

            return ResponseEntity.accepted().body(Map.of("requestId", requestId, "status", "Processing"));
        } catch (Exception e) {
            log.error("Error processing /schedules/analyze request", e);
            return ResponseEntity.status(500).body(Map.of("error", e.getMessage()));
        }
    }

    @Operation(
            summary = "Delete schedule by ID",
            description = "Deletes the schedule with the specified ID if it exists."
    )
    @DeleteMapping("/delete/id/{id}")
    public ResponseEntity<String> deleteById(@PathVariable String id) {
        boolean deleted = service.deleteScheduleById(id);
        if (deleted) {
            return ResponseEntity.ok("Schedule with ID " + id + " deleted.");
        }
        return ResponseEntity.notFound().build();
    }

    @Operation(
            summary = "Delete schedule by title",
            description = "Deletes the schedule with the specified title if it exists."
    )
    @DeleteMapping("/delete/title/{title}")
    public ResponseEntity<String> deleteByTitle(@PathVariable String title) {
        boolean deleted = service.deleteScheduleByTitle(title);
        if (deleted) {
            return ResponseEntity.ok("Schedule with title '" + title + "' deleted.");
        }
        return ResponseEntity.notFound().build();
    }


}
