package smartask.api.config;

import org.springframework.amqp.core.*;
import org.springframework.amqp.rabbit.core.RabbitTemplate;
import org.springframework.amqp.support.converter.Jackson2JsonMessageConverter;
import org.springframework.context.annotation.Bean;
import org.springframework.context.annotation.Configuration;
import org.springframework.amqp.rabbit.connection.ConnectionFactory;

@Configuration
public class RabbitMqConfig {

    // Configuração de Tarefas
    private static final String TASK_QUEUE = "task-queue";
    private static final String TASK_EXCHANGE = "task-exchange";
    private static final String TASK_ROUTING_KEY = "task-routing-key";

    // Configuração de Status
    private static final String STATUS_QUEUE = "status-queue";
    private static final String STATUS_EXCHANGE = "status-exchange";
    private static final String STATUS_ROUTING_KEY = "status-routing-key";

    // Configuração para Tarefas
    @Bean
    public Queue taskQueue() {
        return QueueBuilder.durable(TASK_QUEUE).build();
    }

    @Bean
    public DirectExchange taskExchange() {
        return new DirectExchange(TASK_EXCHANGE);
    }

    @Bean
    public Binding taskBinding(Queue taskQueue, DirectExchange taskExchange) {
        return BindingBuilder.bind(taskQueue).to(taskExchange).with(TASK_ROUTING_KEY);
    }

    // Configuração para Status
    @Bean
    public Queue statusQueue() {
        return QueueBuilder.durable(STATUS_QUEUE).build();
    }

    @Bean
    public DirectExchange statusExchange() {
        return new DirectExchange(STATUS_EXCHANGE);
    }

    @Bean
    public Binding statusBinding(Queue statusQueue, DirectExchange statusExchange) {
        return BindingBuilder.bind(statusQueue).to(statusExchange).with(STATUS_ROUTING_KEY);
    }

    @Bean
    public Jackson2JsonMessageConverter jackson2JsonMessageConverter() {
        return new Jackson2JsonMessageConverter();
    }

    @Bean
    public RabbitTemplate rabbitTemplate(ConnectionFactory connectionFactory,
                                         Jackson2JsonMessageConverter converter) {
        RabbitTemplate template = new RabbitTemplate(connectionFactory);
        template.setMessageConverter(converter);
        return template;
    }
}
