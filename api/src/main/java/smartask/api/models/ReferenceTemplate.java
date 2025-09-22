package smartask.api.models;

import jakarta.validation.constraints.NotBlank;
import lombok.*;
import org.springframework.data.annotation.Id;
import org.springframework.data.mongodb.core.index.Indexed;
import org.springframework.data.mongodb.core.mapping.Document;

import java.util.List;

@Document(collection = "reference")
@Data
@NoArgsConstructor
@AllArgsConstructor
@Builder
public class ReferenceTemplate {

    @Id
    private String id;

    @NotBlank
    @Indexed(unique = true)        
    private String name;

    private List<List<String>> minimuns; 
}
