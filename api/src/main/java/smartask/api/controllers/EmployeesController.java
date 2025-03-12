package smartask.api.controllers;

import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.http.ResponseEntity;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RestController;
import smartask.api.models.Employee;
import smartask.api.services.EmployeeService;

import java.util.List;

@RestController
@RequestMapping("employee")
public class EmployeesController {

    @Autowired
    private EmployeeService service;

    @GetMapping("/all")
    public ResponseEntity<List<Employee>> getEmps(){
        return  ResponseEntity.ok(service.getAll());
    }

}
