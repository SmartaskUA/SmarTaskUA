package smartask.api.repositories;

import org.springframework.data.mongodb.repository.MongoRepository;
import org.springframework.stereotype.Repository;
import smartask.api.models.RuleSet;

import java.util.Optional;

@Repository
public interface RuleSetRepository extends MongoRepository<RuleSet, String> {
    Optional<RuleSet> findByName(String name);
}
