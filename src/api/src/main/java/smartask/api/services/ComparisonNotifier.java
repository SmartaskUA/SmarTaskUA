package smartask.api.services;

import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.messaging.simp.SimpMessagingTemplate;
import org.springframework.stereotype.Component;
import org.springframework.scheduling.annotation.Scheduled;
import org.springframework.data.mongodb.core.MongoTemplate;
import org.springframework.data.mongodb.core.query.Query;
import org.springframework.data.mongodb.core.query.Criteria;
import org.bson.Document;
import java.util.ArrayList;
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

        // ✅ Ler de ambas as coleções
        List<Document> verificationDocs = mongoTemplate.find(query, Document.class, "verifications");
        List<Document> comparisonDocs = mongoTemplate.find(query, Document.class, "comparisons");

        List<Document> results = new ArrayList<>();
        results.addAll(verificationDocs);
        results.addAll(comparisonDocs);

        if (!results.isEmpty()) {
            System.out.println("📊 Sending KPI results to frontend: " + results.size());

            // Extrair só o necessário
            List<Object> payload = results.stream()
                    .map(doc -> {
                        Document res = new Document();
                        res.put("requestId", doc.getString("requestId"));
                        res.put("problemType", doc.getString("problemType"));
                        res.put("result", doc.get("result"));
                        return res;
                    })
                    .collect(Collectors.toList());

            // ✅ Envia para o tópico WebSocket
            messagingTemplate.convertAndSend("/topic/comparison/all", payload);

            // ✅ Remove resultados enviados
            mongoTemplate.remove(query, "verifications");
            mongoTemplate.remove(query, "comparisons");
        }
    }
}
