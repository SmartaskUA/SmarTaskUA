package smartask.api.models;

import jakarta.validation.constraints.NotBlank;
import lombok.AllArgsConstructor;
import lombok.Data;
import lombok.NoArgsConstructor;
import org.springframework.data.annotation.Id;

import java.util.Map;

@Data
@NoArgsConstructor
@AllArgsConstructor
public class Rule {
    
    private String id;

    @NotBlank
    private String type; // e.g. "max_consecutive_days"

    /**
     * "hard" or "soft" or boolean flag; kept here simple
     */
    private String kind = "hard";

    /**
     * scope string (per-employee-day, per-day-shift-team, ...)
     */
    private String scope;

    private String description;

    private Map<String, Object> params;

}
