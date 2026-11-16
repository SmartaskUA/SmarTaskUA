package smartask.api.services;

import com.fasterxml.jackson.databind.ObjectMapper;
import org.junit.jupiter.api.Test;

import java.io.IOException;
import java.nio.file.Files;
import java.nio.file.Path;
import java.util.List;
import java.util.Map;

import static org.junit.jupiter.api.Assertions.*;
import static smartask.api.services.SchedulingAlgorithmRegistry.Granularity.V4;
import static smartask.api.services.SchedulingAlgorithmRegistry.Granularity.V4_LEGACY;

/** Plain JUnit: which v4 solvers a SISQUAL package and a converted SMARTASK package are offered. */
class SchedulingAlgorithmRegistryTest {

    private static final String LEGACY_GA = "Genetic Algorithm Legacy v4";
    private final SchedulingAlgorithmRegistry registry = new SchedulingAlgorithmRegistry();

    /** data/problems/<name>/problem.json, found by walking up from the working directory. */
    @SuppressWarnings("unchecked")
    private static Map<String, Object> problem(String name) throws IOException {
        for (Path dir = Path.of("").toAbsolutePath(); dir != null; dir = dir.getParent()) {
            Path candidate = dir.resolve("data/problems").resolve(name).resolve("problem.json");
            if (Files.isRegularFile(candidate)) {
                return new ObjectMapper().readValue(candidate.toFile(), Map.class);
            }
        }
        throw new IllegalStateException("data/problems/" + name + " not found");
    }

    @Test
    void aLegacyPackageOffersTheLegacyGaFirstThenTheV4Solvers() {
        List<String> legacy = registry.problemAlgorithms(V4_LEGACY);
        assertEquals(LEGACY_GA, legacy.get(0));
        assertTrue(legacy.containsAll(registry.problemAlgorithms(V4)));
    }

    @Test
    void aSisqualPackageIsNotOfferedTheLegacyGa() {
        assertFalse(registry.problemAlgorithms(V4).contains(LEGACY_GA));
        var spec = registry.find(LEGACY_GA).orElseThrow();
        assertFalse(registry.accepts(V4, spec));
        assertTrue(registry.accepts(V4_LEGACY, spec));
        assertTrue(registry.accepts(V4_LEGACY, registry.find("Genetic Algorithm v4").orElseThrow()));
    }

    @Test
    void theConvertedPackagesAreRecognisedAndSisqualOnesAreNot() throws IOException {
        assertTrue(ProblemService.isLegacyShiftPackage(problem("V4_SMARTASK_SIMPLE_2025")));
        assertTrue(ProblemService.isLegacyShiftPackage(problem("V4_SMARTASK_3SHIFTS_2TEAMS_2025")));
        assertFalse(ProblemService.isLegacyShiftPackage(problem("V4_C2_JANUARY_2026")));
    }
}
