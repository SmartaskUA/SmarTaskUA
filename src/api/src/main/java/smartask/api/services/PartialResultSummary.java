package smartask.api.services;

import com.fasterxml.jackson.databind.ObjectMapper;

import java.io.IOException;
import java.nio.charset.StandardCharsets;
import java.nio.file.Files;
import java.nio.file.Path;
import java.time.LocalDate;
import java.time.format.DateTimeParseException;
import java.util.ArrayList;
import java.util.HashMap;
import java.util.LinkedHashMap;
import java.util.LinkedHashSet;
import java.util.List;
import java.util.Locale;
import java.util.Map;
import java.util.Optional;
import java.util.Set;
import java.util.stream.Stream;

/**
 * What a schema v4 package's partial result fixes, for the problem list.
 *
 * The result is found by content - a JSON beside the problem carrying OutRosterTeamDays - and
 * its sidecar by convention, &lt;stem&gt;_schedules.csv, as the scheduler finds them
 * (src/scheduler/problem_v4/loader.py). The scheduler applies the entries as fixed days; this
 * only counts them: distinct employee-days inside the roster and the horizon, like the v4
 * validator's rosterDaysLeft.
 */
final class PartialResultSummary {

    static final String SIDECAR_SUFFIX = "_schedules.csv";
    /** WFM's rest codes, assumed when neither the sidecar nor the menu defines the codes. */
    private static final Set<Integer> FALLBACK_REST_CODES = Set.of(1, 3, 4);

    private PartialResultSummary() {
    }

    /**
     * {file, sidecar, fixedDays, openDays, employeeDays, workedDays, restDays} for the result beside
     * `problemJson`, or empty when the package carries none. `sidecar` is null when it is missing.
     */
    @SuppressWarnings("unchecked")
    static Optional<Map<String, Object>> of(Path problemJson, Map<String, Object> problem, ObjectMapper mapper)
            throws IOException {
        Path folder = problemJson.toAbsolutePath().getParent();
        Optional<Map.Entry<Path, Map<String, Object>>> found = locateResult(folder, problemJson, mapper);
        if (found.isEmpty()) {
            return Optional.empty();
        }
        Path resultPath = found.get().getKey();
        Object list = found.get().getValue().get("OutRosterTeamDays");
        List<Object> entries = list instanceof List<?> l ? (List<Object>) l : List.of();

        Set<String> employees = employeeIds(problem);
        Set<String> days = horizon(problem);
        String stem = resultPath.getFileName().toString().replaceFirst("\\.[^.]*$", "");
        Path sidecar = folder.resolve(stem + SIDECAR_SUFFIX);
        Map<Integer, Boolean> restByCode = Files.isRegularFile(sidecar)
                ? readRestCodes(sidecar)
                : menuFile(folder, problem).map(PartialResultSummary::readRestCodesQuietly).orElse(Map.of());

        Set<String> fixed = new LinkedHashSet<>();
        int worked = 0;
        int rest = 0;
        for (Object item : entries) {
            if (!(item instanceof Map<?, ?> entry)) {
                continue;
            }
            String eid = entry.get("EmployeeCode") == null ? "" : String.valueOf(entry.get("EmployeeCode")).trim();
            String date = entry.get("Date") == null ? "" : String.valueOf(entry.get("Date"));
            String day = date.length() >= 10 ? date.substring(0, 10) : date;
            // The first entry for a day is the one that stands; a duplicate is the validator's finding.
            if (!employees.contains(eid) || !days.contains(day) || !fixed.add(eid + "|" + day)) {
                continue;
            }
            Integer code = entry.get("ScheduleCode") instanceof Number n ? n.intValue() : null;
            boolean isRest = code != null && restByCode.getOrDefault(code, FALLBACK_REST_CODES.contains(code));
            if (isRest) {
                rest++;
            } else {
                worked++;
            }
        }

        int employeeDays = employees.size() * days.size();
        Map<String, Object> summary = new LinkedHashMap<>();
        summary.put("file", resultPath.getFileName().toString());
        summary.put("sidecar", Files.isRegularFile(sidecar) ? sidecar.getFileName().toString() : null);
        summary.put("fixedDays", fixed.size());
        summary.put("openDays", Math.max(0, employeeDays - fixed.size()));
        summary.put("employeeDays", employeeDays);
        summary.put("workedDays", worked);
        summary.put("restDays", rest);
        return Optional.of(summary);
    }

    /** The one result in `folder`: a JSON other than the problem carrying OutRosterTeamDays. */
    @SuppressWarnings("unchecked")
    private static Optional<Map.Entry<Path, Map<String, Object>>> locateResult(Path folder, Path problemJson,
                                                                               ObjectMapper mapper) throws IOException {
        if (folder == null || !Files.isDirectory(folder)) {
            return Optional.empty();
        }
        List<Path> candidates;
        try (Stream<Path> files = Files.list(folder)) {
            candidates = files
                    .filter(p -> p.getFileName().toString().toLowerCase(Locale.ROOT).endsWith(".json"))
                    .filter(p -> !p.getFileName().equals(problemJson.getFileName()))
                    .sorted()
                    .toList();
        }
        for (Path candidate : candidates) {
            Object doc;
            try {
                doc = mapper.readValue(candidate.toFile(), Object.class);
            } catch (IOException e) {
                continue;    // not JSON: not a result
            }
            if (doc instanceof Map<?, ?> map && map.containsKey("OutRosterTeamDays") && !"input".equals(map.get("form"))) {
                return Optional.of(Map.entry(candidate, (Map<String, Object>) map));
            }
        }
        return Optional.empty();
    }

    private static Set<String> employeeIds(Map<String, Object> problem) {
        Set<String> ids = new LinkedHashSet<>();
        if (problem.get("employees") instanceof Map<?, ?> employees && employees.get("list") instanceof List<?> list) {
            for (Object item : list) {
                if (item instanceof Map<?, ?> employee && employee.get("id") != null) {
                    ids.add(String.valueOf(employee.get("id")).trim());
                }
            }
        }
        return ids;
    }

    /** Every date of temporalScope, start to end inclusive, as YYYY-MM-DD. */
    private static Set<String> horizon(Map<String, Object> problem) {
        Set<String> days = new LinkedHashSet<>();
        if (!(problem.get("temporalScope") instanceof Map<?, ?> scope)) {
            return days;
        }
        try {
            LocalDate start = LocalDate.parse(String.valueOf(scope.get("start")));
            LocalDate end = LocalDate.parse(String.valueOf(scope.get("end")));
            for (LocalDate d = start; !d.isAfter(end); d = d.plusDays(1)) {
                days.add(d.toString());
            }
        } catch (DateTimeParseException e) {
            // an unreadable scope counts no days; the validator reports it
        }
        return days;
    }

    private static Optional<Path> menuFile(Path folder, Map<String, Object> problem) {
        if (problem.get("schedules") instanceof Map<?, ?> schedules && schedules.get("dataFile") instanceof String name
                && !name.isBlank()) {
            Path menu = folder.resolve(name.trim()).normalize();
            return Files.isRegularFile(menu) ? Optional.of(menu) : Optional.empty();
        }
        return Optional.empty();
    }

    private static Map<Integer, Boolean> readRestCodesQuietly(Path csv) {
        try {
            return readRestCodes(csv);
        } catch (IOException e) {
            return Map.of();
        }
    }

    /**
     * {code: is a rest} from a schedules CSV (code,description,scheduleWeightMinutes,startMin,endMin).
     * A row with no window and zero weight is a rest. '#' lines and blank lines are skipped.
     */
    static Map<Integer, Boolean> readRestCodes(Path csv) throws IOException {
        Map<Integer, Boolean> out = new HashMap<>();
        List<String> header = null;
        for (String line : Files.readAllLines(csv, StandardCharsets.UTF_8)) {
            String text = line.replace("﻿", "").strip();
            if (text.isEmpty() || text.startsWith("#")) {
                continue;
            }
            List<String> cells = splitCsv(text);
            if (header == null) {
                header = cells;
                continue;
            }
            int code = header.indexOf("code");
            int weight = header.indexOf("scheduleWeightMinutes");
            int start = header.indexOf("startMin");
            if (code < 0 || code >= cells.size()) {
                continue;
            }
            try {
                int value = Integer.parseInt(cells.get(code).strip());
                String w = weight >= 0 && weight < cells.size() ? cells.get(weight).strip() : "";
                String s = start >= 0 && start < cells.size() ? cells.get(start).strip() : "";
                out.put(value, s.isEmpty() && (w.isEmpty() || Double.parseDouble(w) == 0));
            } catch (NumberFormatException e) {
                // a malformed row is the validator's finding
            }
        }
        return out;
    }

    /** A CSV line's fields; commas inside double quotes stay in the field. */
    private static List<String> splitCsv(String line) {
        List<String> fields = new ArrayList<>();
        StringBuilder field = new StringBuilder();
        boolean quoted = false;
        for (int i = 0; i < line.length(); i++) {
            char c = line.charAt(i);
            if (c == '"') {
                if (quoted && i + 1 < line.length() && line.charAt(i + 1) == '"') {
                    field.append('"');
                    i++;
                } else {
                    quoted = !quoted;
                }
            } else if (c == ',' && !quoted) {
                fields.add(field.toString());
                field.setLength(0);
            } else {
                field.append(c);
            }
        }
        fields.add(field.toString());
        return fields;
    }
}
