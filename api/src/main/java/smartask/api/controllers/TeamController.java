package smartask.api.controllers;

import io.swagger.v3.oas.annotations.Operation;
import io.swagger.v3.oas.annotations.tags.Tag;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.http.HttpStatus;
import org.springframework.http.ResponseEntity;
import org.springframework.web.bind.annotation.*;
import smartask.api.models.Team;
import smartask.api.models.requests.AddEmployeesToTeamRequest;
import smartask.api.services.EmployeeService;
import smartask.api.services.TeamService;
import java.util.List;

@Tag(name = "Team", description = "Teams Management")
@RestController
@RequestMapping("/api/v1/teams")
public class TeamController {
    @Autowired
    private TeamService teamService;

    @Autowired
    EmployeeService employeeService;


    public TeamController(TeamService teamService) {
        this.teamService = teamService;
    }

    @Operation(summary = "Get all teams")
    @GetMapping("/")
    public ResponseEntity<List<Team>> getTeams() {
        List<Team> teams = teamService.getTeams();
        return new ResponseEntity<>(teams, HttpStatus.OK);
    }

    @Operation(summary = "Get a team by ID")
    @GetMapping("/{id}")
    public ResponseEntity<Team> getTeamById(@PathVariable String id) {
        Team team = teamService.getTeamById(id);
        return new ResponseEntity<>(team, HttpStatus.OK);
    }

    @Operation(summary = "Get a team by name")
    @GetMapping("/name/{name}")
    public ResponseEntity<Team> getTeamByName(@PathVariable String name) {
        Team team = teamService.getTeamByName(name);
        return new ResponseEntity<>(team, HttpStatus.OK);
    }


    @Operation(summary = "Add a new team")
    @PostMapping("/{teamName}")
    public ResponseEntity<String> addTeam(@PathVariable String teamName) {
        teamService.addTeam(teamName);
        return ResponseEntity.ok("Team created successfully");
    }


    @Operation(summary = "Update a team")
    @PutMapping("/{id}")
    public ResponseEntity<String> updateTeam(@RequestBody Team team, @PathVariable String id) {
        teamService.updateTeam(id, team);
        return ResponseEntity.ok("Team updated successfully");
    }

    @Operation(summary = "Add employees to a team")
    @PostMapping("/{teamName}/add-employees")
    public ResponseEntity<String> addEmployeesToTeam(
            @PathVariable String teamName,
            @RequestBody AddEmployeesToTeamRequest request
    ) {
        teamService.addEmployeesToTeam(teamName, request.getEmployeeIds());
        return ResponseEntity.ok("Employees added to team successfully");
    }

    @Operation(summary = "Set first preference team for an employee")
    @PutMapping("/{employeeId}/set-first-preference/{teamName}")
    public ResponseEntity<String> setEmployeeFirstPreference(
            @PathVariable String employeeId,
            @PathVariable String teamName
    ) {
        teamService.setEmployeeFirstPreference(employeeId, teamName);
        return ResponseEntity.ok("First preference set successfully");
    }

    @Operation(summary = "Set team at specific position for an employee")
    @PutMapping("/{employeeId}/set-team-preference-index/{teamName}/{position}")
    public ResponseEntity<String> setEmployeeTeamAtPosition(
            @PathVariable String employeeId,
            @PathVariable String teamName,
            @PathVariable int position
    ) {
        teamService.setEmployeeTeamAtPosition(employeeId, teamName, position);
        return ResponseEntity.ok("Team position set successfully");
    }

    @Operation(summary = "Remove an employee from a team by name")
    @DeleteMapping("/{teamName}/remove-employee/{employeeId}")
    public ResponseEntity<String> removeEmployeeFromTeam(
            @PathVariable String teamName,
            @PathVariable String employeeId) {
        teamService.removeEmployeeFromTeam(employeeId, teamName);
        return ResponseEntity.ok("Employee removed from team successfully");
    }

    @Operation(summary = "Delete a team by Name and remove it from all employees")
    @DeleteMapping("/{teamName}")
    public ResponseEntity<String> deleteTeam(@PathVariable String teamName) {
        teamService.deleteTeam(teamName);
        return ResponseEntity.ok("Team deleted successfully");
    }

    @Operation(summary = "Get all unique group names from teams")
    @GetMapping("/groups")
    public ResponseEntity<List<String>> getAllGroupNames() {
        List<Team> teams = teamService.getTeams();

        List<String> uniqueGroups = teams.stream()
                .map(Team::getGroupName)
                .filter(g -> g != null && !g.isBlank())
                .distinct()
                .sorted()
                .toList();

        return new ResponseEntity<>(uniqueGroups, HttpStatus.OK);
    }



}
