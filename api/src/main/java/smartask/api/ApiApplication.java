package smartask.api;

import org.springframework.boot.CommandLineRunner;
import org.springframework.boot.SpringApplication;
import org.springframework.boot.autoconfigure.SpringBootApplication;
import org.springframework.context.annotation.Bean;
import smartask.api.models.Schedule;
import smartask.api.repositories.SchedulesRepository;
import smartask.api.services.SchedulesService;

@SpringBootApplication
public class ApiApplication {

	public static void main(String[] args) {
		SpringApplication.run(ApiApplication.class, args);
	}

	@Bean
	CommandLineRunner initDatabase(SchedulesRepository schedulesRepository, SchedulesService schedulesService) {
		return args -> {
			if (!schedulesRepository.existsByTitle("Sample")) {
				schedulesService.readex1();
				System.out.println("Sample schedule created at startup.");
			} else {
				System.out.println("Sample schedule already exists.");
			}
		};
	}
}
