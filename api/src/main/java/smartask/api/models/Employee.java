package smartask.api.models;

import com.fasterxml.jackson.databind.JsonNode;
import lombok.Getter;
import lombok.RequiredArgsConstructor;
import lombok.Setter;
import org.bson.types.ObjectId;
import org.springframework.data.annotation.Id;
import org.springframework.data.mongodb.core.mapping.Document;

@Document(collection = "employees")
@Getter
@Setter
@RequiredArgsConstructor
public class Employee {
    @Id
    private ObjectId id;
    private String name;
    private JsonNode restrictions; // Stores JSON object directly

    public Employee(String name) {
        this.name = name;
    }
}
