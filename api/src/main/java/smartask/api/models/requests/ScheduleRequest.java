package smartask.api.models.requests;

import lombok.AllArgsConstructor;
import lombok.Data;
import lombok.Setter;

import java.time.Duration;
import java.time.LocalDate;

@AllArgsConstructor
@Data
@Setter
public class ScheduleRequest
{
    private LocalDate init, end;

    private String algorithm;

    private String title;

    private Duration maxTime;
}
