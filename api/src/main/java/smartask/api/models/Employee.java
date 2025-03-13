package smartask.api.models;

import lombok.Getter;
import lombok.RequiredArgsConstructor;
import lombok.Setter;
import org.bson.types.ObjectId;
import org.springframework.data.annotation.Id;
import org.springframework.data.mongodb.core.mapping.Document;

import java.util.HashMap;
import java.util.List;
import java.util.Map;

@Document(collection = "employees")
@Getter
@Setter
@RequiredArgsConstructor
public class Employee {
    @Id
    private ObjectId id;
    private String name;

    private Map<String, List<String>> restrictions; // Updated to store multiple dates per restriction type

    public Employee(String name) {
        this.id = new ObjectId();
        this.name = name;
        this.restrictions = new HashMap<>(); // Initialize to avoid null pointer issues
    }

    public void setRestrictions(Map<String, List<String>> restrictions) {
        this.restrictions = restrictions;
    }

    public Map<String, List<String>> getRestrictions() {
        return this.restrictions;
    }
}
