package smartask.api;

import org.springframework.boot.CommandLineRunner;
import org.springframework.boot.SpringApplication;
import org.springframework.boot.autoconfigure.SpringBootApplication;
import org.springframework.context.annotation.Bean;
import org.springframework.core.io.ClassPathResource;
import org.springframework.scheduling.annotation.EnableScheduling;
import com.fasterxml.jackson.core.type.TypeReference;
import com.fasterxml.jackson.databind.ObjectMapper;

import smartask.api.event.RabbitMqProducer;
import smartask.api.models.Employee;
import smartask.api.models.Rule;
import smartask.api.models.RuleSet;
import smartask.api.models.Team;
import smartask.api.repositories.SchedulesRepository;
import smartask.api.services.EmployeeService;
import smartask.api.services.RuleSetService;
import smartask.api.services.SchedulesService;
import smartask.api.services.TeamService;

import java.io.InputStream;
import java.time.Instant;
import java.util.List;
import java.util.stream.Stream;

@EnableScheduling
@SpringBootApplication
public class ApiApplication {

	public static void main(String[] args) {
		SpringApplication.run(ApiApplication.class, args);
	}

	@Bean
	CommandLineRunner initDatabase(TeamService teamService, EmployeeService employeeService,
								   SchedulesRepository schedulesRepository, SchedulesService schedulesService, RabbitMqProducer producer, RuleSetService ruleSetService) {
		return args -> {
			ObjectMapper mapper = new ObjectMapper();

			// Load the JSON file from resources
			InputStream inputStream = new ClassPathResource("rules.json").getInputStream();

			if (inputStream != null) {
				// Deserialize JSON directly into a RuleSet
				RuleSet defaultSet = mapper.readValue(inputStream, RuleSet.class);

				// If your JSON doesn't have name/description fields, set them manually
				if (defaultSet.getName() == null || defaultSet.getName().isBlank()) {
					defaultSet.setName("default");
				}
				if (defaultSet.getDescription() == null || defaultSet.getDescription().isBlank()) {
					defaultSet.setDescription("Default rule set loaded from JSON");
				}

				// Save to DB
				ruleSetService.saveRuleSet(defaultSet);

				System.out.println("Default rule set loaded successfully!");
			} else {
				System.err.println("Could not find rules.json in resources folder!");
			}
			// ---- Equipa A ----------------------------------------------------
			Team teamA = teamService.getTeams().stream()
					.filter(team -> "Equipa A".equals(team.getName()))
					.findFirst().orElse(null);
			if (teamA == null) {
				teamService.addTeam("Equipa A");

				for (int i = 1; i <= 9; i++) {
					String name = "Employee " + i;
					boolean exists = employeeService.getEmployees().stream()
							.anyMatch(e -> name.equals(e.getName()));
					if (!exists) {
						employeeService.addEmployee(new Employee(name));
					}
				}

				var aEmployees = employeeService.getEmployees().stream()
						.filter(e -> e.getName().startsWith("Employee "))
						.filter(e -> {
							try {
								int n = Integer.parseInt(e.getName().split(" ")[1]);
								return n >= 1 && n <= 9;
							} catch (NumberFormatException ex) {
								return false;
							}
						})
						.map(Employee::getId)
						.toList();

				teamService.addEmployeesToTeam("Equipa A", aEmployees);
			}

			// ---- Equipa B ----------------------------------------------------
			Team teamB = teamService.getTeams().stream()
					.filter(team -> "Equipa B".equals(team.getName()))
					.findFirst().orElse(null);
			if (teamB == null) {
				teamService.addTeam("Equipa B");

				for (int i = 10; i <= 12; i++) {
					String name = "Employee " + i;
					boolean exists = employeeService.getEmployees().stream()
							.anyMatch(e -> name.equals(e.getName()));
					if (!exists) {
						employeeService.addEmployee(new Employee(name));
					}
				}

				var bEmployees = employeeService.getEmployees().stream()
						.filter(e -> e.getName().startsWith("Employee "))
						.filter(e -> {
							try {
								int n = Integer.parseInt(e.getName().split(" ")[1]);
								return n >= 10;
							} catch (NumberFormatException ex) {
								return false;
							}
						})
						.map(Employee::getId)
						.toList();

				teamService.addEmployeesToTeam("Equipa B", bEmployees);
			}

			// Cross-memberships: add Employee 5 & 6 to B; Employee 11 to A
			var employee5 = employeeService.getEmployees().stream()
					.filter(e -> e.getName().equals("Employee 5")).findFirst().orElse(null);
			var employee6 = employeeService.getEmployees().stream()
					.filter(e -> e.getName().equals("Employee 6")).findFirst().orElse(null);
			if (employee5 != null && employee6 != null) {
				teamService.addEmployeesToTeam("Equipa B", List.of(employee5.getId(), employee6.getId()));
			}
			var employee11 = employeeService.getEmployees().stream()
					.filter(e -> e.getName().equals("Employee 11")).findFirst().orElse(null);
			if (employee11 != null) {
				teamService.addEmployeesToTeam("Equipa A", List.of(employee11.getId()));
			}

			// ---- Equipa C (with extra employees) -----------------------------
			Team teamC = teamService.getTeams().stream()
					.filter(team -> "Equipa C".equals(team.getName()))
					.findFirst()
					.orElse(null);

			if (teamC == null) {
				teamService.addTeam("Equipa C");

				// Create extra employees 13..20 if they don't exist yet
				for (int i = 13; i <= 17; i++) {
					String name = "Employee " + i;
					boolean exists = employeeService.getEmployees().stream()
							.anyMatch(e -> name.equals(e.getName()));
					if (!exists) {
						employeeService.addEmployee(new Employee(name));
					}
				}

				// New employees for C: 13..20
				var newCEmployees = employeeService.getEmployees().stream()
						.filter(e -> e.getName().startsWith("Employee "))
						.filter(e -> {
							try {
								int n = Integer.parseInt(e.getName().split(" ")[1]);
								return n >= 13 && n <= 20;
							} catch (NumberFormatException ex) {
								return false;
							}
						})
						.map(Employee::getId)
						.toList();

				// Reuse some existing employees too (example: 3, 6, 11)
				var reusedEmployees = employeeService.getEmployees().stream()
						.filter(e -> List.of("Employee 3", "Employee 6", "Employee 11").contains(e.getName()))
						.map(Employee::getId)
						.toList();

				// Combine and add to Equipa C
				var cEmployees = Stream.concat(newCEmployees.stream(), reusedEmployees.stream()).toList();
				teamService.addEmployeesToTeam("Equipa C", cEmployees);
			}
		};
	}
}
