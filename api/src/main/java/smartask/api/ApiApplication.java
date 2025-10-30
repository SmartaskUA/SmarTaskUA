package smartask.api;

import org.springframework.boot.CommandLineRunner;
import org.springframework.boot.SpringApplication;
import org.springframework.boot.autoconfigure.SpringBootApplication;
import org.springframework.context.annotation.Bean;
import org.springframework.core.io.ClassPathResource;
import org.springframework.scheduling.annotation.EnableScheduling;
import org.springframework.web.multipart.MultipartFile;

import com.fasterxml.jackson.databind.ObjectMapper;

import smartask.api.event.RabbitMqProducer;
import smartask.api.models.Employee;
import smartask.api.models.RuleSet;
import smartask.api.models.Team;
import smartask.api.models.requests.ScheduleRequest;
import smartask.api.repositories.SchedulesRepository;
import smartask.api.services.EmployeeService;
import smartask.api.services.ReferenceService;
import smartask.api.services.RuleSetService;
import smartask.api.services.SchedulesService;
import smartask.api.services.TeamService;
import smartask.api.services.VacationService;
import org.springframework.mock.web.MockMultipartFile;
import java.io.File;
import java.io.InputStream;
import java.nio.file.Files;
import java.util.*;

@EnableScheduling
@SpringBootApplication
public class ApiApplication {

    public static void main(String[] args) {
        SpringApplication.run(ApiApplication.class, args);
    }

    @Bean
    CommandLineRunner initDatabase(TeamService teamService,
                                   EmployeeService employeeService,
                                   SchedulesRepository schedulesRepository,
                                   SchedulesService schedulesService,
                                   RabbitMqProducer producer,
                                   RuleSetService ruleSetService,
                                   VacationService vacationService,
                                   ReferenceService referenceService) {
        return args -> {

            if (!teamService.getTeams().isEmpty()) {
                System.out.println("⚠️ Database already initialized — skipping setup.");
            return;
            }


            ObjectMapper mapper = new ObjectMapper();
            InputStream inputStream = new ClassPathResource("rules.json").getInputStream();
            if (inputStream != null) {
                RuleSet defaultSet = mapper.readValue(inputStream, RuleSet.class);
                if (defaultSet.getName() == null || defaultSet.getName().isBlank()) {
                    defaultSet.setName("default");
                }
                if (defaultSet.getDescription() == null || defaultSet.getDescription().isBlank()) {
                    defaultSet.setDescription("Default rule set loaded from JSON");
                }
                ruleSetService.saveRuleSet(defaultSet);
                System.out.println("Default rule set loaded successfully!");
            } else {
                System.err.println("Could not find rules.json in resources folder!");
            }

            // ----------------------------------------------------
            // Create all 4 scenarios
            // ----------------------------------------------------
            createBaseScenario_2Teams12Employees(teamService, employeeService);    
            createScenarioWithCrossing(teamService, employeeService, 4, 24, 0.20);
            createScenarioWithCrossing(teamService, employeeService, 8, 48, 0.20);
            createScenarioWithCrossing(teamService, employeeService, 16, 96, 0.20);
            loadTemplatesIntoDatabase(vacationService, referenceService);
            runLinearProgrammingScenarios(schedulesService, "CSPv2");
            runLinearProgrammingScenarios(schedulesService, "linear programming 2");

            System.out.println("\nAll team scenarios successfully initialized!");
        };
    }

    // BASE SCENARIO (exactly as requested):
    // Group = Scenario_2Teams
    // - Equipa A: 10 members (S2-E1..S2-E10)
    // - Equipa B: 5 members total, with 3 shared with A:
    //     shared = S2-E8, S2-E9, S2-E10
    //     unique to B = S2-E11, S2-E12
    // => 12 unique employees total
    private void createBaseScenario_2Teams12Employees(TeamService teamService, EmployeeService employeeService) {
        final String groupName = "Scenario_2Teams";

        System.out.println("\nInitializing " + groupName + " → 2 teams, 12 employees");

        Team teamA = createOrGetTeam(teamService, "Equipa A", groupName);
        Team teamB = createOrGetTeam(teamService, "Equipa B", groupName);

        // Create 12 unique employees for this scenario
        List<Employee> all = new ArrayList<>();
        for (int i = 1; i <= 12; i++) {
            String name = "Employee " + i;
            Employee e = new Employee(name);
            employeeService.addEmployee(e); // do NOT check name existence; scenario-specific namespace avoids collisions
            all.add(e);
        }

        // A primary = E1..E10
        List<String> aPrimIds = ids(all, 1, 10);
        teamService.addEmployeesToTeam(teamA.getName(), aPrimIds, groupName);

        // B shared with A = E8,E9,E10; plus unique E11,E12
        List<String> bIds = new ArrayList<>();
        bIds.addAll(ids(all, 8, 10));     // shared 3
        bIds.addAll(ids(all, 11, 12));    // unique 2
        teamService.addEmployeesToTeam(teamB.getName(), bIds, groupName);

        System.out.printf("%s ready. A=%d (with 3 shared), B=%d, unique=%d%n",
                groupName, aPrimIds.size(), bIds.size(), 12);
    }

    // ----------------------------------------------------------------
    // GENERIC SCENARIO MAKER WITH CROSSING
    // - Evenly distributes employees as primary members across N teams
    // - Adds cross-memberships: for each team, ~crossRatio of its size
    //   borrowed from the NEXT team (wrap around)
    // ----------------------------------------------------------------
    private void createScenarioWithCrossing(TeamService teamService,
                                            EmployeeService employeeService,
                                            int numTeams,
                                            int numEmployees,
                                            double crossRatio) {

        final String groupName = "Scenario_" + numTeams + "Teams";

        System.out.printf("%n🧱 Initializing %s → %d teams, %d employees, cross=%.0f%%%n",
                groupName, numTeams, numEmployees, crossRatio * 100);

        // Create teams A..(A+numTeams-1)
        List<Team> teams = new ArrayList<>();
        for (int t = 0; t < numTeams; t++) {
            String teamName = "Equipa " + (char) ('A' + t);
            teams.add(createOrGetTeam(teamService, teamName, groupName));
        }

        // Create unique employees for this scenario
        List<Employee> emps = new ArrayList<>(numEmployees);
        for (int i = 1; i <= numEmployees; i++) {
            Employee e = new Employee("Employee " + i);
            employeeService.addEmployee(e);
            emps.add(e);
        }

        // Primary assignment (round-robin)
        List<List<Employee>> primaryByTeam = new ArrayList<>();
        for (int t = 0; t < numTeams; t++) primaryByTeam.add(new ArrayList<>());

        for (int i = 0; i < emps.size(); i++) {
            int t = i % numTeams;
            primaryByTeam.get(t).add(emps.get(i));
        }

        // Add primary members to teams
        for (int t = 0; t < numTeams; t++) {
            List<String> ids = primaryByTeam.get(t).stream().map(Employee::getId).toList();
            teamService.addEmployeesToTeam(teams.get(t).getName(), ids, groupName);
        }

        // Cross-memberships: borrow from next team (wrap) ~ crossRatio
        for (int t = 0; t < numTeams; t++) {
            int next = (t + 1) % numTeams;
            List<Employee> donors = primaryByTeam.get(next); // borrow from the "next" team
            int toShare = Math.max(1, (int) Math.round(primaryByTeam.get(t).size() * crossRatio));

            // pick first N donors (or randomize as you like)
            for (int i = 0; i < Math.min(toShare, donors.size()); i++) {
                teamService.addEmployeesToTeam(teams.get(t).getName(), List.of(donors.get(i).getId()), groupName);
            }
        }

        // Console summary
        for (int t = 0; t < numTeams; t++) {
            int prim = primaryByTeam.get(t).size();
            int crossAdded = Math.max(1, (int) Math.round(primaryByTeam.get(t).size() * crossRatio));
            System.out.printf("  • %s: primary≈%d, +cross≈%d%n",
                    teams.get(t).getName(), prim, crossAdded);
        }
        System.out.printf("%s initialized with primary distribution and cross-memberships.%n", groupName);
    }

    // ----------------------------------------------------------------
    // Helpers
    // ----------------------------------------------------------------
    private Team createOrGetTeam(TeamService teamService, String name, String groupName) {
        return teamService.getTeams().stream()
                .filter(t -> name.equals(t.getName()) && groupName.equals(t.getGroupName()))
                .findFirst()
                .orElseGet(() -> {
                    Team t = new Team(name, groupName);
                    teamService.addTeam(t);
                    return t;
                });
    }

    private List<String> ids(List<Employee> emps, int startInclusive, int endInclusive) {
        List<String> res = new ArrayList<>();
        for (int i = startInclusive; i <= endInclusive; i++) {
            res.add(emps.get(i - 1).getId());
        }
        return res;
    }


    private void loadTemplatesIntoDatabase(VacationService vacationService,
                                       ReferenceService referenceService) {
        try {
            System.out.println("\nLoading vacation and minimun templates from /resources...");

            // === Vacation Templates ===
            String[] employeeFolders = {"12", "24", "48", "96"};
            for (String empCount : employeeFolders) {
                String basePath = "vacationData/" + empCount + "_employees/templates/";
                for (int caseNum = 1; caseNum <= 4; caseNum++) {
                    String name = "VacationTemplate_Case" + caseNum + "_" + empCount;
                    String path = basePath + name + ".csv";

                    try (InputStream is = new ClassPathResource(path).getInputStream()) {
                        if (is != null) {
                            // Temporarily write to a temp file for existing parser
                            File temp = File.createTempFile("vac", ".csv");
                            Files.copy(is, temp.toPath(), java.nio.file.StandardCopyOption.REPLACE_EXISTING);
                            vacationService.processCsvFileAndGenerateTemplate(name, temp.getAbsolutePath());
                            temp.delete();
                            System.out.println("Vacation template loaded: " + name);
                        }
                    } catch (Exception e) {
                        System.err.println("Could not load vacation template: " + name + " — " + e.getMessage());
                    }
                }
            }

            // === Minimuns / Reference Templates ===
            // Located at /resources/minimuns/minimuns_4teams_24emp.csv etc.
            String[] refFiles = {
                    "minimuns_2teams_12emp.csv",
                    "minimuns_4teams_24emp.csv",
                    "minimuns_8teams_48emp.csv",
                    "minimuns_16teams_96emp.csv"
            };

            for (String file : refFiles) {
                try (InputStream is = new ClassPathResource("minimuns/" + file).getInputStream()) {
                    if (is != null) {
                        String name = file.replace(".csv", "");
                        MultipartFile mf = new MockMultipartFile(name, file, "text/csv", is.readAllBytes());
                        referenceService.createTemplateFromCsv(name, mf);
                        System.out.println("Reference template loaded: " + name);
                    }
                } catch (Exception e) {
                    System.err.println("Could not load reference template " + file + " — " + e.getMessage());
                }
            }

        } catch (Exception e) {
            System.err.println(" Error while loading templates: " + e.getMessage());
            e.printStackTrace();
        }
    }

private void runLinearProgrammingScenarios(SchedulesService schedulesService, String algorithmName) {
    System.out.println("\n Starting sequential " + algorithmName + " runs for all scenarios...");

    // Ordered map: smallest scenario first
    Map<String, String> minimunToGroup = new LinkedHashMap<>();
    minimunToGroup.put("minimuns_2teams_12emp", "Scenario_2Teams");
    minimunToGroup.put("minimuns_4teams_24emp", "Scenario_4Teams");
    minimunToGroup.put("minimuns_8teams_48emp", "Scenario_8Teams");
    minimunToGroup.put("minimuns_16teams_96emp", "Scenario_16Teams");

    for (Map.Entry<String, String> entry : minimunToGroup.entrySet()) {
        String minimunName = entry.getKey();
        String groupName = entry.getValue();

        String employeeCount = minimunName.replaceAll(".*_(\\d+)emp$", "$1");

        for (int caseNum = 1; caseNum <= 4; caseNum++) {
            String vacationTemplate = "VacationTemplate_Case" + caseNum + "_" + employeeCount;
            String title;
            if (algorithmName.equals("linear programming 2")) {
               title = "ILPv2_";
            } else {
               title = "CSPv2_" + groupName + "_Case" + caseNum;
            }

            title = title + groupName + "_Case" + caseNum;
            String taskId = UUID.randomUUID().toString();

            ScheduleRequest req = new ScheduleRequest(
                taskId,
                "2025",                      // year
                algorithmName,               // algorithm
                title,                       // title
                "5",                         // maxTime (minutes)
                java.time.LocalDateTime.now(),
                vacationTemplate,
                minimunName,
                2,                           // shifts
                "default",                   // rule set
                groupName                    // group name
            );

            System.out.printf("\nSubmitting [%s] with VacationTemplate '%s'%n", title, vacationTemplate);
            try {
                String res = schedulesService.requestScheduleGeneration(req);
                System.out.printf("[%s vs %s] → %s%n", minimunName, vacationTemplate, res);

                waitForTaskCompletion(taskId, title, schedulesService, 5);
            } catch (Exception e) {
                System.err.printf("Failed for %s x %s → %s%n", minimunName, vacationTemplate, e.getMessage());
            }
        }
    }

    System.out.println("\nAll ILP-2 scheduling tasks completed sequentially!");
}

private void waitForTaskCompletion(String taskId, String title, SchedulesService schedulesService, int maxMinutes) {
    System.out.printf("Waiting for completion of task '%s'...%n", title);
    long start = System.currentTimeMillis();
    long timeout = maxMinutes * 60 * 1000L; // Convert minutes to milliseconds

    while (true) {
        try {
            Optional<smartask.api.models.TaskStatus> statusOpt =
                    schedulesService.getTaskStatusRepository().findById(taskId);

            if (statusOpt.isPresent()) {
                String status = statusOpt.get().getStatus();
                if ("COMPLETED".equalsIgnoreCase(status)) {
                    System.out.printf("✅ Task '%s' completed successfully.%n", title);
                    break;
                }
                if ("FAILED".equalsIgnoreCase(status)) {
                    System.err.printf("❌ Task '%s' failed.%n", title);
                    break;
                }
            } else {
                System.out.printf("🕓 Task '%s' not yet created in DB, waiting...%n", title);
            }

            if (System.currentTimeMillis() - start > timeout) {
                System.err.printf("⚠️ Timeout reached for task '%s'. Moving to next.%n", title);
                break;
            }

            Thread.sleep(5000);
        } catch (Exception e) {
            System.err.printf("⚠️ Error checking status of '%s': %s%n", title, e.getMessage());
            break;
        }
    }
}


}
