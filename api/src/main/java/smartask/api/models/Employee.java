package smartask.api.models;

import com.fasterxml.jackson.databind.JsonNode;
import com.fasterxml.jackson.databind.annotation.JsonDeserialize;
import com.fasterxml.jackson.databind.annotation.JsonSerialize;
import lombok.Getter;
import lombok.RequiredArgsConstructor;
import lombok.Setter;
import org.bson.types.ObjectId;
import org.springframework.data.annotation.Id;
import org.springframework.data.mongodb.core.mapping.Document;
import smartask.api.utils.JsonNodeDeserializer;
import smartask.api.utils.JsonNodeSerializer;

@Document(collection = "employees")
@Getter
@Setter
@RequiredArgsConstructor
public class Employee {
    @Id
    private ObjectId id;
    private String name;

    // Restrictions as JsonNode, which will be serialized/deserialized as JSON
    @JsonSerialize(using = JsonNodeSerializer.class)
    @JsonDeserialize(using = JsonNodeDeserializer.class)
    private JsonNode restrictions;

    public Employee(String name) {
        this.id = new ObjectId();  // Manually assign a new ObjectId
        this.name = name;
    }

    // Setter and Getter methods for restrictions are optional
    public void setRestrictions(JsonNode restrictions) {
        this.restrictions = restrictions;
    }

    public JsonNode getRestrictions() {
        return this.restrictions;
    }
}
