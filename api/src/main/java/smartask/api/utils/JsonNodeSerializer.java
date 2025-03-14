package smartask.api.utils;

import com.fasterxml.jackson.core.JsonGenerator;
import com.fasterxml.jackson.databind.JsonNode;
import com.fasterxml.jackson.databind.SerializerProvider;
import com.fasterxml.jackson.databind.ser.std.StdSerializer;

import java.io.IOException;

public class JsonNodeSerializer extends StdSerializer<JsonNode> {

    public JsonNodeSerializer() {
        super(JsonNode.class);
    }

    @Override
    public void serialize(JsonNode value, JsonGenerator gen, SerializerProvider provider) throws IOException {
        gen.writeTree(value);
    }
}
