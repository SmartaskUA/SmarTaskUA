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


    @Operation(summary = "Get all the restrictions for an employee by their ID")
    @GetMapping("/restriction/{id}")
    public ResponseEntity<Map<String, List<String>>> getRestriction(@PathVariable String id) {
        return ResponseEntity.ok(employeeService.getEmployeeRestrictions(id));
    }

    @Operation(summary = "Add new restriction to an employee by their ID")
    @PostMapping("/restriction/{id}")
    public ResponseEntity<String> addRestriction(@RequestBody RestrictionRequest restrictionRequest,
                                                 @PathVariable String id) {
        System.out.println(restrictionRequest + " for " + id);
        employeeService.addRestrictionToEmployee(id, restrictionRequest.getRestrictionType(), restrictionRequest.getDate());
        return ResponseEntity.ok("Restriction added successfully");
    }

    @Operation(summary = "Update restriction for an employee by their ID")
    @PutMapping("/restriction/{id}")
    public ResponseEntity<String> updateRestriction(@RequestBody RestrictionRequest restrictionRequest,
                                                    @PathVariable String id) {
        System.out.println(restrictionRequest + " for " + id);
        // Process the received restrictionType and date (a ser implementado, se necessário)
        return ResponseEntity.ok("Restriction updated successfully");
    }

    @Operation(summary = "Delete restriction for an employee by their ID")
    @DeleteMapping("/restriction/{id}")
    public ResponseEntity<String> deleteRestriction(@RequestBody RestrictionRequest restrictionRequest,
                                                    @PathVariable String id) {
        System.out.println(restrictionRequest + " for " + id);
        employeeService.removeRestrictionFromEmployee(id, restrictionRequest.getRestrictionType(), restrictionRequest.getDate());
        return ResponseEntity.ok("Restriction deleted successfully");
    }
}
