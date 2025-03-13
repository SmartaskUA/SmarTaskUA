package smartask.api.services;

import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.stereotype.Service;
import smartask.api.models.Employee;
import smartask.api.repositories.EmployeesRepository;

@Service
public class TeamService {
    @Autowired
    private TeamRepository teamRepository;

    public TeamService(TeamRepository teamRepository) {
        this.teamRepository = teamRepository;
    }

    public List<Team> getTeams(){
        return teamRepository.findAll();
    }

    public void addTeam(Team team){
        teamRepository.save(team);
    }

    public Team getTeamById(Long id){
        Optional<Team> optionalTeam = teamRepository.findById(id);
        if (!optionalTeam.isPresent()) {
            throw new IllegalArgumentException("Team not found");
        }
        return optionalTeam.get();
    }
    
}
