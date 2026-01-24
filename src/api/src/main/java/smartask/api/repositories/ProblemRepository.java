package smartask.api.repositories;

import org.springframework.data.mongodb.repository.MongoRepository;
import org.springframework.stereotype.Repository;
import smartask.api.models.ProblemDefinition;

import java.util.Optional;

@Repository
public interface ProblemRepository extends MongoRepository<ProblemDefinition, String> {
    Optional<ProblemDefinition> findByProblemId(String problemId);
}
