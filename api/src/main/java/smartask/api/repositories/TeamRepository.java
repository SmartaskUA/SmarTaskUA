package smartask.api.repositories;

import org.springframework.data.mongodb.repository.MongoRepository;
import org.springframework.stereotype.Repository;
import smartask.api.models.Employee;
import smartask.api.models.Team;

import java.util.List;
import java.util.Optional;

@Repository
public interface TeamRepository extends MongoRepository<Team, String> {
    Optional<Team> findById(String id);
    Optional<Team> findByName(String name);
    List<Team> findByEmployeeIdsContains(String employeeId);

}
