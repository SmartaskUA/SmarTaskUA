package smartask.api.repositories;

import org.springframework.data.mongodb.repository.MongoRepository;
import smartask.api.models.VacationTemplate;

import java.util.Optional;

public interface VacationTemplateRepository  extends MongoRepository<VacationTemplate, String> {
    Optional<VacationTemplate> findByName(String name);
}
