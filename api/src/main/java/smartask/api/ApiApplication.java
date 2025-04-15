package smartask.api;

import org.springframework.boot.CommandLineRunner;
import org.springframework.boot.SpringApplication;
import org.springframework.boot.autoconfigure.SpringBootApplication;
import org.springframework.context.annotation.Bean;
import smartask.api.event.RabbitMqProducer;
import smartask.api.models.Employee;
import smartask.api.models.Team;
import smartask.api.models.requests.ScheduleRequest;
import smartask.api.repositories.EmployeesRepository;
import smartask.api.repositories.SchedulesRepository;
import smartask.api.repositories.TeamRepository;
import smartask.api.services.EmployeeService;
import smartask.api.services.SchedulesService;
import smartask.api.services.TeamService;

import java.time.LocalDate;
import java.time.LocalDateTime;

@SpringBootApplication
public class ApiApplication {

	public static void main(String[] args) {
		SpringApplication.run(ApiApplication.class, args);
	}

	@Bean
	CommandLineRunner initDatabase(TeamService teamService, EmployeeService employeeService,
								   SchedulesRepository schedulesRepository, SchedulesService schedulesService, RabbitMqProducer producer) {
		return args -> {
			// Check if Team A exists, if not create and save it

			if (teamService.getTeams().isEmpty() || teamService.getTeams().stream().noneMatch(team -> "A".equals(team.getName()))) {
				Team teamA = new Team("A");
				teamService.addTeam(teamA);

				// Create and add 9 employees to Team A
				for (int i = 1; i <= 9; i++) {
					Employee employee = new Employee("Employee " + i, teamA);
					employeeService.addEmployee(employee);
				}
			}

			// Check if Team B exists, if not create and save it
			if (teamService.getTeams().isEmpty() || teamService.getTeams().stream().noneMatch(team -> "B".equals(team.getName()))) {
				Team teamB = new Team("B");
				teamService.addTeam(teamB);

				// Create and add 3 employees to Team B
				for (int i = 10; i <= 12; i++) {
					Employee employee = new Employee("Employee " + i, teamB);
					employeeService.addEmployee(employee);
				}
			}

			if (!schedulesRepository.existsByTitle("Sample")) {
				schedulesService.readex1();
				System.out.println("Sample schedule created at startup.");
			} else {
				System.out.println("Sample schedule already exists.");
			}
/*
			ScheduleRequest mockRequest = new ScheduleRequest(
					"string",                               // taskId
					LocalDate.parse("2025-03-30"),           // init
					LocalDate.parse("2025-03-30"),           // end
					"string",                               // algorithm
					"startconn",                                     // title
					"string",                               // maxTime
					LocalDateTime.parse("2025-03-30T15:57:23.796")  // requestedAt
			);
			producer.requestScheduleMessage(mockRequest);

			 */
		};
	}
}
