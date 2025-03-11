package smartask.api.controller;


import lombok.AllArgsConstructor;
import lombok.NoArgsConstructor;
import lombok.RequiredArgsConstructor;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.http.ResponseEntity;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.ResponseBody;
import org.springframework.web.bind.annotation.RestController;
import smartask.api.entity.Schedule;
import smartask.api.service.SchedulesService;

import java.util.List;

@RestController
@RequestMapping("/schedules")
@RequiredArgsConstructor
public class SchedulesController {

    @Autowired
    private  SchedulesService service;

    @GetMapping("/generate")
    public ResponseEntity<String> generateNewSchedule(){
        String response = "SEVEN NATION ARMY GOES BRRRRRRRR";
        return   ResponseEntity.ok(response);
    }


    @GetMapping("/read")
    public ResponseEntity<List<String[]>> readex1(){
        return   ResponseEntity.ok(service.readex1());
    }


    @GetMapping("/fetch")
    public ResponseEntity<List<Schedule>> fetchall(){
        return   ResponseEntity.ok(service.getAllSchedules());
    }
}
