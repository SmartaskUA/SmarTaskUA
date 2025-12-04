package smartask.api.repositories;

import org.springframework.data.mongodb.repository.MongoRepository;
import org.springframework.stereotype.Repository;
import java.util.Optional;
import smartask.api.models.Schedule;
import java.util.List;

@Repository
public interface SchedulesRepository extends MongoRepository<Schedule, String> {
    boolean existsByTitle(String sample);
    Optional<Schedule> findByTitle(String title);
    boolean existsByTitleAndAlgorithm(String title, String algorithm);
}
