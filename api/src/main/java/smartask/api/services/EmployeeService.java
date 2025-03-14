package smartask.api.services;

import com.fasterxml.jackson.databind.JsonNode;
import com.fasterxml.jackson.databind.ObjectMapper;
import com.fasterxml.jackson.databind.node.ObjectNode;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.stereotype.Service;
import smartask.api.models.Employee;
import smartask.api.repositories.EmployeesRepository;

import java.util.*;

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

        // Ensure the restrictions map is initialized
        if (employee.getRestrictions() == null) {
            employee.setRestrictions(new HashMap<>());
        }

        // Get or create the list of dates for the restriction type
        employee.getRestrictions().computeIfAbsent(restrictionType, k -> new ArrayList<>());

        // Add the new date if it's not already in the list
        if (!employee.getRestrictions().get(restrictionType).contains(date)) {
            employee.getRestrictions().get(restrictionType).add(date);
        }

        // Save the updated employee back to the database
        repository.save(employee);
    }

    public void removeRestrictionFromEmployee(String employeeName, String restrictionType, String date) {
        Optional<Employee> optionalEmployee = repository.findByName(employeeName);

        if (!optionalEmployee.isPresent()) {
            throw new IllegalArgumentException("Employee not found");
        }

        Employee employee = optionalEmployee.get();

        // Ensure the restrictions map exists
        if (employee.getRestrictions() == null) {
            return; // No restrictions to remove
        }

        // Get the list of dates for the restriction type
        List<String> dates = employee.getRestrictions().get(restrictionType);

        if (dates != null) {
            dates.remove(date); // Remove the specified date

            // If the list is empty, remove the restriction type from the map
            if (dates.isEmpty()) {
                employee.getRestrictions().remove(restrictionType);
            }

            // Save the updated employee back to the database
            repository.save(employee);
        }
    }

    public Map<String, List<String>> getEmployeeRestrictions(String employeeName) {
        Optional<Employee> optionalEmployee = repository.findByName(employeeName);

        if (!optionalEmployee.isPresent()) {
            throw new IllegalArgumentException("Employee not found");
        }

        Employee employee = optionalEmployee.get();

        // Return a copy of the restrictions map to avoid modifications outside this method
        return employee.getRestrictions() != null ? new HashMap<>(employee.getRestrictions()) : new HashMap<>();
    }




    public List<Employee> getAll(){
        return repository.findAll();
    }

    public Optional<Employee> findByName(String name){
        return repository.findByName(name);
    }
}
