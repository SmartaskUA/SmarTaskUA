package smartask.api.models;

import lombok.NoArgsConstructor;
import org.springframework.data.annotation.Id;
import org.springframework.data.mongodb.core.mapping.Document;
import jakarta.validation.constraints.NotBlank;

import java.util.*;

@Document(collection = "employees")
@NoArgsConstructor
public class Employee {

    @Id
    private String id;

    @NotBlank
    private String name;

    // Armazena os IDs dos times aos quais pertence
    private Set<String> teamIds = new LinkedHashSet<>();


    public Employee(String name) {
        this.name = name;
    }

    public String getId() { return id; }
    public void setId(String id) { this.id = id; }

    public String getName() { return name; }
    public void setName(String name) { this.name = name; }

    public Set<String> getTeamIds() { return teamIds; }
    public void setTeamIds(Set<String> teamIds) { this.teamIds = teamIds; }

}
