package smartask.api.repositories;

import org.springframework.data.mongodb.repository.MongoRepository;
import smartask.api.models.VacationTemplate;

public interface VacationTemplateRepository  extends MongoRepository<VacationTemplate, String> {
}
