package smartask.api.services;

import lombok.RequiredArgsConstructor;
import org.springframework.stereotype.Service;
import smartask.api.models.ProblemDefinition;
import smartask.api.models.ReferenceTemplate;
import smartask.api.models.VacationTemplate;
import smartask.api.models.requests.ProblemSolveRequest;
import smartask.api.models.requests.ScheduleRequest;
import smartask.api.repositories.ProblemRepository;
import smartask.api.repositories.ReferenceTemplateRepository;
import smartask.api.repositories.VacationTemplateRepository;

import com.fasterxml.jackson.databind.ObjectMapper;

import java.io.BufferedReader;
import java.io.IOException;
import java.nio.charset.StandardCharsets;
import java.nio.file.Files;
import java.nio.file.Path;
import java.nio.file.Paths;
import java.time.LocalDate;
import java.time.LocalDateTime;
import java.time.Year;
import java.time.format.DateTimeFormatter;
import java.time.format.DateTimeParseException;
import java.util.ArrayList;
import java.util.LinkedHashMap;
import java.util.LinkedHashSet;
import java.util.List;
import java.util.Map;
import java.util.Optional;
import java.util.Set;
import java.util.UUID;

@Service
@RequiredArgsConstructor
public class ProblemService {

    private static final Set<String> GENERAL_ALGORITHMS = Set.of(
            "ilp general",
            "csp general"
    );
    private static final List<String> VACATION_KEYWORDS = List.of(
            "vacation",
            "vacations",
            "vacationtemplate",
            "vacation_template"
    );
    private static final List<String> MINIMUMS_KEYWORDS = List.of(
            "minimun",
            "minimuns",
            "minimum",
            "minimums",
            "minimo",
            "minimos"
    );
    private static final List<String> DEMAND_KEYWORDS = List.of(
            "demand",
            "demanda"
    );

    private final ProblemRepository problemRepository;
    private final VacationTemplateRepository vacationTemplateRepository;
    private final ReferenceTemplateRepository referenceTemplateRepository;
    private final ObjectMapper objectMapper = new ObjectMapper();

    public List<Map<String, Object>> getAllProblemListItems() {
        List<ProblemDefinition> problems = getAllDefinitions();
        List<Map<String, Object>> items = new ArrayList<>();
        for (ProblemDefinition def : problems) {
            Map<String, Object> item = loadListItem(def);
            if (item != null) {
                items.add(item);
            }
        }
        return items;
    }

    public Optional<ProblemDefinition> getDefinitionByProblemId(String problemId) {
        return problemRepository.findByProblemId(problemId);
    }

    public Optional<Map<String, Object>> getProblemListItem(String problemId) {
        return getDefinitionByProblemId(problemId).map(this::loadListItem);
    }

    public Optional<Map<String, Object>> getProblemJson(String problemId) {
        if (problemId == null || problemId.isBlank()) {
            return Optional.empty();
        }
        Optional<ProblemDefinition> definition = getDefinitionByProblemId(problemId);
        if (definition.isEmpty()) {
            return Optional.empty();
        }
        String problemPath = definition.get().getProblemPath();
        if (problemPath == null || problemPath.isBlank()) {
            return Optional.empty();
        }
        Path repoRoot = resolveRepoRoot();
        Path path = repoRoot == null ? Paths.get(problemPath) : repoRoot.resolve(problemPath);
        Map<String, Object> root = readProblemJson(path);
        if (root == null) {
            return Optional.empty();
        }
        return Optional.of(root);
    }

    public ProblemDefinition save(ProblemDefinition problem) {
        problem.setUpdatedAt(java.time.Instant.now());
        if (problem.getCreatedAt() == null) {
            problem.setCreatedAt(java.time.Instant.now());
        }
        return problemRepository.save(problem);
    }

    public ScheduleRequest buildScheduleRequest(ProblemDefinition problem, ProblemSolveRequest request) {
        Map<String, Object> root = loadProblemJson(problem);
        if (root == null) {
            throw new IllegalStateException("Problem definition is missing problem.json data.");
        }
        Map<String, Object> metadata = getMap(root, "metadata");
        Map<String, Object> temporal = getMap(root, "temporalScope");
        Map<String, Object> demand = getMap(root, "demand");
        Map<String, Object> constraints = getMap(root, "constraints");

        String problemId = resolveValue(getString(metadata, "problemId"), problem.getProblemId());
        if (problemId == null || problemId.isBlank()) {
            throw new IllegalStateException("Problem is missing metadata.problemId.");
        }

        String year = null;
        Object yearObj = temporal.get("year");
        if (yearObj != null) {
            year = String.valueOf(yearObj);
        }

        Integer shifts = null;
        Object shiftsObj = demand.get("shifts");
        if (shiftsObj instanceof List<?> shiftsList) {
            shifts = shiftsList.size();
        }

        Path problemPath = resolveProblemPath(problem);
        if (problemPath == null) {
            throw new IllegalStateException("Problem definition is missing problem.json path.");
        }

        List<String> rawDataFiles = collectDataFiles(root);
        List<String> resolvedDataFiles = resolveDataFiles(problemPath, rawDataFiles);
        List<String> bundleFiles = listBundleFiles(problemPath);
        List<String> dataFiles = mergeDataFiles(resolvedDataFiles, bundleFiles);

        TemplateNames templateNames = ensureProblemTemplates(problemId, problem.getProblemPath(), year, dataFiles);
        ScheduleRequest scheduleRequest = new ScheduleRequest();
        scheduleRequest.setTaskId(UUID.randomUUID().toString());
        scheduleRequest.setAlgorithm(request.getAlgorithm());
        scheduleRequest.setTitle(resolveTitle(problem, request.getTitle(), request.getAlgorithm()));
        scheduleRequest.setMaxTime(request.getMaxTime() == null || request.getMaxTime().isBlank() ? "45" : request.getMaxTime());
        scheduleRequest.setRequestedAt(LocalDateTime.now());
        scheduleRequest.setYear(resolveValue(request.getYear(), year));
        scheduleRequest.setVacationTemplate(templateNames.vacationsName);
        scheduleRequest.setMinimuns(templateNames.minimunsName);
        scheduleRequest.setShifts(request.getShifts() == null ? shifts : request.getShifts());
        scheduleRequest.setHours(request.getHours());
        scheduleRequest.setGroupName(null);

        if (shouldUseConstraints(request.getAlgorithm(), constraints)) {
            scheduleRequest.setConstraints(constraints);
        }

        List<Map<String, Object>> employees = loadProblemEmployees(problem);
        if (!employees.isEmpty()) {
            scheduleRequest.setEmployees(employees);
        }

        return scheduleRequest;
    }

    public boolean isGeneralAlgorithm(String algorithm) {
        if (algorithm == null) {
            return false;
        }
        return GENERAL_ALGORITHMS.contains(algorithm.trim().toLowerCase());
    }

    public void seedDefaultProblems() {
        List<ProblemDefinition> existingProblems = problemRepository.findAll();
        Map<String, ProblemDefinition> existingById = new java.util.HashMap<>();
        for (ProblemDefinition p : existingProblems) {
            if (p.getProblemId() != null) {
                existingById.put(p.getProblemId(), p);
            }
        }

        List<ProblemDefinition> seeds = buildProblemDefinitionsFromFiles();
        List<ProblemDefinition> toInsert = new ArrayList<>();
        List<ProblemDefinition> toUpdate = new ArrayList<>();
        for (ProblemDefinition seed : seeds) {
            ProblemDefinition existing = existingById.get(seed.getProblemId());
            if (existing == null) {
                toInsert.add(seed);
            } else if (seed.getProblemPath() != null && !seed.getProblemPath().equals(existing.getProblemPath())) {
                existing.setProblemPath(seed.getProblemPath());
                toUpdate.add(existing);
            }
        }

        if (!toInsert.isEmpty()) {
            problemRepository.saveAll(toInsert);
        }
        if (!toUpdate.isEmpty()) {
            problemRepository.saveAll(toUpdate);
        }
    }

    private boolean shouldUseConstraints(String algorithm, Map<String, Object> constraints) {
        if (constraints == null || constraints.isEmpty()) {
            return false;
        }
        if (algorithm == null) {
            return false;
        }
        String normalized = algorithm.trim().toLowerCase();
        return GENERAL_ALGORITHMS.contains(normalized);
    }

    private String resolveTitle(ProblemDefinition problem, String requestedTitle, String algorithm) {
        if (requestedTitle != null && !requestedTitle.isBlank()) {
            return requestedTitle;
        }
        String base = problem.getProblemId() != null && !problem.getProblemId().isBlank()
                ? problem.getProblemId()
                : "problem";
        String algo = algorithm == null || algorithm.isBlank()
                ? "schedule"
                : algorithm.trim().replaceAll("\\s+", "_");
        String stamp = DateTimeFormatter.ofPattern("yyyyMMdd_HHmmss").format(LocalDateTime.now());
        return base + "_" + algo + "_" + stamp;
    }

    private List<ProblemDefinition> buildProblemDefinitionsFromFiles() {
        List<ProblemDefinition> problems = new ArrayList<>();
        Path repoRoot = resolveRepoRoot();
        if (repoRoot == null) {
            return problems;
        }

        Path problemsRoot = repoRoot.resolve("data/problems");
        if (!Files.isDirectory(problemsRoot)) {
            return problems;
        }

        List<Path> problemFiles = new ArrayList<>();
        try {
            Files.walk(problemsRoot)
                    .filter(p -> p.getFileName().toString().equals("problem.json"))
                    .forEach(problemFiles::add);
        } catch (IOException e) {
            return problems;
        }

        for (Path problemFile : problemFiles) {
            Map<String, Object> root = readProblemJson(problemFile);
            if (root == null) {
                continue;
            }
            Map<String, Object> metadata = getMap(root, "metadata");
            String problemId = getString(metadata, "problemId");
            if (problemId == null || problemId.isBlank()) {
                continue;
            }
            String relativePath = repoRoot.relativize(problemFile).toString();
            ProblemDefinition def = ProblemDefinition.builder()
                    .problemId(problemId)
                    .problemPath(relativePath)
                    .build();
            problems.add(def);
        }

        return problems;
    }

    private List<ProblemDefinition> getAllDefinitions() {
        List<ProblemDefinition> problems = problemRepository.findAll();
        if (problems.isEmpty()) {
            seedDefaultProblems();
            problems = problemRepository.findAll();
        }
        return problems;
    }

    private Path resolveProblemPath(ProblemDefinition problem) {
        if (problem == null || problem.getProblemPath() == null || problem.getProblemPath().isBlank()) {
            return null;
        }
        Path repoRoot = resolveRepoRoot();
        return repoRoot == null ? Paths.get(problem.getProblemPath()) : repoRoot.resolve(problem.getProblemPath());
    }

    private Map<String, Object> loadProblemJson(ProblemDefinition def) {
        Path problemPath = resolveProblemPath(def);
        return readProblemJson(problemPath);
    }

    private Map<String, Object> readProblemJson(Path problemPath) {
        if (problemPath == null || !Files.isRegularFile(problemPath)) {
            return null;
        }
        try {
            return objectMapper.readValue(problemPath.toFile(), Map.class);
        } catch (IOException e) {
            return null;
        }
    }

    private Map<String, Object> loadListItem(ProblemDefinition def) {
        if (def == null) {
            return null;
        }
        String defPath = def.getProblemPath();
        Map<String, Object> item = null;
        if (defPath != null && !defPath.isBlank()) {
            Path problemPath = resolveProblemPath(def);
            item = parseProblemListItem(problemPath);
        }
        if (item == null) {
            item = new LinkedHashMap<>();
        }
        Object existingId = item.get("problemId");
        if (existingId == null || String.valueOf(existingId).isBlank()) {
            item.put("problemId", def.getProblemId());
        }
        if (defPath != null && !defPath.isBlank()) {
            item.put("problemPath", defPath);
        }
        return item;
    }

    private Map<String, Object> parseProblemListItem(Path problemPath) {
        Map<String, Object> root = readProblemJson(problemPath);
        if (root == null) {
            return null;
        }
        Map<String, Object> metadata = getMap(root, "metadata");
        Map<String, Object> item = new LinkedHashMap<>();
        String problemId = getString(metadata, "problemId");
        if (problemId != null && !problemId.isBlank()) {
            item.put("problemId", problemId);
        }
        String name = getString(metadata, "name");
        if (name != null && !name.isBlank()) {
            item.put("name", name);
        }
        String description = getString(metadata, "description");
        if (description != null && !description.isBlank()) {
            item.put("description", description);
        }
        return item;
    }

    private List<Map<String, Object>> loadProblemEmployees(ProblemDefinition problem) {
        Path problemPath = resolveProblemPath(problem);
        if (problemPath == null) {
            return List.of();
        }
        return parseEmployees(problemPath);
    }

    private List<Map<String, Object>> parseEmployees(Path problemPath) {
        if (problemPath == null || !Files.isRegularFile(problemPath)) {
            return List.of();
        }
        try {
            Map<String, Object> root = objectMapper.readValue(problemPath.toFile(), Map.class);
            return extractTeamEmployees(root);
        } catch (IOException e) {
            return List.of();
        }
    }

    private List<Map<String, Object>> extractTeamEmployees(Map<String, Object> root) {
        Map<String, Object> employeesNode = getMap(root, "employees");
        if (employeesNode.isEmpty()) {
            return List.of();
        }
        String model = getString(employeesNode, "model");
        if (model != null && !model.isBlank() && !"team".equalsIgnoreCase(model)) {
            return List.of();
        }
        Object simple = employeesNode.get("simple");
        return coerceEmployeeList(simple);
    }

    @SuppressWarnings("unchecked")
    private List<Map<String, Object>> coerceEmployeeList(Object value) {
        if (!(value instanceof List<?> list)) {
            return List.of();
        }
        List<Map<String, Object>> employees = new ArrayList<>();
        for (Object item : list) {
            if (item instanceof Map<?, ?> map) {
                employees.add((Map<String, Object>) map);
            }
        }
        return employees;
    }

    private Path resolveRepoRoot() {
        Path current = Paths.get("").toAbsolutePath();
        for (int i = 0; i < 6; i++) {
            if (Files.isDirectory(current.resolve("data/problems"))) {
                return current;
            }
            if (Files.isDirectory(current.resolve("json_generation"))) {
                return current;
            }
            current = current.getParent();
            if (current == null) {
                break;
            }
        }
        return null;
    }

    private Map<String, Object> getMap(Map<String, Object> root, String key) {
        Object value = root == null ? null : root.get(key);
        if (value instanceof Map<?, ?> map) {
            return (Map<String, Object>) map;
        }
        return Map.of();
    }

    private List<String> collectDataFiles(Object node) {
        java.util.LinkedHashSet<String> files = new java.util.LinkedHashSet<>();
        collectDataFiles(node, files);
        return new ArrayList<>(files);
    }

    private void collectDataFiles(Object node, java.util.Set<String> files) {
        if (node instanceof Map<?, ?> map) {
            for (Map.Entry<?, ?> entry : map.entrySet()) {
                Object key = entry.getKey();
                Object value = entry.getValue();
                if (key instanceof String s && "dataFile".equals(s) && value instanceof String file) {
                    if (!file.isBlank()) {
                        files.add(file);
                    }
                }
                collectDataFiles(value, files);
            }
            return;
        }
        if (node instanceof List<?> list) {
            for (Object item : list) {
                collectDataFiles(item, files);
            }
        }
    }

    private List<String> resolveDataFiles(Path problemPath, List<String> dataFiles) {
        if (dataFiles == null || dataFiles.isEmpty()) {
            return List.of();
        }
        java.util.LinkedHashSet<String> resolved = new java.util.LinkedHashSet<>();
        for (String file : dataFiles) {
            String resolvedPath = resolveProblemFile(problemPath, file);
            if (resolvedPath != null && !resolvedPath.isBlank()) {
                resolved.add(resolvedPath);
            }
        }
        return new ArrayList<>(resolved);
    }

    private List<String> mergeDataFiles(List<String> primary, List<String> secondary) {
        java.util.LinkedHashSet<String> merged = new java.util.LinkedHashSet<>();
        if (primary != null) {
            merged.addAll(primary);
        }
        if (secondary != null) {
            merged.addAll(secondary);
        }
        return new ArrayList<>(merged);
    }

    private List<String> listBundleFiles(Path problemPath) {
        if (problemPath == null) {
            return List.of();
        }
        Path dir = problemPath.getParent();
        if (dir == null || !Files.isDirectory(dir)) {
            return List.of();
        }
        java.util.LinkedHashSet<String> files = new java.util.LinkedHashSet<>();
        try (java.util.stream.Stream<Path> stream = Files.list(dir)) {
            stream.filter(Files::isRegularFile)
                    .filter(p -> !p.getFileName().toString().equalsIgnoreCase("problem.json"))
                    .sorted(java.util.Comparator.comparing(p -> p.getFileName().toString().toLowerCase()))
                    .forEach(p -> {
                        String resolvedPath = resolveProblemFile(problemPath, p.getFileName().toString());
                        if (resolvedPath != null && !resolvedPath.isBlank()) {
                            files.add(resolvedPath);
                        }
                    });
        } catch (IOException e) {
            return List.of();
        }
        return new ArrayList<>(files);
    }

    private String findDataFileByKeywords(List<String> dataFiles, List<String> keywords) {
        if (dataFiles == null) {
            return null;
        }
        for (String file : dataFiles) {
            String lowerName = toLowerName(file);
            if (lowerName == null) {
                continue;
            }
            if (!lowerName.endsWith(".csv")) {
                continue;
            }
            if (containsKeyword(lowerName, keywords)) {
                return file;
            }
        }
        return null;
    }

    private String findFileInDirectory(Path problemPath, List<String> keywords) {
        if (problemPath == null) {
            return null;
        }
        Path dir = problemPath.getParent();
        if (dir == null || !Files.isDirectory(dir)) {
            return null;
        }
        try (java.util.stream.Stream<Path> stream = Files.list(dir)) {
            Optional<Path> match = stream
                    .filter(Files::isRegularFile)
                    .filter(p -> p.getFileName().toString().toLowerCase().endsWith(".csv"))
                    .filter(p -> containsKeyword(p.getFileName().toString().toLowerCase(), keywords))
                    .sorted(java.util.Comparator.comparing(p -> p.getFileName().toString().toLowerCase()))
                    .findFirst();
            if (match.isPresent()) {
                return resolveProblemFile(problemPath, match.get().getFileName().toString());
            }
        } catch (IOException e) {
            return null;
        }
        return null;
    }

    private boolean containsKeyword(String value, List<String> keywords) {
        if (value == null) {
            return false;
        }
        String lower = value.toLowerCase();
        for (String keyword : keywords) {
            if (lower.contains(keyword)) {
                return true;
            }
        }
        return false;
    }

    private String toLowerName(String pathValue) {
        if (pathValue == null || pathValue.isBlank()) {
            return null;
        }
        return Paths.get(pathValue).getFileName().toString().toLowerCase();
    }

    private TemplateNames ensureProblemTemplates(String problemId, String problemPathValue, String yearText, List<String> dataFiles) {
        if (problemId == null || problemId.isBlank()) {
            throw new IllegalStateException("Problem is missing metadata.problemId.");
        }

        List<String> bundledDataFiles = dataFiles == null ? List.of() : dataFiles;
        String vacationsFile = findDataFileByKeywords(bundledDataFiles, VACATION_KEYWORDS);
        String demandFile = findDataFileByKeywords(bundledDataFiles, DEMAND_KEYWORDS);
        String minimunsFile = findDataFileByKeywords(bundledDataFiles, MINIMUMS_KEYWORDS);
        Path problemPath = resolveAbsolutePath(problemPathValue);
        if (vacationsFile == null || vacationsFile.isBlank()) {
            vacationsFile = findFileInDirectory(problemPath, VACATION_KEYWORDS);
        }
        if (demandFile == null || demandFile.isBlank()) {
            demandFile = findFileInDirectory(problemPath, DEMAND_KEYWORDS);
        }
        if (minimunsFile == null || minimunsFile.isBlank()) {
            minimunsFile = findFileInDirectory(problemPath, MINIMUMS_KEYWORDS);
        }
        if (vacationsFile == null || vacationsFile.isBlank()) {
            throw new IllegalStateException("Problem is missing a vacations CSV in its bundle.");
        }
        if ((demandFile == null || demandFile.isBlank())
                && (minimunsFile == null || minimunsFile.isBlank())) {
            throw new IllegalStateException("Problem is missing a demand or minimuns CSV in its bundle.");
        }

        Path vacationPath = resolveAbsolutePath(vacationsFile);
        if (vacationPath == null || !Files.isRegularFile(vacationPath)) {
            throw new IllegalStateException("Problem vacations file not found: " + vacationsFile);
        }

        String vacationTemplateName = problemId + "__vacations";
        String minimunsTemplateName = problemId + "__minimuns";

        List<List<String>> vacationRows = readCsvRows(vacationPath, false);
        List<List<String>> minimunsRows = List.of();
        if (demandFile != null && !demandFile.isBlank()) {
            Path demandPath = resolveAbsolutePath(demandFile);
            if (demandPath == null || !Files.isRegularFile(demandPath)) {
                throw new IllegalStateException("Problem demand file not found: " + demandFile);
            }
            minimunsRows = buildMinimunsRowsFromDemand(demandPath, yearText);
        }
        if (minimunsRows.isEmpty() && minimunsFile != null && !minimunsFile.isBlank()) {
            Path minimunsPath = resolveAbsolutePath(minimunsFile);
            if (minimunsPath == null || !Files.isRegularFile(minimunsPath)) {
                throw new IllegalStateException("Problem minimuns file not found: " + minimunsFile);
            }
            minimunsRows = readCsvRows(minimunsPath, true);
        }
        if (minimunsRows.isEmpty()) {
            throw new IllegalStateException("Problem demand/minimuns data produced no coverage rows.");
        }

        upsertVacationTemplate(vacationTemplateName, vacationRows);
        upsertReferenceTemplate(minimunsTemplateName, minimunsRows);

        return new TemplateNames(vacationTemplateName, minimunsTemplateName);
    }

    private List<List<String>> buildMinimunsRowsFromDemand(Path demandPath, String yearText) {
        List<List<String>> demandRows = readCsvRows(demandPath, true);
        if (demandRows.isEmpty()) {
            return List.of();
        }

        Integer year = parseYear(yearText);
        if (year == null) {
            for (List<String> row : demandRows) {
                LocalDate date = parseDemandDate(row, 0);
                if (date != null) {
                    year = date.getYear();
                    break;
                }
            }
        }
        int numDays = resolveNumDays(year, demandRows);

        Map<String, Map<String, int[]>> minsByTeam = new LinkedHashMap<>();
        Map<String, Map<String, int[]>> idealsByTeam = new LinkedHashMap<>();
        LinkedHashSet<String> seenShifts = new LinkedHashSet<>();

        for (List<String> row : demandRows) {
            if (row.size() < 5) {
                continue;
            }
            LocalDate date = parseDemandDate(row, 0);
            if (date == null) {
                continue;
            }
            int dayIndex = date.getDayOfYear();
            if (dayIndex < 1 || dayIndex > numDays) {
                continue;
            }

            String shift = normalizeShiftCode(valueAt(row, 1));
            String teamCode = normalizeTeamCode(valueAt(row, 2));
            if (shift.isEmpty() || teamCode.isEmpty()) {
                continue;
            }
            seenShifts.add(shift);

            Integer minVal = parseInteger(valueAt(row, 3));
            Integer idealVal = parseInteger(valueAt(row, 4));
            if (minVal == null && idealVal == null) {
                continue;
            }
            if (minVal == null) {
                minVal = 0;
            }
            if (idealVal == null) {
                idealVal = minVal;
            }

            int[] mins = minsByTeam
                    .computeIfAbsent(teamCode, key -> new LinkedHashMap<>())
                    .computeIfAbsent(shift, key -> new int[numDays]);
            int[] ideals = idealsByTeam
                    .computeIfAbsent(teamCode, key -> new LinkedHashMap<>())
                    .computeIfAbsent(shift, key -> new int[numDays]);

            mins[dayIndex - 1] = minVal;
            ideals[dayIndex - 1] = idealVal;
        }

        if (minsByTeam.isEmpty()) {
            return List.of();
        }

        List<String> shiftOrder = buildShiftOrder(seenShifts);
        List<List<String>> rows = new ArrayList<>();

        for (Map.Entry<String, Map<String, int[]>> teamEntry : minsByTeam.entrySet()) {
            String teamCode = teamEntry.getKey();
            Map<String, int[]> teamMins = teamEntry.getValue();
            Map<String, int[]> teamIdeals = idealsByTeam.getOrDefault(teamCode, Map.of());

            for (String shift : shiftOrder) {
                int[] minValues = teamMins.get(shift);
                int[] idealValues = teamIdeals.get(shift);
                if (minValues != null) {
                    rows.add(buildMinimunsRow(teamCode, "Minimo", shift, minValues));
                }
                if (idealValues != null) {
                    rows.add(buildMinimunsRow(teamCode, "Ideal", shift, idealValues));
                }
            }

            for (String shift : teamMins.keySet()) {
                if (shiftOrder.contains(shift)) {
                    continue;
                }
                int[] minValues = teamMins.get(shift);
                int[] idealValues = teamIdeals.get(shift);
                if (minValues != null) {
                    rows.add(buildMinimunsRow(teamCode, "Minimo", shift, minValues));
                }
                if (idealValues != null) {
                    rows.add(buildMinimunsRow(teamCode, "Ideal", shift, idealValues));
                }
            }
        }

        return rows;
    }

    private int resolveNumDays(Integer year, List<List<String>> demandRows) {
        if (year != null) {
            return Year.of(year).length();
        }
        int maxDay = 0;
        for (List<String> row : demandRows) {
            LocalDate date = parseDemandDate(row, 0);
            if (date != null) {
                maxDay = Math.max(maxDay, date.getDayOfYear());
            }
        }
        return maxDay > 0 ? maxDay : 365;
    }

    private LocalDate parseDemandDate(List<String> row, int index) {
        String value = valueAt(row, index);
        if (value.isEmpty()) {
            return null;
        }
        try {
            return LocalDate.parse(value);
        } catch (DateTimeParseException e) {
            return null;
        }
    }

    private Integer parseYear(String yearText) {
        if (yearText == null || yearText.isBlank()) {
            return null;
        }
        try {
            return Integer.parseInt(yearText.trim());
        } catch (NumberFormatException e) {
            return null;
        }
    }

    private String normalizeShiftCode(String value) {
        if (value == null) {
            return "";
        }
        String shift = value.trim().toUpperCase();
        if (shift.isEmpty()) {
            return "";
        }
        if (shift.startsWith("M")) {
            return "M";
        }
        if (shift.startsWith("T")) {
            return "T";
        }
        if (shift.startsWith("N")) {
            return "N";
        }
        return shift;
    }

    private String normalizeTeamCode(String value) {
        if (value == null) {
            return "";
        }
        String trimmed = value.trim();
        if (trimmed.isEmpty()) {
            return "";
        }
        String[] parts = trimmed.split("\\s+");
        return parts[parts.length - 1].toUpperCase();
    }

    private List<String> buildShiftOrder(Set<String> seenShifts) {
        List<String> order = new ArrayList<>();
        List<String> defaultOrder = List.of("M", "T", "N");
        for (String shift : defaultOrder) {
            if (seenShifts.contains(shift)) {
                order.add(shift);
            }
        }
        for (String shift : seenShifts) {
            if (!order.contains(shift)) {
                order.add(shift);
            }
        }
        return order;
    }

    private List<String> buildMinimunsRow(String teamCode, String type, String shift, int[] values) {
        List<String> row = new ArrayList<>(values.length + 3);
        row.add("Equipa " + teamCode);
        row.add(type);
        row.add(shift);
        for (int value : values) {
            row.add(String.valueOf(value));
        }
        return row;
    }

    private Integer parseInteger(String value) {
        if (value == null) {
            return null;
        }
        String trimmed = value.trim();
        if (trimmed.isEmpty()) {
            return null;
        }
        try {
            return Integer.parseInt(trimmed);
        } catch (NumberFormatException e) {
            return null;
        }
    }

    private String valueAt(List<String> row, int index) {
        if (row == null || index < 0 || index >= row.size()) {
            return "";
        }
        return row.get(index) == null ? "" : row.get(index).trim();
    }

    private void upsertVacationTemplate(String name, List<List<String>> rows) {
        VacationTemplate template = vacationTemplateRepository.findByName(name).orElse(null);
        if (template == null) {
            template = VacationTemplate.builder()
                    .name(name)
                    .vacations(rows)
                    .build();
        } else {
            template.setVacations(rows);
        }
        vacationTemplateRepository.save(template);
    }

    private void upsertReferenceTemplate(String name, List<List<String>> rows) {
        ReferenceTemplate template = referenceTemplateRepository.findByName(name).orElse(null);
        if (template == null) {
            template = ReferenceTemplate.builder()
                    .name(name)
                    .minimuns(rows)
                    .build();
        } else {
            template.setMinimuns(rows);
        }
        referenceTemplateRepository.save(template);
    }

    private List<List<String>> readCsvRows(Path path, boolean skipHeader) {
        List<List<String>> rows = new ArrayList<>();
        try (BufferedReader reader = Files.newBufferedReader(path, StandardCharsets.UTF_8)) {
            String line;
            boolean first = true;
            while ((line = reader.readLine()) != null) {
                if (first && skipHeader) {
                    first = false;
                    continue;
                }
                String[] values = line.split(",", -1);
                List<String> row = new ArrayList<>(values.length);
                for (String value : values) {
                    row.add(value.replace("\uFEFF", "").trim());
                }
                if (!row.isEmpty()) {
                    rows.add(row);
                }
                first = false;
            }
        } catch (IOException e) {
            throw new IllegalStateException("Failed to read CSV at " + path, e);
        }
        return rows;
    }

    private String resolveProblemFile(Path problemPath, String dataFile) {
        if (dataFile == null || dataFile.isBlank()) {
            return null;
        }
        Path baseDir = problemPath == null ? null : problemPath.getParent();
        Path resolved = baseDir == null ? Paths.get(dataFile) : baseDir.resolve(dataFile);
        Path repoRoot = resolveRepoRoot();
        if (repoRoot != null) {
            Path normalized = resolved.normalize();
            if (normalized.startsWith(repoRoot)) {
                return repoRoot.relativize(normalized).toString();
            }
        }
        return resolved.normalize().toString();
    }

    private Path resolveAbsolutePath(String pathValue) {
        if (pathValue == null || pathValue.isBlank()) {
            return null;
        }
        Path path = Paths.get(pathValue);
        if (path.isAbsolute()) {
            return path.normalize();
        }
        Path repoRoot = resolveRepoRoot();
        return repoRoot == null ? path.normalize() : repoRoot.resolve(pathValue).normalize();
    }

    private static class TemplateNames {
        private final String vacationsName;
        private final String minimunsName;

        private TemplateNames(String vacationsName, String minimunsName) {
            this.vacationsName = vacationsName;
            this.minimunsName = minimunsName;
        }
    }

    private String getString(Map<String, Object> map, String key) {
        Object value = map == null ? null : map.get(key);
        return value == null ? null : String.valueOf(value);
    }

    private String resolveValue(String primary, String fallback) {
        if (primary == null || primary.isBlank()) {
            return fallback;
        }
        return primary;
    }
}
