package smartask.api.config;

import org.springframework.amqp.core.*;
import org.springframework.context.annotation.Bean;
import org.springframework.context.annotation.Configuration;

@Configuration
public class RabbitMqConfig {

    private static final String QUEUE_NAME = "task-queue";
    private static final String EXCHANGE_NAME = "task-exchange";
    private static final String ROUTING_KEY = "task-routing-key";

    @Bean
    public Queue queue() {
        return QueueBuilder.durable("task-queue")
                .withArgument("x-dead-letter-exchange", "dlx-exchange")  // Send to DLX on rejection
                .withArgument("x-dead-letter-routing-key", "dlx-routing-key")
                .build();
    }

    @Bean
    public DirectExchange deadLetterExchange() {
        return new DirectExchange("dlx-exchange");
    }

    @Bean
    public Queue deadLetterQueue() {
        return new Queue("task-queue-dlx", true);
    }

    @Bean
    public Binding dlqBinding() {
        return BindingBuilder.bind(deadLetterQueue()).to(deadLetterExchange()).with("dlx-routing-key");
    }


    @Bean
    public DirectExchange exchange() {
        return new DirectExchange(EXCHANGE_NAME);
    }

    @Bean
    public Binding binding(Queue queue, DirectExchange exchange) {
        return BindingBuilder.bind(queue).to(exchange).with(ROUTING_KEY);
    }
}
