package smartask.api.repositories;


import org.springframework.data.mongodb.repository.MongoRepository;
import org.springframework.stereotype.Repository;

import smartask.api.models.Schedule;

import java.util.List;

@Repository
public interface SchedulesRepository
        extends MongoRepository<Schedule, String> {
}
