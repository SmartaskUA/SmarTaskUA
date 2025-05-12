package smartask.api.services;

import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.stereotype.Service;
import smartask.api.models.Employee;
import smartask.api.repositories.*;
import smartask.api.services.EmployeeService;
import smartask.api.services.TeamService;

import java.util.List;

@Service
public class ClearAndResetService {
    @Autowired
    private  TeamRepository teamRepository;
    @Autowired
    private  EmployeesRepository employeesRepository;
    @Autowired
    private  TeamService teamService;
    @Autowired
    private  EmployeeService employeeService;
    @Autowired
    private SchedulesRepository schedulesRepository;
    @Autowired
    private ReferenceTemplateRepository referenceTemplateRepository;
    @Autowired
    private VacationTemplateRepository vacationTemplateRepository;

    /**
     * Apaga todos os dados de equipes e funcionários e reseta a estrutura inicial.
     */
    public void clearAndResetData() {
        // Apagar tudo
        teamRepository.deleteAll();
        employeesRepository.deleteAll();

        // Criar Equipa A com 9 funcionários
        teamService.addTeam("Equipa A");
        for (int i = 1; i <= 9; i++) {
            Employee employee = new Employee("Employee " + i);
            employeeService.addEmployee(employee);
        }
        var aEmployees = employeeService.getEmployees().stream()
                .filter(e -> e.getName().startsWith("Employee ") && Integer.parseInt(e.getName().split(" ")[1]) <= 9)
                .map(Employee::getId)
                .toList();
        teamService.addEmployeesToTeam("Equipa A", aEmployees);

        // Criar Equipa B com 3 funcionários
        teamService.addTeam("Equipa B");
        for (int i = 10; i <= 12; i++) {
            Employee employee = new Employee("Employee " + i);
            employeeService.addEmployee(employee);
        }
        var bEmployees = employeeService.getEmployees().stream()
                .filter(e -> e.getName().startsWith("Employee ") && Integer.parseInt(e.getName().split(" ")[1]) >= 10)
                .map(Employee::getId)
                .toList();
        teamService.addEmployeesToTeam("Equipa B", bEmployees);

        // Adicionar Employee 5 e 6 à Equipa B (também estão na A)
        employeeService.getEmployees().stream()
                .filter(e -> e.getName().equals("Employee 5") || e.getName().equals("Employee 6"))
                .map(Employee::getId)
                .forEach(id -> teamService.addEmployeesToTeam("Equipa B", List.of(id)));

        // Adicionar Employee 11 à Equipa A (também está na B)
        employeeService.getEmployees().stream()
                .filter(e -> e.getName().equals("Employee 11"))
                .map(Employee::getId)
                .forEach(id -> teamService.addEmployeesToTeam("Equipa A", List.of(id)));
    }

    public void deleteAllSchedules() {
        schedulesRepository.deleteAll();
    }

    public void deleteAllReferenceTemplates() {
        referenceTemplateRepository.deleteAll();
    }



    /**
     * Apaga todos os documentos da coleção "vacations".
     */
    public void deleteAllVacationTemplates() {
        vacationTemplateRepository.deleteAll();
    }



}
