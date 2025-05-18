package smartask.api.services;

import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.stereotype.Service;
import smartask.api.models.Employee;
import smartask.api.models.requests.UpdateEmployee;
import smartask.api.repositories.EmployeesRepository;

import java.util.*;

@Service
public class EmployeeService {
    @Autowired
    private EmployeesRepository repository;

    public EmployeeService(EmployeesRepository repository) {
        this.repository = repository;
    }

    public List<Employee> getEmployees() {
        return repository.findAll();
    }

    public void addEmployee(Employee employee) {
        saveEmployee(employee);
    }

    public Employee getEmployeeById(String id) {
        return repository.findById(id).orElseThrow(() -> new IllegalArgumentException("Employee not found"));
    }



    public void updateEmployeeName(String id, UpdateEmployee updateEmployeeRequest) {
        Employee employeeToUpdate = getEmployeeById(id);
        employeeToUpdate.setName(updateEmployeeRequest.getName());
        saveEmployee(employeeToUpdate);
    }



    public void saveEmployee(Employee employee) {
        repository.save(employee);
    }


    public void deleteEmployeeById(String id) {
        if (!repository.existsById(id)) {
            throw new IllegalArgumentException("Employee with ID " + id + " not found.");
        }
        repository.deleteById(id);
    }

    public void deleteEmployeeByName(String name) {
        Optional<Employee> optional = repository.findByName(name);
        if (optional.isEmpty()) {
            throw new IllegalArgumentException("Employee with name '" + name + "' not found.");
        }
        repository.delete(optional.get());
    }

}
