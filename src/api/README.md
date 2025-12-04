# API Service

## Overview

Spring Boot REST API that serves as the main backend for the SmarTask system. Handles user authentication, schedule management, employee data, and orchestrates communication between the frontend and worker services via RabbitMQ.

## Technology Stack

- **Java 17** with **Spring Boot**
- **MongoDB** for data persistence
- **RabbitMQ** for asynchronous task processing
- **WebSocket** for real-time updates
- **Maven** for dependency management

## Project Structure

```
src/main/java/smartask/api/
├── ApiApplication.java          # Main Spring Boot application entry point
├── config/                      # Configuration classes
│   ├── RabbitMqConfig.java      # RabbitMQ setup
│   ├── SecurityConfig.java      # Authentication & authorization
│   └── WebSocketConfig.java     # WebSocket configuration
├── controllers/                 # REST API endpoints
├── services/                    # Business logic layer
├── repositories/                # MongoDB data access
├── models/                      # Domain entities and DTOs
├── event/                       # RabbitMQ producers & consumers
└── utils/                       # Utility classes

src/main/resources/
├── application.properties       # Application configuration
└── rules.json                   # Business rules (if present)
```

## Key Features

- **Schedule Management:** CRUD operations for work schedules
- **Employee Management:** Employee profiles, teams, and skills
- **Vacation Management:** Vacation templates and constraints
- **Task Orchestration:** Sends schedule generation tasks to RabbitMQ
- **Real-time Updates:** WebSocket notifications for task completion
- **Rules Management:** Business rules and constraints configuration

## Development

### Build & Run Locally

```bash
# Build with Maven
mvn clean install

# Run the application
mvn spring-boot:run

# The API will be available at http://localhost:8081
```

### Run with Docker

```bash
# From project root
make build-api
```

## API Endpoints

Access the API at `http://localhost:8081`

- **Health Check:** `GET /actuator/health`
- See controllers/ directory for all available endpoints

## Environment Variables

Configured in `application.properties`:
- MongoDB connection settings
- RabbitMQ connection settings
- Server port configuration
