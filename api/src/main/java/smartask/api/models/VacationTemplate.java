package smartask.api.models;

import jakarta.validation.constraints.NotBlank;
import lombok.Builder;
import lombok.Data;
import org.springframework.data.annotation.Id;
import org.springframework.data.mongodb.core.mapping.Document;

import java.util.List;
import java.util.Map;

@Document(collection = "vacations")
@Builder
@Data
public class VacationTemplate {

    @Id
    private String id;

    @NotBlank
    private String name;

    private List<List<String>> vacations;
}
