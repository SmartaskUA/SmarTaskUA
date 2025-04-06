package smartask.api.controllers;

import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.http.ResponseEntity;
import org.springframework.web.bind.annotation.*;
import smartask.api.models.VacationTemplate;
import smartask.api.models.requests.VacationTemplateRequest;
import smartask.api.services.VacationService;

import java.util.List;

@RestController
@RequestMapping("/vacation")
public class VacationController {

    @Autowired
    private VacationService service;

    @PostMapping("/")
    public ResponseEntity<String> newTemplate(@RequestBody VacationTemplateRequest req){
        this.service.newTemplate(req.getName(), req.getVacations());
        return ResponseEntity.ok("Template with data "+ req+ " created");
    }

    @GetMapping("/")
    public ResponseEntity<List<VacationTemplate>> newTemplate(){
        return ResponseEntity.ok(
                this.service.getAll()
        );
    }
}
