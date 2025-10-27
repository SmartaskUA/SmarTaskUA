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
    private Double elapsed_time;

    public Schedule(List<List<String>> data, String title, String algorithm) {
        this.data = data;
        this.title = title;
        this.algorithm = algorithm;
    }

    public Schedule(List<List<String>> data, String title, String algorithm, Map<String, Object> metadata, Double elapsed_time) {
        this.data = data;
        this.title = title;
        this.algorithm = algorithm;
        this.metadata = metadata;
        this.elapsed_time = elapsed_time;
    }

    public Schedule(List<List<String>> data, String title, String algorithm, Instant timestamp, Map<String, Object> metadata, Double elapsed_time) {
        this.data = data;
        this.title = title;
        this.algorithm = algorithm;
        this.timestamp = timestamp;
        this.metadata = metadata;
        this.elapsed_time = elapsed_time;
    }
}
