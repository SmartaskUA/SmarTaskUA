package smartask.api.entity;

import lombok.Getter;
import lombok.Setter;
import org.springframework.data.annotation.Id;
import org.springframework.data.mongodb.core.mapping.Document;

@Document(collection = "schedules")
@Getter
@Setter
public class Schedule {
    @Id
    private String id;
    private String name;

}
