package smartask.api.services;

import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.messaging.simp.SimpMessagingTemplate;
import org.springframework.stereotype.Component;
import org.springframework.scheduling.annotation.Scheduled;
import org.springframework.data.mongodb.core.MongoTemplate;
import org.springframework.data.mongodb.core.query.Query;
import org.springframework.data.mongodb.core.query.Criteria;
import org.bson.Document;

import java.util.List;

@Component
public class ComparisonNotifier {

    @Autowired
    private SimpMessagingTemplate messagingTemplate;

    @Autowired
    private MongoTemplate mongoTemplate;

    @Scheduled(fixedDelay = 2000)
    public void notifyComparisonResults() {
        Query query = new Query(Criteria.where("status").is("done"));
        List<Document> results = mongoTemplate.find(query, Document.class, "comparisons");

        for (Document doc : results) {
            String requestId = doc.getString("requestId");
            Object result = doc.get("result");

            messagingTemplate.convertAndSend("/topic/comparison/" + requestId, result);

            mongoTemplate.remove(doc, "comparisons");
        }
    }
}
