package smartask.api.controllers;

import io.swagger.v3.oas.annotations.Operation;
import io.swagger.v3.oas.annotations.tags.Tag;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.http.HttpStatus;
import org.springframework.http.ResponseEntity;
import org.springframework.web.bind.annotation.*;
import smartask.api.models.Employee;
import smartask.api.models.requests.RestrictionRequest;
import smartask.api.models.requests.UpdateEmployee;
import smartask.api.services.EmployeeService;

import java.util.List;
import java.util.Map;

@Tag(name = "Employee", description = "Employees Management")
@RestController
@RequestMapping("/api/v1/employees")
@CrossOrigin(origins = "http://localhost:5173")
public class EmployeesController {

    @Autowired
    private EmployeeService employeeService;

    public EmployeesController(EmployeeService employeeService) {
        this.employeeService = employeeService;
    }

    @Operation(summary = "Get all employees")
    @GetMapping("/")
    public ResponseEntity<List<Employee>> getEmployees() {
        List<Employee> employees = employeeService.getEmployees();
        return new ResponseEntity<>(employees, HttpStatus.OK);
    }

    @Operation(summary = "Add a new employee")
    @PostMapping("/")
    public ResponseEntity<String> addEmployee(@RequestBody Employee employee) {
        employeeService.addEmployee(employee);
        return ResponseEntity.ok("Employee created successfully");
    }

    @Operation(summary = "Get an employee by ID")
    @GetMapping("/{id}")
    public ResponseEntity<Employee> getEmployeeById(@PathVariable String id) {
        Employee employee = employeeService.getEmployeeById(id);
        return new ResponseEntity<>(employee, HttpStatus.OK);
    }

    @Operation(summary = "Update employee's name by their ID")
    @PutMapping("/{id}")
    public ResponseEntity<String> updateEmployee(@RequestBody UpdateEmployee updateEmployeeRequest,
                                                 @PathVariable String id) {
        employeeService.updateEmployeeName(id, updateEmployeeRequest);
        return ResponseEntity.ok("Employee name updated successfully");
    }



    @Operation(summary = "Delete an employee by ID")
    @DeleteMapping("/{id}")
    public ResponseEntity<String> deleteEmployeeById(@PathVariable String id) {
        employeeService.deleteEmployeeById(id);
        return ResponseEntity.ok("Employee with ID " + id + " deleted successfully");
    }

    @Operation(summary = "Delete an employee by name")
    @DeleteMapping("/by-name/{name}")
    public ResponseEntity<String> deleteEmployeeByName(@PathVariable String name) {
        employeeService.deleteEmployeeByName(name);
        return ResponseEntity.ok("Employee with name '" + name + "' deleted successfully");
    }

}
