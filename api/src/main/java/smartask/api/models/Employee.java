package smartask.api.models;

import java.util.List;

import org.springframework.data.annotation.Id;

import jakarta.persistence.GeneratedValue;
import jakarta.persistence.GenerationType;
import jakarta.persistence.Entity;

@Entity(name = "employee")
public class Employee {
    @Id
    @GeneratedValue(strategy = GenerationType.AUTO)
    private Long id;
    private String name;
    private List<String> restrictions;

    public Employee(String name, List<String> restrictions) {
        this.name = name;
        this.restrictions = restrictions;
    }
}
