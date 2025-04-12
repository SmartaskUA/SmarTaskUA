# Usando uma imagem base do Java 17
FROM openjdk:17-jdk-slim

# Copie o arquivo .jar do diretório atual para o container

COPY ./target/api-0.0.1-SNAPSHOT.jar api.jar

# Define o diretório de trabalho dentro do container

# Expõe a porta que a aplicação Spring Boot irá usar
EXPOSE 8081

# Comando para executar o jar da aplicação Spring Boot
CMD ["java", "-jar", "api.jar"]
