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
import smartask.api.services.SchedulingAlgorithmRegistry;

import java.time.LocalDateTime;
import java.util.HashMap;
import java.util.Map;
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

    @Autowired
    private SchedulingAlgorithmRegistry schedulingAlgorithmRegistry;


    public String requestScheduleMessage(ScheduleRequest schedule) {
        String res;
        SchedulingAlgorithmRegistry.AlgorithmSpec algorithmSpec = schedulingAlgorithmRegistry.find(schedule.getAlgorithm())
                .orElse(null);
        if (algorithmSpec == null) {
            return "Unsupported algorithm";
        }

        boolean usesProblemBundle =
                algorithmSpec.getInputKind() == SchedulingAlgorithmRegistry.InputKind.PROBLEM_BUNDLE;

        Optional<VacationTemplate> vactemp = Optional.empty();
        Optional<ReferenceTemplate> mins = Optional.empty();
        if (!usesProblemBundle) {
            vactemp = vacationTemplateRepository.findByName(schedule.getVacationTemplate());
            if (vactemp.isEmpty()) {
                return "Vacation template not found";
            }

            mins = referenceTemplateRepository.findByName(schedule.getMinimuns());
            if (mins.isEmpty()) {
                return "Minimums template not found";
            }
        } else if (schedule.getProblemPath() == null || schedule.getProblemPath().isBlank()) {
            return "Problem path is required for problem-bundle algorithms";
        }

        try {
            String taskId = schedule.getTaskId();
            if (taskId == null || taskId.isBlank()) {
                taskId = UUID.randomUUID().toString();
                schedule.setTaskId(taskId);
            }

            TaskStatus taskStatus = new TaskStatus(
                taskId,
                "PENDING",
                LocalDateTime.now(),
                LocalDateTime.now(),
                schedule
            );

            if (!"startconn".equals(schedule.getTitle())) {
                taskStatusRepository.save(taskStatus);
            } else {
                System.out.println("\n[Debug] Sending mock connection test to queue...");
            }

            // ✅ Prepare message payload with all data
            Map<String, Object> payload = new HashMap<>();
            payload.put("taskId", taskId);
            payload.put("title", schedule.getTitle());
            payload.put("algorithm", schedule.getAlgorithm());
            payload.put("year", schedule.getYear());
            payload.put("maxTime", schedule.getMaxTime());
            payload.put("shifts", schedule.getShifts());
            payload.put("groupName", schedule.getGroupName());
            if (!usesProblemBundle) {
                payload.put("vacationTemplate", vactemp.get().getName());
                payload.put("minimuns", mins.get().getName());
            } else {
                payload.put("problemPath", schedule.getProblemPath());
            }
            if (schedule.getEmployees() != null) {
                payload.put("employees", schedule.getEmployees());
            }

            // Add constraints if provided; otherwise send null for rules
            if (schedule.getConstraints() != null) {
                payload.put("rules", schedule.getConstraints());
            } else {
                payload.put("rules", null);
            }

            // Serialize to JSON for logging/debug
            String jsonMessage = objectMapper.writeValueAsString(payload);
            System.out.println("📤 Sent task request payload:\n" + jsonMessage);

            // Send message to RabbitMQ
            rabbitTemplate.convertAndSend(EXCHANGE_NAME, ROUTING_KEY, payload);

            return res = "Sent task request";

        } catch (JsonProcessingException e) {
            System.err.println("Error converting payload to JSON: " + e.getMessage());
            return res = "Error converting ScheduleRequest to JSON: " + e.getMessage();
        } catch (Exception e) {
            System.err.println("Unexpected error: " + e.getMessage());
            e.printStackTrace();
            return res = "Unexpected error: " + e.getMessage();
        }
    }



    public void sendMessage(String message) {
        rabbitTemplate.convertAndSend(EXCHANGE_NAME, ROUTING_KEY, message);
        System.out.println("Sent message: " + message);
    }
}
