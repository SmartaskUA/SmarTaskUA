package smartask.api.dataAccess;


import org.springframework.data.mongodb.repository.MongoRepository;
import org.springframework.stereotype.Repository;
import smartask.api.entity.Schedule;

import java.util.List;

@Repository
public interface SchedulesRepository
        extends MongoRepository<Schedule, String> {
}
