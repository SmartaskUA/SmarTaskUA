package smartask.api.controllers;

import io.swagger.v3.oas.annotations.Operation;
import io.swagger.v3.oas.annotations.tags.Tag;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.http.ResponseEntity;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.PathVariable;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RestController;
import smartask.api.models.Employee;
import smartask.api.services.EmployeeService;

import java.util.List;
import java.util.Optional;

@RestController
@RequestMapping("employee")
@Tag(name = "Employee Management", description = "Endpoints for managing employees")
public class EmployeesController {

    @Autowired
    private EmployeeService service;

    @Operation(
            summary = "Get all employees",
            description = "Retrieves a list of all employees stored in the system."
    )
    @GetMapping("/all")
    public ResponseEntity<List<Employee>> getEmps() {
        return ResponseEntity.ok(service.getAll());
    }

    @Operation(
            summary = "Get an employee by name",
            description = "Searches for an employee by their name. If found, returns employee details; otherwise, returns a 404 Not Found response."
    )
    @GetMapping("/{name}")
    public ResponseEntity<Optional<Employee>> getEmpByName(@PathVariable String name) {
        if (service.findByName(name).isPresent()) {
            return ResponseEntity.ok(service.findByName(name));
        }
        return ResponseEntity.notFound().build();
    }
}
