package smartask.api.services;

import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.stereotype.Service;
import smartask.api.models.Team;
import smartask.api.repositories.TeamRepository;

import java.util.List;
import java.util.Optional;

@Service
public class TeamService {
    @Autowired
    private TeamRepository teamRepository;

    @Autowired
    private SequenceGeneratorService sequenceGeneratorService;

    public TeamService(TeamRepository teamRepository) {
        this.teamRepository = teamRepository;
    }

    public List<Team> getTeams(){
        return teamRepository.findAll();
    }

    public void addTeam(Team team){
        saveTeam(team);
    }

    public Team getTeamById(String id){
        Optional<Team> optionalTeam = teamRepository.findById(id);
        if (!optionalTeam.isPresent()) {
            throw new IllegalArgumentException("Team not found");
        }
        return optionalTeam.get();
    }

    public void updateTeam(String id, Team team){
        Team teamToUpdate = getTeamById(id);
        teamToUpdate.setName(team.getName());
        teamToUpdate.setEmployees(team.getEmployees());
        saveTeam(teamToUpdate);
    }

    public void saveTeam(Team team) {
        teamRepository.save(team);
    }
    
}
