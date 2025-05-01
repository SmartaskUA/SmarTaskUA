package smartask.api.models;

import org.springframework.data.annotation.Id;
import org.springframework.data.mongodb.core.mapping.Document;
import jakarta.validation.constraints.NotBlank;

import java.util.*;

@Document(collection = "employees")
public class Employee {

    @Id
    private String id;

    @NotBlank
    private String name;

    // Armazena os IDs dos times aos quais pertence
    private Set<String> teamIds = new HashSet<>();

    private Map<String, List<String>> restrictions = new HashMap<>();

    public Employee(String name) {
        this.name = name;
    }

    public String getId() { return id; }
    public void setId(String id) { this.id = id; }

    public String getName() { return name; }
    public void setName(String name) { this.name = name; }

    public Set<String> getTeamIds() { return teamIds; }
    public void setTeamIds(Set<String> teamIds) { this.teamIds = teamIds; }

    public Map<String, List<String>> getRestrictions() { return restrictions; }
    public void setRestrictions(Map<String, List<String>> restrictions) { this.restrictions = restrictions; }
}
