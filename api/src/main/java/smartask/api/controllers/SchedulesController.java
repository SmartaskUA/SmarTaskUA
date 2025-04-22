package smartask.api.controllers;

import io.swagger.v3.oas.annotations.Operation;
import io.swagger.v3.oas.annotations.tags.Tag;
import lombok.RequiredArgsConstructor;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.http.ResponseEntity;
import org.springframework.web.bind.annotation.*;
import org.springframework.web.multipart.MultipartFile;
import smartask.api.models.Schedule;
import smartask.api.models.requests.ScheduleRequest;
import smartask.api.services.SchedulesService;
import java.io.IOException;
import java.util.List;
import java.util.Optional;
import java.io.File;

@RestController
@CrossOrigin(origins = "http://localhost:5173")
@RequestMapping("/schedules")
@RequiredArgsConstructor
@Tag(name = "Schedule Management", description = "Endpoints for managing work schedules")
public class SchedulesController {

    @Autowired
    private SchedulesService service;

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
        // ToDo : Should also verify if the request with the same configuration was already generated
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
    public ResponseEntity<String> analyzeSchedules(@RequestParam("file1") MultipartFile file1,
                                 @RequestParam("file2") MultipartFile file2) throws IOException {

    File temp1 = File.createTempFile("file1-", ".csv");
    File temp2 = File.createTempFile("file2-", ".csv");
    file1.transferTo(temp1);
    file2.transferTo(temp2);

    String jsonOutput = service.analyzeSchedules(temp1, temp2);

    return ResponseEntity.ok(jsonOutput);
}

}
