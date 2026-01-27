package smartask.api;

import org.springframework.boot.CommandLineRunner;
import org.springframework.boot.SpringApplication;
import org.springframework.boot.autoconfigure.SpringBootApplication;
import org.springframework.context.annotation.Bean;
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
    CommandLineRunner initDatabase(ScenarioSeeder scenarioSeeder) {
        return args -> {
            scenarioSeeder.seedIfEnabled();
        };
    }

    @Bean
    CommandLineRunner initProblems(ProblemService problemService) {
        return args -> {
            System.out.println("[Startup] Seeding problems from data/problems...");
            problemService.seedDefaultProblems();
            System.out.println("[Startup] Problem seeding complete.");
        };
    }
}
