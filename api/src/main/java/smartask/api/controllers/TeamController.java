package smartask.api.controllers;

import io.swagger.v3.oas.annotations.Operation;
import io.swagger.v3.oas.annotations.tags.Tag;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.http.HttpStatus;
import org.springframework.http.ResponseEntity;
import org.springframework.web.bind.annotation.*;
import smartask.api.models.Employee;
import smartask.api.models.requests.RestrictionRequest;
import smartask.api.services.EmployeeService;
import smartask.api.services.TeamService;

import java.util.List;
import java.util.Map;

@Tag(name = "Team", description = "Teams Management")
@RestController
@RequestMapping("/api/v1/teams")
public class TeamController {
    @Autowired
    private TeamService teamService;

    public TeamController(TeamService teamService) {
        this.teamService = teamService;
    }

    
}
