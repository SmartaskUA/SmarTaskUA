package smartask.api.controllers;

import io.swagger.v3.oas.annotations.Operation;
import io.swagger.v3.oas.annotations.tags.Tag;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.http.ResponseEntity;
import org.springframework.web.bind.annotation.*;
import smartask.api.models.Employee;
import smartask.api.models.requests.RestrictionRequest;
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

    @Operation(
            summary = "Add new restriction to an employee by their name",
            description = "Searches for an employee by their name. If found, add new restriction, e.g. search for [Joao] and add restriction [Fer] for the date [11/05]"
    )
    @PostMapping("/restriction/{name}")
    public ResponseEntity<String> addRestriction(@RequestBody RestrictionRequest restrictionRequest,
                                                 @PathVariable String name) {
        System.out.println(restrictionRequest+" for "+name);
        service.addRestrictionToEmployee(name, restrictionRequest.getRestrictionType(), restrictionRequest.getDate());
        return ResponseEntity.ok("Restriction added successfully");
    }

    @Operation(
            summary = "Update new restriction to an employee by their name",
            description = "Searches for an employee by their name. If found, change the value of the restriction, e.g. search for [Joao] and change restriction [Fer] for the date [11/05]"
    )
    @PutMapping("/restriction/{name}")
    public ResponseEntity<String> updateRestriction(@RequestBody RestrictionRequest restrictionRequest,
                                                    @PathVariable String name) {
        System.out.println(restrictionRequest+" for "+name);
        // Process the received restrictionType and date
        return ResponseEntity.ok("Restriction update successfully");
    }

    @Operation(
            summary = "Delete new restriction to an employee by their name",
            description = "Searches for an employee by their name. If found, delete value of the restriction, e.g. search for [Joao] and  delete the date [11/05] for the restriction [Fer]"
    )
    @DeleteMapping("/restriction/{name}")
    public ResponseEntity<String> deleteRestriction(@RequestBody RestrictionRequest restrictionRequest,
                                                    @PathVariable String name) {
        System.out.println(restrictionRequest+" for "+name);
        service.removeRestrictionFromEmployee(name, restrictionRequest.getRestrictionType(), restrictionRequest.getDate());
        return ResponseEntity.ok("Restriction deleted successfully");
    }
}
