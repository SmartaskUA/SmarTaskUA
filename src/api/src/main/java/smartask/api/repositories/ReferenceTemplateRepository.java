package smartask.api.repositories;

import org.springframework.data.mongodb.repository.MongoRepository;
import smartask.api.models.ReferenceTemplate;
import java.util.Optional;

public interface ReferenceTemplateRepository extends MongoRepository<ReferenceTemplate, String> {
    Optional<ReferenceTemplate> findByName(String name);
}
