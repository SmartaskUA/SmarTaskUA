package smartask.api.controllers;

import io.swagger.v3.oas.annotations.Operation;
import io.swagger.v3.oas.annotations.tags.Tag;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.http.HttpStatus;
import org.springframework.http.ResponseEntity;
import org.springframework.web.bind.annotation.*;
import smartask.api.models.Employee;
import smartask.api.models.requests.RestrictionRequest;
import smartask.api.services.EmployeeService;
import java.util.List;
import java.util.Map;

@Tag(name = "Employee", description = "Employees Management")
@RestController
@RequestMapping("/api/v1/employees")
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
    public ResponseEntity<Employee> getEmployeeById(@PathVariable Long id) {
        Employee employee = employeeService.getEmployeeById(id);
        return new ResponseEntity<>(employee, HttpStatus.OK);
    }

    @Operation(summary = "Update an employee")
    @PutMapping("/{id}")
    public ResponseEntity<String> updateEmployee(@RequestBody Employee employee, @PathVariable Long id) {
        employeeService.updateEmployee(id, employee);
        return ResponseEntity.ok("Employee updated successfully");
    }

    @Operation(summary = "Get all the restriction to an employee by their ID")
    @GetMapping("/restriction/{id}")
    public ResponseEntity<Map<String, List<String>>> getRestriction(@PathVariable Long id) {
        return ResponseEntity.ok(employeeService.getEmployeeRestrictions(id));
    }

    @Operation(summary = "Add new restriction to an employee by their ID")
    @PostMapping("/restriction/{id}")
    public ResponseEntity<String> addRestriction(@RequestBody RestrictionRequest restrictionRequest,
                                                 @PathVariable Long id) {
        System.out.println(restrictionRequest+" for "+id);
        employeeService.addRestrictionToEmployee(id, restrictionRequest.getRestrictionType(), restrictionRequest.getDate());
        return ResponseEntity.ok("Restriction added successfully");
    }

    @Operation(summary = "Update new restriction to an employee by their ID")
    @PutMapping("/restriction/{id}")
    public ResponseEntity<String> updateRestriction(@RequestBody RestrictionRequest restrictionRequest,
                                                    @PathVariable Long id) {
        System.out.println(restrictionRequest+" for "+id);
        // Process the received restrictionType and date
        return ResponseEntity.ok("Restriction update successfully");
    }

    @Operation(summary = "Delete new restriction to an employee by their ID")
    @DeleteMapping("/restriction/{id}")
    public ResponseEntity<String> deleteRestriction(@RequestBody RestrictionRequest restrictionRequest,
                                                    @PathVariable Long id) {
        System.out.println(restrictionRequest+" for "+id);
        employeeService.removeRestrictionFromEmployee(id, restrictionRequest.getRestrictionType(), restrictionRequest.getDate());
        return ResponseEntity.ok("Restriction deleted successfully");
    }
}
