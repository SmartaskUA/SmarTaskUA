package smartask.api.services;

import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.stereotype.Service;
import smartask.api.models.Employee;
import smartask.api.models.Team;
import smartask.api.repositories.TeamRepository;

import java.util.*;

@Service
public class TeamService {
    @Autowired
    private TeamRepository teamRepository;

    @Autowired
    private EmployeeService employeeService;

    public TeamService(TeamRepository teamRepository) {
        this.teamRepository = teamRepository;
    }

    public List<Team> getTeams() {
        return teamRepository.findAll();
    }

    public void addTeam(String teamName) {
        Team team = new Team(teamName);
        team.setEmployeeIds(new ArrayList<>());  
        saveTeam(team);
    }

    public void addTeam(Team team) {
        if (team.getEmployeeIds() == null) {
            team.setEmployeeIds(new ArrayList<>());
        }
        saveTeam(team);
    }

    public Team getTeamById(String id) {
        return teamRepository.findById(id).orElseThrow(() -> new IllegalArgumentException("Team not found"));
    }

    public Team getTeamByName(String name) {
    return teamRepository.findByName(name)
            .orElseThrow(() -> new IllegalArgumentException("Team with name '" + name + "' not found"));
}


    public void updateTeam(String id, Team team) {
        Team teamToUpdate = getTeamById(id);
        teamToUpdate.setName(team.getName());
        teamToUpdate.setEmployeeIds(team.getEmployeeIds());
        saveTeam(teamToUpdate);
    }

    public void addEmployeesToTeam(String teamName, List<String> employeeIds) {
        Team team = teamRepository.findAll().stream()
                .filter(t -> t.getName().equals(teamName))
                .findFirst()
                .orElseThrow(() -> new IllegalArgumentException("Team with name '" + teamName + "' not found"));

        String teamId = team.getId();
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

    public void addEmployeesToTeam(String teamName, List<String> employeeIds, String groupName) {
        Team team = teamRepository.findAll().stream()
                .filter(t -> t.getName().equals(teamName) && groupName.equals(t.getGroupName()))
                .findFirst()
                .orElseThrow(() -> new IllegalArgumentException("Team with name '" + teamName + "' and group '" + groupName + "' not found"));

        String teamId = team.getId();
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



    public void setEmployeeFirstPreference(String employeeId, String teamName) {
        // Busca o employee
        Employee employee = employeeService.getEmployeeById(employeeId);

        // Busca o team pelo nome
        Team team = teamRepository.findByName(teamName)
                .orElseThrow(() -> new IllegalArgumentException("Team with name " + teamName + " not found"));

        // Atualiza o set de teamIds do employee (LinkedHashSet para garantir ordem)
        Set<String> currentTeamIds = employee.getTeamIds() != null ? new LinkedHashSet<>(employee.getTeamIds()) : new LinkedHashSet<>();
        currentTeamIds.remove(team.getId());  // Remove se já estiver
        LinkedHashSet<String> updatedTeamIds = new LinkedHashSet<>();
        updatedTeamIds.add(team.getId());     // Adiciona como primeira preferência
        updatedTeamIds.addAll(currentTeamIds);
        employee.setTeamIds(updatedTeamIds);

        // Atualiza o list de employeeIds do team (ArrayList mantendo ordem)
        List<String> currentEmployeeIds = team.getEmployeeIds() != null ? new ArrayList<>(team.getEmployeeIds()) : new ArrayList<>();
        if (!currentEmployeeIds.contains(employeeId)) {
            currentEmployeeIds.add(employeeId);
            team.setEmployeeIds(currentEmployeeIds);
        }

        // Salva ambos no banco
        employeeService.saveEmployee(employee);
        teamRepository.save(team);
    }

    public void setEmployeeTeamAtPosition(String employeeId, String teamName, int position) {
        // Busca employee
        Employee employee = employeeService.getEmployeeById(employeeId);

        // Busca team pelo nome
        Team team = teamRepository.findByName(teamName)
                .orElseThrow(() -> new IllegalArgumentException("Team with name " + teamName + " not found"));

        // Prepara a lista ordenada
        List<String> teamIdList = employee.getTeamIds() != null ? new ArrayList<>(employee.getTeamIds()) : new ArrayList<>();

        // Remove se já existir na lista
        teamIdList.remove(team.getId());

        // Corrige a posição (Java é indexado em 0)
        int insertIndex = Math.max(0, Math.min(position - 1, teamIdList.size()));
        teamIdList.add(insertIndex, team.getId());

        // Atualiza o employee
        employee.setTeamIds(new LinkedHashSet<>(teamIdList));

        // Atualiza o team, adicionando employeeId se necessário
        List<String> employeeIds = team.getEmployeeIds() != null ? new ArrayList<>(team.getEmployeeIds()) : new ArrayList<>();
        if (!employeeIds.contains(employeeId)) {
            employeeIds.add(employeeId);
            team.setEmployeeIds(employeeIds);
        }

        // Salva ambos
        employeeService.saveEmployee(employee);
        teamRepository.save(team);
    }

    public void removeEmployeeFromTeam(String employeeId, String teamName) {
        // Busca o time pelo nome
        Team team = teamRepository.findAll().stream()
                .filter(t -> t.getName().equals(teamName))
                .findFirst()
                .orElseThrow(() -> new IllegalArgumentException("Team not found"));

        // Remove o employeeId da lista do time
        List<String> employeeIds = team.getEmployeeIds();
        if (employeeIds.contains(employeeId)) {
            employeeIds.remove(employeeId);
            team.setEmployeeIds(employeeIds);
            saveTeam(team);
        }

        // Remove o teamId do employee
        Employee employee = employeeService.getEmployeeById(employeeId);
        Set<String> teamIds = employee.getTeamIds();
        if (teamIds.contains(team.getId())) {
            teamIds.remove(team.getId());
            employee.setTeamIds(teamIds);
            employeeService.saveEmployee(employee);
        }
    }


    public void deleteTeam(String teamName) {
        Team team = teamRepository.findAll().stream()
                .filter(t -> t.getName().equals(teamName))
                .findFirst()
                .orElseThrow(() -> new IllegalArgumentException("Team with name '" + teamName + "' not found"));

        String teamId = team.getId();

        // Remove o teamId de todos os employees
        List<String> employeeIds = team.getEmployeeIds();
        for (String employeeId : employeeIds) {
            Employee employee = employeeService.getEmployeeById(employeeId);
            Set<String> teamIds = employee.getTeamIds();
            if (teamIds.contains(teamId)) {
                teamIds.remove(teamId);
                employee.setTeamIds(teamIds);
                employeeService.saveEmployee(employee);
            }
        }

        // Finalmente, apaga o time do banco
        teamRepository.deleteById(teamId);
    }




    public void saveTeam(Team team) {
        teamRepository.save(team);
    }
}
