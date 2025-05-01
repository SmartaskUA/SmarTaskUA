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
			Team teamA = teamService.getTeams().stream().filter(team -> "A".equals(team.getName())).findFirst().orElse(null);
			if (teamA == null) {
				teamA = new Team("A");
				teamService.addTeam(teamA);
				for (int i = 1; i <= 9; i++) {
					Employee employee = new Employee("Employee " + i); // assign team after saving
					employeeService.addEmployee(employee);
				}
				// Assign to team A
				var aEmployees = employeeService.getEmployees().stream()
						.filter(e -> e.getName().startsWith("Employee ") && Integer.parseInt(e.getName().split(" ")[1]) <= 9)
						.map(Employee::getId)
						.toList();
				teamService.addEmployeesToTeam(teamA.getId(), aEmployees, employeeService);
			}

			Team teamB = teamService.getTeams().stream().filter(team -> "B".equals(team.getName())).findFirst().orElse(null);
			if (teamB == null) {
				teamB = new Team("B");
				teamService.addTeam(teamB);
				for (int i = 10; i <= 12; i++) {
					Employee employee = new Employee("Employee " + i); // assign team after saving
					employeeService.addEmployee(employee);
				}
				// Assign to team B
				var bEmployees = employeeService.getEmployees().stream()
						.filter(e -> e.getName().startsWith("Employee ") && Integer.parseInt(e.getName().split(" ")[1]) >= 10)
						.map(Employee::getId)
						.toList();
				teamService.addEmployeesToTeam(teamB.getId(), bEmployees, employeeService);
			}
		};
	}




}
