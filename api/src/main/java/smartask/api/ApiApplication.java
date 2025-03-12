package smartask.api;

import org.springframework.boot.CommandLineRunner;
import org.springframework.boot.SpringApplication;
import org.springframework.boot.autoconfigure.SpringBootApplication;
import org.springframework.context.annotation.Bean;
import org.springframework.data.mongodb.core.MongoTemplate;

@SpringBootApplication
public class ApiApplication {

	public static void main(String[] args) {
		SpringApplication.run(ApiApplication.class, args);
	}
	//*
	// @Bean
	//	CommandLineRunner clearDatabase(MongoTemplate mongoTemplate) {
	//		return args -> {
	//			mongoTemplate.getDb().listCollectionNames().forEach(collectionName -> {
	//				mongoTemplate.dropCollection(collectionName);
	//				System.out.println("Dropped collection: " + collectionName);
	//			});
	//			System.out.println("All collections have been deleted at startup.");
	//		};
	//	}
	// *


}
