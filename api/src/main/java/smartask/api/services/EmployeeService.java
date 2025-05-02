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

    public void updateEmployee(String id, Employee employee) {
        Employee employeeToUpdate = getEmployeeById(id);
        employeeToUpdate.setName(employee.getName());
        employeeToUpdate.setRestrictions(employee.getRestrictions());
        employeeToUpdate.setTeamIds(employee.getTeamIds());
        saveEmployee(employeeToUpdate);
    }

    public void updateEmployeeName(String id, UpdateEmployee updateEmployeeRequest) {
        Employee employeeToUpdate = getEmployeeById(id);
        employeeToUpdate.setName(updateEmployeeRequest.getName());
        saveEmployee(employeeToUpdate);
    }

    public void addRestrictionToEmployee(String id, String restrictionType, String date) {
        Employee employee = getEmployeeById(id);
        employee.getRestrictions().computeIfAbsent(restrictionType, k -> new ArrayList<>());
        if (!employee.getRestrictions().get(restrictionType).contains(date)) {
            employee.getRestrictions().get(restrictionType).add(date);
        }
        saveEmployee(employee);
    }

    public void removeRestrictionFromEmployee(String id, String restrictionType, String date) {
        Employee employee = getEmployeeById(id);
        if (employee.getRestrictions() == null) return;
        List<String> dates = employee.getRestrictions().get(restrictionType);
        if (dates != null) {
            dates.remove(date);
            if (dates.isEmpty()) {
                employee.getRestrictions().remove(restrictionType);
            }
            saveEmployee(employee);
        }
    }

    public Map<String, List<String>> getEmployeeRestrictions(String id) {
        Employee employee = getEmployeeById(id);
        return employee.getRestrictions() != null ? new HashMap<>(employee.getRestrictions()) : new HashMap<>();
    }

    public void saveEmployee(Employee employee) {
        repository.save(employee);
    }
}
