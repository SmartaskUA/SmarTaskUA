package smartask.api.controllers;

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
public class EmployeesController {

    @Autowired
    private EmployeeService service;

    @GetMapping("/all")
    public ResponseEntity<List<Employee>> getEmps(){
        return  ResponseEntity.ok(service.getAll());
    }

    @GetMapping("/{name}")
    public  ResponseEntity<Optional<Employee>> getEmpByName(@PathVariable String name){
        if (service.findByName(name).isPresent()){
            return ResponseEntity.ok(service.findByName(name));
        }
        return ResponseEntity.notFound().build();
    }


}
