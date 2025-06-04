package smartask.api.models.requests;

import lombok.AllArgsConstructor;
import lombok.Data;
import lombok.Setter;

import java.time.LocalDate;
import java.time.LocalDateTime;

@Data
@Setter
public class ScheduleRequest {

    private String taskId;
    private String year;
    private String algorithm;
    private String title;
    private String maxTime;
    private LocalDateTime requestedAt;
    private String vacationTemplate;
    private String minimuns;

    // Construtor explícito
    public ScheduleRequest(String taskId, String year, String algorithm, String title, String maxTime, LocalDateTime requestedAt, String vacationTemplate, String minimuns) {
        this.taskId = taskId;
        this.year =  year;
        this.algorithm = algorithm;
        this.title = title;
        this.maxTime = maxTime;
        this.requestedAt = requestedAt;
        this.vacationTemplate = vacationTemplate;
        this.minimuns = minimuns;
    }

    // Getters and setters
    public String getTaskId() {
        return this.taskId;
    }

    public void setTaskId(String taskId) {
        this.taskId = taskId;
    }

    public String getTitle(){return this.title;}
}
