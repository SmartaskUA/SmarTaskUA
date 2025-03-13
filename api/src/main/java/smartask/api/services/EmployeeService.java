package smartask.api.services;

import com.fasterxml.jackson.databind.JsonNode;
import com.fasterxml.jackson.databind.ObjectMapper;
import com.fasterxml.jackson.databind.node.ObjectNode;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.stereotype.Service;
import smartask.api.models.Employee;
import smartask.api.repositories.EmployeesRepository;

import java.util.List;
import java.util.Optional;

@Service
public class EmployeeService {
    @Autowired
    private EmployeesRepository repository;

    @Autowired
    private ObjectMapper objectMapper;

    public void addRestrictionToEmployee(String employeeName, String restrictionType, String date) {
        Optional<Employee> optionalEmployee = repository.findByName(employeeName);

        if (!optionalEmployee.isPresent()) {
            throw new IllegalArgumentException("Employee not found");
        }

        Employee employee = optionalEmployee.get();

        JsonNode restrictions = employee.getRestrictions();

        // Check if restrictions is null or not an ObjectNode
        if (restrictions == null || !restrictions.isObject()) {
            // Create a new ObjectNode if the restrictions is null or not an object
            restrictions = objectMapper.createObjectNode();
        }

        // Cast restrictions to ObjectNode (since we know it's now an object)
        ObjectNode restrictionsNode = (ObjectNode) restrictions;

        // Add or update the restriction
        restrictionsNode.put(restrictionType, date);  // Add the new restriction or update the existing one

        // Update the employee's restrictions with the modified JSON
        employee.setRestrictions(restrictionsNode);

        // Save the updated employee back to the database
        repository.save(employee);
    }


    public List<Employee> getAll(){
        return repository.findAll();
    }

    public Optional<Employee> findByName(String name){
        return repository.findByName(name);
    }
}
