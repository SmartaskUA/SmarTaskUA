package smartask.api.services;

import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.data.mongodb.core.MongoTemplate;
import org.springframework.data.mongodb.core.query.Query;
import org.springframework.data.mongodb.core.query.Update;
import org.springframework.stereotype.Service;
import smartask.api.models.Sequence;

import static org.springframework.data.mongodb.core.query.Criteria.where;

@Service
public class SequenceGeneratorService {

    @Autowired
    private MongoTemplate mongoTemplate;

    public Long generateSequence(String collectionName) {
        // Ensure the sequence document exists or create it
        Sequence sequence = mongoTemplate.findAndModify(
                Query.query(where("_id").is(collectionName)),
                new Update().inc("seq", 1),  // Increment the seq field by 1
                Sequence.class
        );

        if (sequence == null) {
            // If sequence is null, it means the collection was not found, so create a new one
            sequence = new Sequence();
            sequence.setId(collectionName);
            sequence.setSeq(1L); // Start with 1 as the first ID
            mongoTemplate.save(sequence);
        }

        return sequence.getSeq(); // Return the incremented sequence value
    }
}
