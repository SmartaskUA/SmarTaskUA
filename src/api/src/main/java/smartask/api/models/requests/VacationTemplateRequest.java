package smartask.api.models.requests;

import lombok.Data;

import java.util.List;
import java.util.Map;

@Data
public class VacationTemplateRequest {
    private String name;
    private Map<String, List<String>> vacations;
}
