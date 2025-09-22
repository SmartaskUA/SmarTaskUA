package smartask.api.models;

import org.springframework.data.annotation.Id;
import org.springframework.data.mongodb.core.mapping.Document;
import jakarta.validation.constraints.NotBlank;

import java.util.ArrayList;
import java.util.List;

@Document(collection = "teams")
public class Team {

    @Id
    private String id;

    @NotBlank
    private String name;

    // Armazena apenas os IDs dos funcionários
    private List<String> employeeIds = new ArrayList<>();

    public Team() { }

    public Team(String name) {
        this.name = name;
    }

    public String getId() { return id; }
    public void setId(String id) { this.id = id; }

    public String getName() { return name; }
    public void setName(String name) { this.name = name; }

    public List<String> getEmployeeIds() { return employeeIds; }
    public void setEmployeeIds(List<String> employeeIds) { this.employeeIds = employeeIds; }
}
