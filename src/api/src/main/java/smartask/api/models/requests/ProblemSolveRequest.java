package smartask.api.models.requests;

import lombok.Data;

@Data
public class ProblemSolveRequest {
    private String algorithm;
    private String title;
    private String maxTime;
    private String year;
    private Integer shifts;
    private Integer hours;
}
