package smartask.api.event;
import com.fasterxml.jackson.core.JsonProcessingException;
import org.springframework.amqp.rabbit.core.RabbitTemplate;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.stereotype.Service;
import smartask.api.models.requests.ScheduleRequest;
import com.fasterxml.jackson.databind.ObjectMapper;

@Service
public class RabbitMqProducer {

    private static final String EXCHANGE_NAME = "task-exchange";
    private static final String ROUTING_KEY = "task-routing-key";

    @Autowired
    private RabbitTemplate rabbitTemplate;

    @Autowired
    private ObjectMapper objectMapper;

    public void requestScheduleMessage(ScheduleRequest schedule) {
        try {
            String jsonMessage = objectMapper.writeValueAsString(schedule);
            rabbitTemplate.convertAndSend(EXCHANGE_NAME, ROUTING_KEY, jsonMessage);
            System.out.println("Sent message: " + jsonMessage);
        } catch (JsonProcessingException e) {
            System.err.println("Error converting ScheduleRequest to JSON: " + e.getMessage());
        }
    }

    public void sendMessage(String message) {
        rabbitTemplate.convertAndSend(EXCHANGE_NAME, ROUTING_KEY, message);
        System.out.println("Sent message: " + message);
    }
}
