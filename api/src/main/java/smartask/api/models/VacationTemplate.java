package smartask.api.models;

import jakarta.validation.constraints.NotBlank;
import lombok.Builder;
import org.springframework.data.annotation.Id;
import org.springframework.data.mongodb.core.mapping.Document;

import java.util.List;
import java.util.Map;

@Document(collection = "vacations")
@Builder
public class VacationTemplate {

    @Id
    private String id;

    @NotBlank
    private String name;

    private Map<String, List<String>> vacations;
}
