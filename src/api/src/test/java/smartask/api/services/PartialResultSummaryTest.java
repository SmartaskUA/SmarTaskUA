package smartask.api.services;

import com.fasterxml.jackson.databind.ObjectMapper;
import org.junit.jupiter.api.Test;
import org.junit.jupiter.api.io.TempDir;

import java.io.IOException;
import java.nio.file.Files;
import java.nio.file.Path;
import java.util.Map;
import java.util.Optional;
import java.util.stream.Stream;

import static org.junit.jupiter.api.Assertions.*;

/** Plain JUnit: the partial-result summary against the v4 sample packages in data/problems. */
class PartialResultSummaryTest {

    private static final ObjectMapper MAPPER = new ObjectMapper();

    /** data/problems/<name>, found by walking up from the working directory (src/api under Maven). */
    private static Path sample(String name) {
        for (Path dir = Path.of("").toAbsolutePath(); dir != null; dir = dir.getParent()) {
            Path candidate = dir.resolve("data/problems").resolve(name);
            if (Files.isDirectory(candidate)) {
                return candidate;
            }
        }
        throw new IllegalStateException("data/problems/" + name + " not found above " + Path.of("").toAbsolutePath());
    }

    @SuppressWarnings("unchecked")
    private static Optional<Map<String, Object>> summarise(Path folder) throws IOException {
        Path problem = folder.resolve("problem.json");
        return PartialResultSummary.of(problem, MAPPER.readValue(problem.toFile(), Map.class), MAPPER);
    }

    private static Path copy(Path from, Path to) throws IOException {
        Files.createDirectories(to);
        try (Stream<Path> files = Files.list(from)) {
            for (Path file : files.toList()) {
                Files.copy(file, to.resolve(file.getFileName()));
            }
        }
        return to;
    }

    @Test
    void countsThePartialSamplesFixedAndOpenDays() throws IOException {
        Map<String, Object> summary = summarise(sample("V4_C2_JANUARY_2026_PARTIAL")).orElseThrow();
        assertEquals("result.json", summary.get("file"));
        assertEquals("result_schedules.csv", summary.get("sidecar"));
        assertEquals(105, summary.get("fixedDays"));
        assertEquals(360, summary.get("openDays"));
        assertEquals(465, summary.get("employeeDays"));
        assertEquals(55, summary.get("workedDays"));
        assertEquals(50, summary.get("restDays"));
    }

    @Test
    void aPackageWithoutAResultHasNoSummary() throws IOException {
        assertTrue(summarise(sample("V4_C2_JANUARY_2026")).isEmpty());
    }

    @Test
    void withoutItsSidecarTheCodesComeFromTheMenu(@TempDir Path tmp) throws IOException {
        Path pkg = copy(sample("V4_C2_JANUARY_2026_PARTIAL"), tmp.resolve("pkg"));
        Files.delete(pkg.resolve("result_schedules.csv"));
        Map<String, Object> summary = summarise(pkg).orElseThrow();
        assertNull(summary.get("sidecar"));
        assertEquals(105, summary.get("fixedDays"));
        assertEquals(50, summary.get("restDays"));
    }

    @Test
    void withNeitherSidecarNorMenuTheWfmRestCodesApply(@TempDir Path tmp) throws IOException {
        Path pkg = copy(sample("V4_C2_JANUARY_2026_PARTIAL"), tmp.resolve("pkg"));
        Files.delete(pkg.resolve("result_schedules.csv"));
        Files.delete(pkg.resolve("schedules.csv"));
        Map<String, Object> summary = summarise(pkg).orElseThrow();
        assertEquals(55, summary.get("workedDays"));
        assertEquals(50, summary.get("restDays"));    // every rest in the sample is code 3
    }

    @Test
    void readsRestCodesFromACommentedSchedulesCsv(@TempDir Path tmp) throws IOException {
        Path csv = tmp.resolve("result_schedules.csv");
        Files.writeString(csv, "# notes\n\ncode,description,scheduleWeightMinutes,startMin,endMin\n"
                + "3,Day off,0,,\n9001,\"09:00-13:00, morning\",240,540,780\n");
        assertEquals(Map.of(3, true, 9001, false), PartialResultSummary.readRestCodes(csv));
    }
}
