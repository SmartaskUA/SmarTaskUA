package smartask.api.services;

import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.data.mongodb.core.MongoTemplate;
import org.springframework.stereotype.Service;

@Service
public class SequenceGeneratorService {

    @Autowired
    private MongoTemplate mongoTemplate;

    public Long generateSequence(String collectionName) {
        return mongoTemplate.getCollection(collectionName).countDocuments() + 1;
    }
}