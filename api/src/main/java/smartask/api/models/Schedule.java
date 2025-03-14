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
    private Long id;
    private Instant timestamp =  Instant.now();
    private String title;
    private List<List<String>> data;

    public Schedule(List<List<String>> data, String title) {
        this.data = data;
        this.title = title;
        System.out.println(toString());
    }

    public Long getId() {
        return this.id;
    }

    public void setId(Long id) {
        this.id = id;
    }

    public String getTitle() {
        return this.title;
    }

    public void setTitle(String title) {
        this.title = title;
    }


}