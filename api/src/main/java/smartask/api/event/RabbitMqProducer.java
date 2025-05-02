package smartask.api.event;
import com.fasterxml.jackson.core.JsonProcessingException;
import org.springframework.amqp.rabbit.core.RabbitTemplate;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.stereotype.Service;
import smartask.api.models.ReferenceTemplate;
import smartask.api.models.TaskStatus;
import smartask.api.models.VacationTemplate;
import smartask.api.models.requests.ScheduleRequest;
import com.fasterxml.jackson.databind.ObjectMapper;
import smartask.api.repositories.ReferenceTemplateRepository;
import smartask.api.repositories.TaskStatusRepository;
import smartask.api.repositories.VacationTemplateRepository;

import java.time.LocalDateTime;
import java.util.Optional;
import java.util.UUID;

@Service
public class RabbitMqProducer {

    private static final String EXCHANGE_NAME = "task-exchange";
    private static final String ROUTING_KEY = "task-routing-key";

    @Autowired
    private RabbitTemplate rabbitTemplate;

    @Autowired
    private ObjectMapper objectMapper;

    @Autowired
    private TaskStatusRepository taskStatusRepository;

    @Autowired
    private VacationTemplateRepository vacationTemplateRepository;

    @Autowired
    private ReferenceTemplateRepository referenceTemplateRepository;

    public String requestScheduleMessage(ScheduleRequest schedule) {
        //Verify the existence of the vacationTemplate
            String res ;
            final Optional<VacationTemplate> vactemp = vacationTemplateRepository.findByName(schedule.getVacationTemplate());
            if (vactemp.isEmpty()){
                return res= "Vacation template not found";
            }

        final Optional<ReferenceTemplate> mins = referenceTemplateRepository.findByName(schedule.getMinimuns());
        if (mins.isEmpty()){
            return res= "minimuns template not found";
        }
        try {

            // Generate a unique task ID
            String taskId = UUID.randomUUID().toString();
            schedule.setTaskId(taskId);

            // Save task status with the original request
            TaskStatus taskStatus = new TaskStatus(taskId, "PENDING", LocalDateTime.now(), LocalDateTime.now(), schedule);

            if (!schedule.getTitle().equals("startconn")) {
                taskStatusRepository.save(taskStatus);
            }
            else{
                System.out.println("\nSending mock connection to qeueu");
            }

            // Convert request to JSON
            String jsonMessage = objectMapper.writeValueAsString(schedule);

            // Send message to RabbitMQ
            rabbitTemplate.convertAndSend(EXCHANGE_NAME, ROUTING_KEY, jsonMessage);
            System.out.println("Sent task request: " + jsonMessage);
            return res ="Sent task request";

        } catch (JsonProcessingException e) {
            System.err.println("Error converting ScheduleRequest to JSON: " + e.getMessage());
            return res = "Error converting ScheduleRequest to JSON: " + e.getMessage();
        }
    }



    public void sendMessage(String message) {
        rabbitTemplate.convertAndSend(EXCHANGE_NAME, ROUTING_KEY, message);
        System.out.println("Sent message: " + message);
    }
}
