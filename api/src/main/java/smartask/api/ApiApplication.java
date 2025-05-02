package smartask.api;

import org.springframework.boot.CommandLineRunner;
import org.springframework.boot.SpringApplication;
import org.springframework.boot.autoconfigure.SpringBootApplication;
import org.springframework.context.annotation.Bean;
import org.springframework.scheduling.annotation.EnableScheduling;
import smartask.api.event.RabbitMqProducer;
import smartask.api.models.Employee;
import smartask.api.models.Team;
import smartask.api.repositories.SchedulesRepository;
import smartask.api.services.EmployeeService;
import smartask.api.services.SchedulesService;
import smartask.api.services.TeamService;

import java.util.List;

@EnableScheduling
@SpringBootApplication
public class ApiApplication {

	public static void main(String[] args) {
		SpringApplication.run(ApiApplication.class, args);
	}

	@Bean
	CommandLineRunner initDatabase(TeamService teamService, EmployeeService employeeService,
								   SchedulesRepository schedulesRepository, SchedulesService schedulesService, RabbitMqProducer producer) {
		return args -> {
			Team teamA = teamService.getTeams().stream().filter(team -> "Equipa A".equals(team.getName())).findFirst().orElse(null);
			if (teamA == null) {
				teamA = new Team("Equipa A");
				teamService.addTeam(teamA);
				for (int i = 1; i <= 9; i++) {
					Employee employee = new Employee("Employee " + i);
					employeeService.addEmployee(employee);
				}
				var aEmployees = employeeService.getEmployees().stream()
						.filter(e -> e.getName().startsWith("Employee ") && Integer.parseInt(e.getName().split(" ")[1]) <= 9)
						.map(Employee::getId)
						.toList();
				teamService.addEmployeesToTeam(teamA.getId(), aEmployees, employeeService);
			}

			Team teamB = teamService.getTeams().stream().filter(team -> "Equipa B".equals(team.getName())).findFirst().orElse(null);
			if (teamB == null) {
				teamB = new Team("Equipa B");
				teamService.addTeam(teamB);
				for (int i = 10; i <= 12; i++) {
					Employee employee = new Employee("Employee " + i);
					employeeService.addEmployee(employee);
				}
				var bEmployees = employeeService.getEmployees().stream()
						.filter(e -> e.getName().startsWith("Employee ") && Integer.parseInt(e.getName().split(" ")[1]) >= 10)
						.map(Employee::getId)
						.toList();
				teamService.addEmployeesToTeam(teamB.getId(), bEmployees, employeeService);
			}

			// Add Employee 5 and 6 to team B (they're already in A)
			var employee5 = employeeService.getEmployees().stream().filter(e -> e.getName().equals("Employee 5")).findFirst().orElse(null);
			var employee6 = employeeService.getEmployees().stream().filter(e -> e.getName().equals("Employee 6")).findFirst().orElse(null);
			if (employee5 != null && employee6 != null) {
				teamService.addEmployeesToTeam(teamB.getId(),
						List.of(employee5.getId(), employee6.getId()),
						employeeService);
			}

			// Add Employee 11 to team A (he's already in B)
			var employee11 = employeeService.getEmployees().stream().filter(e -> e.getName().equals("Employee 11")).findFirst().orElse(null);
			if (employee11 != null) {
				teamService.addEmployeesToTeam(teamA.getId(), List.of(employee11.getId()), employeeService);
			}
		};
	}





}
