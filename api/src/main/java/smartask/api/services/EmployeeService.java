package smartask.api.services;

import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.stereotype.Service;
import smartask.api.models.Employee;
import smartask.api.models.requests.UpdateEmployee;
import smartask.api.models.Team;
import smartask.api.repositories.EmployeesRepository;
import org.springframework.transaction.annotation.Transactional; 
import smartask.api.repositories.TeamRepository;

import java.util.*;

@Service
public class EmployeeService {

    private final EmployeesRepository employeesRepository;
    private final TeamRepository teamsRepository;

    public EmployeeService(EmployeesRepository employeesRepository, TeamRepository teamsRepository) {
        this.employeesRepository = employeesRepository;
        this.teamsRepository = teamsRepository;
    }


    public List<Employee> getEmployees() {
        return employeesRepository.findAll();
    }

    public void addEmployee(Employee employee) {
        saveEmployee(employee);
    }

    public Employee getEmployeeById(String id) {
        return employeesRepository.findById(id).orElseThrow(() -> new IllegalArgumentException("Employee not found"));
    }



    public void updateEmployeeName(String id, UpdateEmployee updateEmployeeRequest) {
        Employee employeeToUpdate = getEmployeeById(id);
        employeeToUpdate.setName(updateEmployeeRequest.getName());
        saveEmployee(employeeToUpdate);
    }



    public void saveEmployee(Employee employee) {
        employeesRepository.save(employee);
    }


    @Transactional
    public void deleteEmployeeById(String id) {
        if (!employeesRepository.existsById(id)) {
            throw new IllegalArgumentException("Employee with ID " + id + " not found.");
        }

        // Deletes employeeId from every team that contains it
        List<Team> teams = teamsRepository.findByEmployeeIdsContains(id);
        for (Team t : teams) {
            t.getEmployeeIds().removeIf(empId -> empId.equals(id));
        }
        teamsRepository.saveAll(teams);

        employeesRepository.deleteById(id);
    }

    @Transactional
    public void deleteEmployeeByName(String name) {
        Optional<Employee> optional = employeesRepository.findByName(name);
        if (optional.isEmpty()) {
            throw new IllegalArgumentException("Employee with name '" + name + "' not found.");
        }

        String employeeId = optional.get().getId();

        // Deletes employeeId from every team that contains it
        List<Team> teams = teamsRepository.findByEmployeeIdsContains(employeeId);
        for (Team t : teams) {
            t.getEmployeeIds().removeIf(empId -> empId.equals(employeeId));
        }
        teamsRepository.saveAll(teams);

        employeesRepository.delete(optional.get());
    }

}
