package smartask.api.models.requests;

import com.fasterxml.jackson.annotation.JsonFormat;
import lombok.AllArgsConstructor;
import lombok.Data;
import lombok.Setter;

import java.time.Duration;
import java.time.LocalDate;
import java.time.LocalDateTime;

@AllArgsConstructor
@Data
@Setter
public class ScheduleRequest
{
    private LocalDate init, end; // Should limit to a year

    private String algorithm;

    private String title;

    private String maxTime; // Expected format : HH:MM:SS

    private LocalDateTime requestedAt;

}
