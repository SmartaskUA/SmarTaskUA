package smartask.api.models;

import jakarta.validation.constraints.NotBlank;
import lombok.AllArgsConstructor;
import lombok.Builder;
import lombok.Data;
import lombok.NoArgsConstructor;
import lombok.Builder.Default;
import org.springframework.data.annotation.Id;
import org.springframework.data.mongodb.core.index.Indexed;
import org.springframework.data.mongodb.core.mapping.Document;

import java.time.Instant;

@Document(collection = "problems")
@Data
@NoArgsConstructor
@AllArgsConstructor
@Builder
public class ProblemDefinition {

    @Id
    private String id;

    @NotBlank
    @Indexed(unique = true)
    private String problemId;

    private String problemPath;

    @Default
    private Instant createdAt = Instant.now();

    @Default
    private Instant updatedAt = Instant.now();
}
