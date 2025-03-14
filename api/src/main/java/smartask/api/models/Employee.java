package smartask.api.models;

import org.bson.types.ObjectId;
import org.springframework.data.annotation.Id;
import org.springframework.data.mongodb.core.mapping.Document;

import jakarta.persistence.GeneratedValue;
import jakarta.persistence.GenerationType;
import jakarta.validation.constraints.NotBlank;

import java.util.HashMap;
import java.util.List;
import java.util.Map;

@Document(collection = "employees")
public class Employee {
    @Id
    private Long id;

    @NotBlank
    private String name;

    private Team team;

    private Map<String, List<String>> restrictions;

    public Employee(String name, Team team) {
        this.name = name;
        this.team = team;
        this.restrictions = new HashMap<>();
    }

    public Long getId() {
        return this.id;
    }

    public void setId(Long id) {
        this.id = id;
    }

    public String getName() {
        return this.name;
    }

    public void setName(String name) {
        this.name = name;
    }

    public Team getTeam() {
        return this.team;
    }

    public void setTeam(Team team) {
        this.team = team;
    }

    public void setRestrictions(Map<String, List<String>> restrictions) {
        this.restrictions = restrictions;
    }

    public Map<String, List<String>> getRestrictions() {
        return this.restrictions;
    }
}
