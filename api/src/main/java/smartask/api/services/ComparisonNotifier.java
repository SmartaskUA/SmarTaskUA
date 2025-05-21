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
import java.util.stream.Collectors;

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

        if (!results.isEmpty()) {
        System.out.println("\n Comparison results : "+results);


            // Pode enviar os documentos inteiros, ou apenas os resultados
            List<Object> comparisonResults = results.stream()
                    .map(doc -> {
                        Document response = new Document();
                        response.put("requestId", doc.getString("requestId"));
                        response.put("result", doc.get("result"));
                        return response;
                    })
                    .collect(Collectors.toList());

            messagingTemplate.convertAndSend("/topic/comparison/all", comparisonResults);

            // Remove todos os documentos enviados
            mongoTemplate.remove(query, "comparisons");
        }
    }
}
