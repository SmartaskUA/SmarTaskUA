package smartask.api.models;

import jakarta.validation.constraints.NotBlank;
import lombok.Builder;
import lombok.Data;
import org.springframework.data.annotation.Id;
import org.springframework.data.mongodb.core.mapping.Document;

import java.util.List;
import java.util.Map;

@Document(collection = "reference")
@Builder
@Data
public class ReferenceTemplate {
    @Id
    private String id;

    @NotBlank
    private String name;

    private Map<String, List<String>> minimuns;
}
