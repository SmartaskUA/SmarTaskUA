package smartask.api.bootstrap;

import org.springframework.beans.factory.annotation.Value;
import org.springframework.core.io.ClassPathResource;
import org.springframework.mock.web.MockMultipartFile;
import org.springframework.stereotype.Component;
import org.springframework.web.multipart.MultipartFile;
import smartask.api.models.Employee;
import smartask.api.models.Team;
import smartask.api.models.requests.ScheduleRequest;
import smartask.api.services.EmployeeService;
import smartask.api.services.ReferenceService;
import smartask.api.services.SchedulesService;
import smartask.api.services.TeamService;
import smartask.api.services.VacationService;

import java.io.File;
import java.io.InputStream;
import java.nio.file.Files;
import java.util.ArrayList;
import java.util.LinkedHashMap;
import java.util.LinkedHashSet;
import java.util.List;
import java.util.Map;
import java.util.Objects;
import java.util.Optional;
import java.util.UUID;

@Component
public class ScenarioSeeder {

    private final TeamService teamService;
    private final EmployeeService employeeService;
    private final SchedulesService schedulesService;
    private final VacationService vacationService;
    private final ReferenceService referenceService;

    @Value("${smartask.defaults.enabled:true}")
    private boolean seedDefaults;

    @Value("${smartask.scenarios.enabled:false}")
    private boolean seedScenarios;

    @Value("${smartask.scenarios.run-algorithms:false}")
    private boolean runAlgorithms;

    public ScenarioSeeder(TeamService teamService,
                          EmployeeService employeeService,
                          SchedulesService schedulesService,
                          VacationService vacationService,
                          ReferenceService referenceService) {
        this.teamService = teamService;
        this.employeeService = employeeService;
        this.schedulesService = schedulesService;
        this.vacationService = vacationService;
        this.referenceService = referenceService;
    }

    public void seedIfEnabled() {
        if (seedDefaults) {
            seedDefaultTeams();
        }

        // ----------------------------------------------------
        // Create all 4 scenarios
        // ----------------------------------------------------
        if (!seedScenarios) {
            System.out.println("Scenario groups disabled (smartask.scenarios.enabled=false).");
            return;
        }
        if (hasScenarioGroups()) {
            System.out.println("Scenario groups already initialized - skipping scenario setup.");
            return;
        }
        // 2-shift scenarios (disabled for now)
        // createBaseScenario_2Teams12Employees();
        // createScenarioWithCrossing(4, 24, 0.20);
        // createScenarioWithCrossing(8, 48, 0.20);
        // createScenarioWithCrossing(16, 96, 0.20);
        // createScenarioWithCrossing(32, 192, 0.20);

        // 3-shift scenarios
        createScenarioWithCrossing(2, 24, 0.20);
        createScenarioWithCrossing(4, 48, 0.20);
        createScenarioWithCrossing(8, 96, 0.20);
        createScenarioWithCrossing(16, 192, 0.20);
        createScenarioWithCrossing(32, 384, 0.20);

        loadTemplatesIntoDatabase();

        System.out.println("\nAll team scenarios successfully initialized!");
    }

    public void runScenarioAlgorithmsIfEnabled(String algorithmName) {
        if (!seedScenarios) {
            System.out.println("Scenario groups disabled (smartask.scenarios.enabled=false).");
            return;
        }
        if (!runAlgorithms) {
            System.out.println("Scenario algorithm runs disabled (smartask.scenarios.run-algorithms=false).");
            return;
        }
        if (!hasScenarioGroups()) {
            System.out.println("Scenario groups not initialized - skipping algorithm runs.");
            return;
        }
        runLinearProgrammingScenarios(algorithmName);
    }

    private void seedDefaultTeams() {
        Team teamA = findTeamByNameNoGroup("Equipa A");
        Team teamB = findTeamByNameNoGroup("Equipa B");

        if (teamA == null) {
            teamA = new Team("Equipa A");
            teamService.addTeam(teamA);
        }
        if (teamB == null) {
            teamB = new Team("Equipa B");
            teamService.addTeam(teamB);
        }

        // Criar 21 funcionários: 7 exclusivos para A, 7 exclusivos para B, 7 para ambas
        ensureEmployeesExist(1, 21);

        // IDs dos funcionários
        List<String> onlyA = employeeIdsInRange(1, 7);      // 1-7
        List<String> onlyB = employeeIdsInRange(8, 14);     // 8-14
        List<String> both = employeeIdsInRange(15, 21);     // 15-21

        // Adicionar aos respetivos grupos
        addEmployeesToTeam(teamA, onlyA);
        addEmployeesToTeam(teamB, onlyB);
        addEmployeesToTeam(teamA, both);
        addEmployeesToTeam(teamB, both);

        System.out.println("[Startup] Criados 7 exclusivos para Equipa A, 7 exclusivos para Equipa B e 7 para ambas as equipas.");
    }

    // BASE SCENARIO (exactly as requested):
    // Group = Scenario_2Teams
    // - Equipa A: 10 members (S2-E1..S2-E10)
    // - Equipa B: 5 members total, with 3 shared with A:
    //     shared = S2-E8, S2-E9, S2-E10
    //     unique to B = S2-E11, S2-E12
    // => 12 unique employees total
    private void createBaseScenario_2Teams12Employees() {
        final String groupName = "Scenario_2Teams";

        System.out.println("\nInitializing " + groupName + " -> 2 teams, 12 employees");

        Team teamA = createOrGetTeam("Equipa A", groupName);
        Team teamB = createOrGetTeam("Equipa B", groupName);

        // Create 12 unique employees for this scenario
        List<Employee> all = new ArrayList<>();
        for (int i = 1; i <= 12; i++) {
            String name = "Employee " + i;
            Employee e = new Employee(name);
            employeeService.addEmployee(e);
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
    private void createScenarioWithCrossing(int numTeams, int numEmployees, double crossRatio) {

        final String groupName = "Scenario_" + numTeams + "Teams";

        System.out.printf("%nInitializing %s -> %d teams, %d employees, cross=%.0f%%%n",
                groupName, numTeams, numEmployees, crossRatio * 100);

        // Create teams A..(A+numTeams-1), supporting multi-char labels beyond Z (AA, AB, ...)
        List<Team> teams = new ArrayList<>();
        for (int t = 0; t < numTeams; t++) {
            String teamName = "Equipa " + teamLabel(t);
            teams.add(createOrGetTeam(teamName, groupName));
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
        for (int t = 0; t < numTeams; t++) {
            primaryByTeam.add(new ArrayList<>());
        }

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
            System.out.printf("  - %s: primary~%d, +cross~%d%n",
                    teams.get(t).getName(), prim, crossAdded);
        }
        System.out.printf("%s initialized with primary distribution and cross-memberships.%n", groupName);
    }

    // ----------------------------------------------------------------
    // Helpers
    // ----------------------------------------------------------------

    /**
     * Convert a 0-based team index to a label: A, B, ..., Z, AA, AB, ..., AF, ...
     * Mirrors Python _team_label() in minimum_generation_template.py.
     */
    private static String teamLabel(int t) {
        StringBuilder label = new StringBuilder();
        int n = t;
        do {
            label.insert(0, (char) ('A' + n % 26));
            n = n / 26 - 1;
        } while (n >= 0);
        return label.toString();
    }

    private Team createOrGetTeam(String name, String groupName) {
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

    private Team findTeamByNameNoGroup(String name) {
        return teamService.getTeams().stream()
                .filter(t -> name.equals(t.getName()))
                .filter(t -> t.getGroupName() == null || t.getGroupName().isBlank())
                .findFirst()
                .orElse(null);
    }

    private boolean hasScenarioGroups() {
        return teamService.getTeams().stream()
                .map(Team::getGroupName)
                .filter(Objects::nonNull)
                .anyMatch(name -> name.startsWith("Scenario_"));
    }

    private void ensureEmployeesExist(int startInclusive, int endInclusive) {
        List<Employee> employees = employeeService.getEmployees();
        for (int i = startInclusive; i <= endInclusive; i++) {
            String name = "Employee " + i;
            boolean exists = employees.stream().anyMatch(e -> name.equals(e.getName()));
            if (!exists) {
                employeeService.addEmployee(new Employee(name));
            }
        }
    }

    private List<String> employeeIdsInRange(int startInclusive, int endInclusive) {
        return employeeService.getEmployees().stream()
                .filter(e -> e.getName() != null && e.getName().startsWith("Employee "))
                .filter(e -> {
                    try {
                        int n = Integer.parseInt(e.getName().split(" ")[1]);
                        return n >= startInclusive && n <= endInclusive;
                    } catch (NumberFormatException ex) {
                        return false;
                    }
                })
                .map(Employee::getId)
                .toList();
    }

    private Employee findEmployeeByName(String name) {
        return employeeService.getEmployees().stream()
                .filter(e -> name.equals(e.getName()))
                .findFirst()
                .orElse(null);
    }

    private void addEmployeesToTeam(Team team, List<String> employeeIds) {
        if (team == null || employeeIds == null || employeeIds.isEmpty()) {
            return;
        }
        List<String> currentEmployeeIds = team.getEmployeeIds() != null
                ? new ArrayList<>(team.getEmployeeIds())
                : new ArrayList<>();

        for (String empId : employeeIds) {
            Employee employee = employeeService.getEmployeeById(empId);
            if (employee.getTeamIds() == null) {
                employee.setTeamIds(new LinkedHashSet<>());
            }
            employee.getTeamIds().add(team.getId());
            employeeService.saveEmployee(employee);

            if (!currentEmployeeIds.contains(empId)) {
                currentEmployeeIds.add(empId);
            }
        }

        team.setEmployeeIds(currentEmployeeIds);
        teamService.addTeam(team);
    }

    private void loadTemplatesIntoDatabase() {
        try {
            System.out.println("\nLoading vacation and minimun templates from /resources...");

            // === Vacation Templates ===
            // 2-shift templates (disabled for now)
            // String[] employeeFolders = {"12", "24", "48", "96"};
            String[] employeeFolders = {"24", "48", "96", "192"};
            for (String empCount : employeeFolders) {
                String basePath = "vacationData_3shifts/" + empCount + "_employees/templates/";
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
                        System.err.println("Could not load vacation template: " + name + " - " + e.getMessage());
                    }
                }
            }

            // === Minimuns / Reference Templates ===
            // Located at /resources/minimuns/minimuns_4teams_24emp.csv etc.
            // 2-shift templates (disabled for now)
            // String[] refFiles = {
            //         "minimuns_2teams_12emp.csv",
            //         "minimuns_4teams_24emp.csv",
            //         "minimuns_8teams_48emp.csv",
            //         "minimuns_16teams_96emp.csv"
            // };
            String[] refFiles = {
                    "minimuns_3shifts_2teams_24emp.csv",
                    "minimuns_3shifts_4teams_48emp.csv",
                    "minimuns_3shifts_8teams_96emp.csv",
                    "minimuns_3shifts_16teams_192emp.csv"
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
                    System.err.println("Could not load reference template " + file + " - " + e.getMessage());
                }
            }

        } catch (Exception e) {
            System.err.println("Error while loading templates: " + e.getMessage());
            e.printStackTrace();
        }
    }

    private void runLinearProgrammingScenarios(String algorithmName) {
        System.out.println("\nStarting sequential " + algorithmName + " runs for all scenarios...");

        // Ordered map: smallest scenario first
        Map<String, String> minimunToGroup = new LinkedHashMap<>();
        // 2-shift templates (disabled for now)
        // minimunToGroup.put("minimuns_2teams_12emp", "Scenario_2Teams");
        // minimunToGroup.put("minimuns_4teams_24emp", "Scenario_4Teams");
        // minimunToGroup.put("minimuns_8teams_48emp", "Scenario_8Teams");
        // minimunToGroup.put("minimuns_16teams_96emp", "Scenario_16Teams");
        minimunToGroup.put("minimuns_3shifts_2teams_24emp", "Scenario_2Teams");
        minimunToGroup.put("minimuns_3shifts_4teams_48emp", "Scenario_4Teams");
        minimunToGroup.put("minimuns_3shifts_8teams_96emp", "Scenario_8Teams");
        minimunToGroup.put("minimuns_3shifts_16teams_192emp", "Scenario_16Teams");

        for (Map.Entry<String, String> entry : minimunToGroup.entrySet()) {
            String minimunName = entry.getKey();
            String groupName = entry.getValue();

            String employeeCount = minimunName.replaceAll(".*_(\\d+)emp$", "$1");

            for (int caseNum = 1; caseNum <= 4; caseNum++) {
                String vacationTemplate = "VacationTemplate_Case" + caseNum + "_" + employeeCount;
                String title;
                if (algorithmName.equals("linear programming 2")) {
                    title = "ILPv2_" + groupName + "_Case" + caseNum;
                } else if (algorithmName.equals("ilp_solver_3")) {
                    title = "ILPv3_" + groupName + "_Case" + caseNum;
                } else if (algorithmName.equals("Heuristic Solver")) {
                    title = "Heuristic_" + groupName + "_Case" + caseNum;
                } else if (algorithmName.equals("Greedy Randomized")) {
                    title = "GreedyRandomized_" + groupName + "_Case" + caseNum;
                } else if (algorithmName.equals("ilp_greedy")) {
                    title = "ILP-Greedy_" + groupName + "_Case" + caseNum;
                } else {
                    title = "CSPv2_" + groupName + "_Case" + caseNum;
                }

                String taskId = UUID.randomUUID().toString();

                ScheduleRequest req = new ScheduleRequest(
                        taskId,
                        "2025",                      // year
                        algorithmName,               // algorithm
                        title,                       // title
                        "45",                        // maxTime (minutes)
                        java.time.LocalDateTime.now(),
                        vacationTemplate,
                        minimunName,
                        3,                           // shifts
                        null,                        // hours
                        groupName                    // group name
                );

                System.out.printf("\nSubmitting [%s] with VacationTemplate '%s'%n", title, vacationTemplate);
                try {
                    String res = schedulesService.requestScheduleGeneration(req);
                    System.out.printf("[%s vs %s] -> %s%n", minimunName, vacationTemplate, res);

                    waitForTaskCompletion(taskId, title, 45);
                } catch (Exception e) {
                    System.err.printf("Failed for %s x %s -> %s%n", minimunName, vacationTemplate, e.getMessage());
                }
            }
        }

        System.out.println("\nAll scheduling tasks completed sequentially!");
    }

    private void waitForTaskCompletion(String taskId, String title, int maxMinutes) {
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
                        System.out.printf("[OK] Task '%s' completed successfully.%n", title);
                        break;
                    }
                    if ("FAILED".equalsIgnoreCase(status)) {
                        System.err.printf("[FAIL] Task '%s' failed.%n", title);
                        break;
                    }
                } else {
                    System.out.printf("[WAIT] Task '%s' not yet created in DB, waiting...%n", title);
                }

                if (System.currentTimeMillis() - start > timeout) {
                    System.err.printf("[TIMEOUT] Task '%s' timed out. Moving to next.%n", title);
                    break;
                }

                Thread.sleep(5000);
            } catch (Exception e) {
                System.err.printf("[WARN] Error checking status of '%s': %s%n", title, e.getMessage());
                break;
            }
        }
    }
}
