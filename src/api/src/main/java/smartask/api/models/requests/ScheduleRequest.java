package smartask.api.models.requests;

import lombok.Data;
import lombok.NoArgsConstructor;
import lombok.Setter;

import java.time.LocalDateTime;
import java.util.List;
import java.util.Map;

@Data
@Setter
@NoArgsConstructor
public class ScheduleRequest {

    private String taskId;
    private String year;
    private String algorithm;
    private String title;
    private String maxTime;
    private LocalDateTime requestedAt;
    private String vacationTemplate;
    private String minimuns;
    private Integer shifts;  
    private Map<String, Object> constraints;
    private Integer hours;
    private String groupName;
    private List<Map<String, Object>> employees;
    // Construtor explícito
    public ScheduleRequest(String taskId, String year, String algorithm, String title, String maxTime, LocalDateTime requestedAt, String vacationTemplate, String minimuns, Integer shifts, Integer hours, String groupName) {
        this.taskId = taskId;
        this.year =  year;
        this.algorithm = algorithm;
        this.title = title;
        this.maxTime = maxTime;
        this.requestedAt = requestedAt;
        this.vacationTemplate = vacationTemplate;
        this.minimuns = minimuns;
        this.shifts = shifts;
        this.groupName = groupName;
        this.hours = hours;
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
