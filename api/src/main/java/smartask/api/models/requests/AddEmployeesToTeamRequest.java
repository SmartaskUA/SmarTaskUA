package smartask.api.models.requests;


import lombok.Data;

import java.util.List;
@Data
public class AddEmployeesToTeamRequest {
    private List<String> employeeIds;
}