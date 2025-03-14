package smartask.api.utils;

import com.fasterxml.jackson.core.JsonParser;
import com.fasterxml.jackson.databind.JsonNode;
import com.fasterxml.jackson.databind.ObjectMapper;
import com.fasterxml.jackson.databind.node.ObjectNode;
import com.fasterxml.jackson.databind.deser.std.StdDeserializer;

import java.io.IOException;

public class JsonNodeDeserializer extends StdDeserializer<JsonNode> {

    public JsonNodeDeserializer() {
        super(JsonNode.class);
    }

    @Override
    public JsonNode deserialize(JsonParser jp, com.fasterxml.jackson.databind.DeserializationContext ctxt) throws IOException {
        ObjectMapper mapper = (ObjectMapper) jp.getCodec();
        JsonNode node = mapper.readTree(jp);

        // Handle different types of JsonNode explicitly if needed
        if (node instanceof ObjectNode) {
            return (ObjectNode) node;  // Return as ObjectNode if that's the type
        }

        return node; // Return as generic JsonNode for others (ArrayNode, etc.)
    }
}
