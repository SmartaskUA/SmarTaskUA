package smartask.api.services;

import com.fasterxml.jackson.databind.JsonNode;
import com.fasterxml.jackson.databind.ObjectMapper;
import com.fasterxml.jackson.databind.node.ObjectNode;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.stereotype.Service;
import smartask.api.models.Employee;
import smartask.api.repositories.EmployeesRepository;

import java.util.ArrayList;
import java.util.HashMap;
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




    public List<Employee> getAll(){
        return repository.findAll();
    }

    public Optional<Employee> findByName(String name){
        return repository.findByName(name);
    }
}
