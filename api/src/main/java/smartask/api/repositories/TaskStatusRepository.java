package smartask.api.repositories;

import org.springframework.data.jpa.repository.JpaRepository;
import org.springframework.data.mongodb.repository.MongoRepository;
import org.springframework.stereotype.Repository;
import smartask.api.models.TaskStatus;

import java.util.Optional;

@Repository
public interface TaskStatusRepository extends MongoRepository<TaskStatus, String> {
    Optional<TaskStatus> findByTaskId(String taskId);
}
