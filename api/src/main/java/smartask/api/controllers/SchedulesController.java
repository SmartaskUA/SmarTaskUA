package smartask.api.controllers;


import lombok.AllArgsConstructor;
import lombok.NoArgsConstructor;
import lombok.RequiredArgsConstructor;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.http.ResponseEntity;
import org.springframework.web.bind.annotation.*;

import smartask.api.models.Schedule;
import smartask.api.services.SchedulesService;

import java.util.List;
import java.util.Optional;

@RestController
@RequestMapping("/schedules")
@RequiredArgsConstructor
public class SchedulesController {

    @Autowired
    private  SchedulesService service;

    @GetMapping("/generate/{title}")
    public ResponseEntity<String> generateNewSchedule(@PathVariable String title) {
        //ToDo : Should also verify if the request with the same configuratio  was already generated
        if (service.requestScheduleGeneration(title)) {
            return ResponseEntity.ok("Schedule generation started for: " + title);
        } else {
            return ResponseEntity.badRequest().body("Failed to start schedule generation for: " + title+" Schedule with the title already exists");
        }
    }

    @GetMapping("/{title}")
    public ResponseEntity<Optional<Schedule>> fetchByTitle(@PathVariable String title){
        if (service.getByTitle(title).isPresent()){
            return ResponseEntity.ok(service.getByTitle(title));
        }
        return ResponseEntity.notFound().build();

    }

    @GetMapping("/fetch")
    public ResponseEntity<List<Schedule>> fetchall(){
        return   ResponseEntity.ok(service.getAllSchedules());
    }
}
