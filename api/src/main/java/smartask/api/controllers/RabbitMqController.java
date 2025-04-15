package smartask.api.controllers;

import org.springframework.web.bind.annotation.*;
import smartask.api.event.RabbitMqProducer;

@RestController
@RequestMapping("/rabbitmq")
public class RabbitMqController {

    private final RabbitMqProducer producer;

    public RabbitMqController(RabbitMqProducer producer) {
        this.producer = producer;
    }

    @PostMapping("/send")
    public String sendMessage(@RequestParam String message) {
        producer.sendMessage(message);
        return "Message sent: " + message;
    }
}
