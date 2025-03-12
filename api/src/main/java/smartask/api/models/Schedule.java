package smartask.api.models;

import lombok.Getter;
import lombok.Setter;
import org.springframework.data.annotation.Id;
import org.springframework.data.mongodb.core.mapping.Document;

import org.bson.types.ObjectId;
import org.springframework.data.annotation.Id;
import org.springframework.data.mongodb.core.mapping.Document;

import java.time.Instant;
import java.util.List;

@Document(collection = "schedules")
@Getter
@Setter
public class Schedule {
    @Id
    private ObjectId id;
    private Instant timestamp;
    private List<List<String>> data;

    public Schedule(List<List<String>> data) {
        this.id = new ObjectId();
        this.timestamp = Instant.now();
        this.data = data;
    }

}