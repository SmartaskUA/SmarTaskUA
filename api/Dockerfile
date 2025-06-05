# Etapa 1: Build com Maven e cache de dependências
FROM maven:3.9.6-eclipse-temurin-17 AS build

WORKDIR /app

# Copie apenas o pom.xml primeiro
COPY pom.xml .

# Baixe dependências (isso usa o cache se o pom.xml não mudar)
RUN mvn dependency:go-offline

# Agora copie o restante do código
COPY src ./src

# Compile o projeto
RUN mvn clean install


# Etapa 2: Imagem final
FROM openjdk:17-jdk-slim

WORKDIR /app

COPY --from=build /app/target/api-0.0.1-SNAPSHOT.jar api.jar

EXPOSE 8081

CMD ["java", "-jar", "api.jar"]
