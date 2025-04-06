package smartask.api.models;

import jakarta.validation.constraints.NotBlank;
import org.springframework.data.annotation.Id;

import java.util.List;
import java.util.Map;

public class VacationTemplate {

    @Id
    private String id;

    @NotBlank
    private String name;

    private Map<String, List<String>> vacations;
}
