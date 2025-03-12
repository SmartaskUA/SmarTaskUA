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
    private JsonNode restrictions;
    public Employee(String name) {
        this.id = new ObjectId(); // Manually assign a new ObjectId
        this.name = name;
    }
}
