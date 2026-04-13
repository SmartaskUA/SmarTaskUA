package smartask.api;

import org.springframework.boot.CommandLineRunner;
import org.springframework.boot.SpringApplication;
import org.springframework.boot.autoconfigure.SpringBootApplication;
import org.springframework.context.annotation.Bean;
import org.springframework.core.annotation.Order;
import org.springframework.scheduling.annotation.EnableScheduling;
import smartask.api.bootstrap.ScenarioSeeder;
import smartask.api.services.ProblemService;

@EnableScheduling
@SpringBootApplication
public class ApiApplication {

    public static void main(String[] args) {
        SpringApplication.run(ApiApplication.class, args);
    }

    @Bean
    @Order(1)
    CommandLineRunner initDatabase(ScenarioSeeder scenarioSeeder) {
        return args -> {
            scenarioSeeder.seedIfEnabled();
        };
    }

    @Bean
    @Order(2)
    CommandLineRunner initProblems(ProblemService problemService) {
        return args -> {
            System.out.println("[Startup] Seeding problems from data/problems...");
            problemService.seedDefaultProblems();
            System.out.println("[Startup] Problem seeding complete.");
        };
    }

    @Bean
    @Order(3)
    CommandLineRunner runScenarioHeuristic(ScenarioSeeder scenarioSeeder) {
        return args -> {
            System.out.println("[Startup] Running 3-shift scenario schedules with Heuristic Solver Restarts...");
            scenarioSeeder.runScenarioAlgorithmsIfEnabled("Heuristic Solver");
        };
    }
}
