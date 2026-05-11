package smartask.api.services;

import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.stereotype.Service;
import smartask.api.models.Employee;
import smartask.api.repositories.*;

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
    @Autowired
    private TaskStatusRepository taskStatusRepository;

    /**
     * Apaga todos os dados de equipes e funcionários e reseta a estrutura inicial.
     */
    public void clearAndResetData() {
        // Apagar tudo
        teamRepository.deleteAll();
        employeesRepository.deleteAll();

        // Criar 24 funcionários: 12 para cada equipa
        teamService.addTeam("Equipa A");
        for (int i = 0; i <= 23; i++) {
            Employee employee = new Employee("Employee " + i);
            employeeService.addEmployee(employee);
        }
        var aEmployees = employeeService.getEmployees().stream()
            .filter(e -> e.getName().startsWith("Employee ") && Integer.parseInt(e.getName().split(" ")[1]) <= 11)
                .map(Employee::getId)
                .toList();
        teamService.addEmployeesToTeam("Equipa A", aEmployees);

        // Os restantes 12 funcionários pertencem à Equipa B
        teamService.addTeam("Equipa B");
        var bEmployees = employeeService.getEmployees().stream()
            .filter(e -> e.getName().startsWith("Employee ") && Integer.parseInt(e.getName().split(" ")[1]) >= 12)
                .map(Employee::getId)
                .toList();
        teamService.addEmployeesToTeam("Equipa B", bEmployees);
    }

    public void deleteAllSchedules() {
        schedulesRepository.deleteAll();
        taskStatusRepository.deleteAll();
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
