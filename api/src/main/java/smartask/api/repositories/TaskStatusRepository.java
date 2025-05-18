package smartask.api.repositories;

import org.springframework.data.jpa.repository.JpaRepository;
import org.springframework.data.mongodb.repository.MongoRepository;
import org.springframework.stereotype.Repository;
import smartask.api.models.TaskStatus;

import java.util.Optional;

@Repository
public interface TaskStatusRepository extends MongoRepository<TaskStatus, String> {
    Optional<TaskStatus> findByTaskId(String taskId);
    void deleteByTaskId(String taskId);
    Optional<TaskStatus> findByScheduleRequest_Title(String title);
    void deleteByScheduleRequest_Title(String title);
    void deleteAllByScheduleRequest_Title(String title);
}
