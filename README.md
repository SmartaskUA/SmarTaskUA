# SmartTask
Intelligent system for test automatically generating schedules work and evaluate them

# Lauching : 
#### Technical note: This project was developed and tested in operating systems from the Unix family (specifically Ubuntu and Arch Linux). No system test was performed in other operating systems (such as Windows or MacOS). If any troubleshooting problem is noticed in other environments, further investigation might be needed to adapt the system to be used in these environments.

### in this project's root, execute the following commands : 
##### (You need to have Docker Compose installed locally in your system; the commands might change from system to system.)

#### Build images and set for development.
```
docker-compose up --build
```


### The running frontend application can be accessed via :
```
http://localhost:5173/
```

#### After shutting down the application via command line, shut down the containers if not needed anymore.
```
docker-compose down
```

#### To debug a specific container/service that is running with the docker compose : 
```
docker compose logs [service name]
```

# Project Structure

```

SmarTaskUA/
├── algorithm/                          # Python Optimization Algorithms
│   ├── CSP.py, CSPv2.py
│   ├── ILP.py, ILPv2.py
│   ├── greedyClimbing.py
│   ├── greedyRandomized.py             #
│   ├── heuristicAlgorithm.py           # Heuristic algorithm
│   ├── kpiComparison.py
│   ├── kpiVerification.py              # For veryfying defined KPI's
│   ├── utils.py
│   ├── contexts/                       # Custom schedule generation (IN_PROGRESS)
│   ├── engines/                        # Custom schedule generation (IN_PROGRESS)
│   ├── handlers/                       # Custom schedule generation (IN_PROGRESS)
│   └── rules/                          # Custom schedule generation (IN_PROGRESS)
│
├── api/                                # Java Spring Boot Backend
│   ├── src/main/java/smartask/api/
│   │   ├── config/                     # (RabbitMqConfig, SecurityConfig, WebSocketConfig)
│   │   ├── controllers/                # (REST controllers)
│   │   ├── models/                     # (Employee, Schedule, Rule, Team, etc.)
│   │   ├── repositories/               # (Database access)
│   │   ├── services/                   # (Business logic)
│   │   └── event/                      # (RabbitMQ producer/consumer)
│   ├── src/main/resources/
│   ├── pom.xml
│   ├── Dockerfile
│   └── target/
│
├── frontend/                           # React + Vite Frontend
│   ├── src/
│   │   ├── Admin/                      # Admin pages
│   │   ├── Manager/                    # Manager pages & components
│   │   ├── components/                 # Reusable components
│   │   ├── context/                    # AuthContext
│   │   ├── login/
│   │   ├── assets/
│   │   └── styles/
│   ├── public/
│   ├── package.json
│   ├── vite.config.js
│   ├── tailwind.config.js
│   ├── Dockerfile / Dockerfile.dev
│   └── node_modules/
│
├── modules/                            # Python Task Management
│   ├── TaskManager.py
│   ├── MongoDBClient.py
│   ├── RabbitMQClient.py
│   ├── analyze.py, send_task.py
│   ├── requirements.txt
│   └── rules.json
│
├── data/                               # Data Templates (CSV files)
│   ├── minimuns.csv                    # General minimuns template file
│   ├── VacationTemplate.csv            # General Vacation template file
│   └── (other template variants)
│
├── shared_tmp/                         
├── docker-compose.yml
├── run-app.sh
└── README.md

```


# System Requirements

### Functional Requirements

1. **Generate new schedules**: The user should be able to configure/customize and perform a generating schedule task.
2. **Optmize the generated schedules**: The user must be able to optmize a previously generated schedule with specific method/algorithm that allows this base configuration.
3. **Fetch all schedules**: The user should be able to fetch and see all the generated schedules, and their metadata(info regarding the generating process, such as the algorithm used and a timestamp) as well
4. **Company restrictions management**:The user must be able to manage the restrictions used in the generation of the schedules.
5. **Real-time update of schedules generation process**: The user should be able to receive real-time notifications(in the system) of when a generating schedule task is finished
6. **Comparison between multiple schedules**: The system should have a feature of comparison between the newly generated schedule with the previouslys generated ones, the comparison is perfomed by a set of parameters (e.g. number of rules/restrictions fullfiled) 

### Non-Functional Requirements

1. **Performance and scalability in schedule generation**: When it comes to launch tasks(generate new schedules) and execute the task itselfs (the algorithsm and methods used to generate new schedules), the system must ensure effiency performance and scalability to reduce the time of execution and response to lowest as possible 
2. **System monitoring and metrics collection**: The system should have a simple but robust monitoring process, that could be achieved by logs (that are also stored in the file system for instance), and metrics collection regarding the algorithms execution should also be perfomed, since these data might be useful for some features related to schedules/algorithms comparison 
3. **Availability & reliability over the schedule generation process**: The system should be able to perform real-time (or almost) response to generating schedules process (tasks) and it should ensure reliability when it comes to the newly generated schedules and their useful 

