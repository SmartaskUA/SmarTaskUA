package smartask.api.services;

import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.stereotype.Service;
import smartask.api.models.Employee;
import smartask.api.models.Team;
import smartask.api.repositories.TeamRepository;

import java.util.ArrayList;
import java.util.List;
import java.util.Optional;

@Service
public class TeamService {
    @Autowired
    private TeamRepository teamRepository;

    public TeamService(TeamRepository teamRepository) {
        this.teamRepository = teamRepository;
    }

    public List<Team> getTeams() {
        return teamRepository.findAll();
    }

    public void addTeam(Team team) {
        saveTeam(team);
    }

    public Team getTeamById(String id) {
        return teamRepository.findById(id).orElseThrow(() -> new IllegalArgumentException("Team not found"));
    }

    public void updateTeam(String id, Team team) {
        Team teamToUpdate = getTeamById(id);
        teamToUpdate.setName(team.getName());
        teamToUpdate.setEmployeeIds(team.getEmployeeIds());
        saveTeam(teamToUpdate);
    }

    public void addEmployeesToTeam(String teamId, List<String> employeeIds, EmployeeService employeeService) {
        Team team = getTeamById(teamId);
        List<String> currentEmployeeIds = team.getEmployeeIds() != null ? team.getEmployeeIds() : new ArrayList<>();

        for (String empId : employeeIds) {
            Employee employee = employeeService.getEmployeeById(empId);

            // Adiciona o ID do time ao funcionário (evitando duplicados)
            employee.getTeamIds().add(teamId);
            employeeService.saveEmployee(employee);

            // Adiciona o ID do funcionário ao time (evitando duplicados)
            if (!currentEmployeeIds.contains(empId)) {
                currentEmployeeIds.add(empId);
            }
        }

        team.setEmployeeIds(currentEmployeeIds);
        saveTeam(team);
    }

    public void saveTeam(Team team) {
        teamRepository.save(team);
    }
}
