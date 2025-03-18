package smartask.api.models;

import lombok.Getter;
import lombok.Setter;
import lombok.ToString;
import org.springframework.data.annotation.Id;
import org.springframework.data.mongodb.core.mapping.Document;


import java.time.Instant;
import java.util.List;

@Document(collection = "schedules")
@Getter
@Setter
@ToString
public class Schedule {
    @Id
    private String id;
    private Instant timestamp =  Instant.now();
    private String title;
    private String algorithm;
    private List<List<String>> data;

    public Schedule(List<List<String>> data, String title, String algorithm) {
        this.data = data;
        this.title = title;
        this.algorithm = algorithm;
        System.out.println(toString());
    }

    public String getId() {
        return this.id;
    }

    public void setId(String id) {
        this.id = id;
    }

    public String getTitle() {
        return this.title;
    }

    public void setTitle(String title) {
        this.title = title;
    }


}