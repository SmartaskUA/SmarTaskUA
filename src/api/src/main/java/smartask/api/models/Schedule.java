package smartask.api.models;

import lombok.Getter;
import lombok.NoArgsConstructor;
import lombok.Setter;
import lombok.ToString;
import org.springframework.data.annotation.Id;
import org.springframework.data.mongodb.core.mapping.Document;


import java.time.Instant;
import java.util.List;

import java.util.Map;

@Document(collection = "schedules")
@Getter
@Setter
@ToString
@NoArgsConstructor
public class Schedule {


    @Id
    private String id;
    private Instant timestamp = Instant.now();
    private String title;
    private String algorithm;
    private List<List<String>> data;
    private Map<String, Object> metadata;


    public Schedule(List<List<String>> data, String title, String algorithm) {
        this.data = data;
        this.title = title;
        this.algorithm = algorithm;
    }
}
