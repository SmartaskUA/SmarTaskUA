package smartask.api.services;

import com.fasterxml.jackson.databind.ObjectMapper;
import org.junit.jupiter.api.Test;
import org.junit.jupiter.api.io.TempDir;
import org.springframework.mock.web.MockMultipartFile;
import smartask.api.models.ProblemDefinition;

import java.io.ByteArrayInputStream;
import java.io.ByteArrayOutputStream;
import java.io.IOException;
import java.nio.charset.StandardCharsets;
import java.nio.file.Files;
import java.nio.file.Path;
import java.util.LinkedHashMap;
import java.util.Map;
import java.util.Optional;
import java.util.zip.ZipEntry;
import java.util.zip.ZipOutputStream;

import static org.junit.jupiter.api.Assertions.*;
import static org.mockito.ArgumentMatchers.any;
import static org.mockito.Mockito.*;

/** Plain JUnit (no Spring context): the upload checks and the write, against a temp folder. */
class ProblemPackageImporterTest {

    private static final ObjectMapper MAPPER = new ObjectMapper();

    private static String problem(String id, String version) {
        return """
                {"schemaVersion": "%s", "form": "input", "metadata": {"problemId": "%s"},
                 "demand": {"dataFileDays": "days.csv", "dataFilePeriods": "periods.csv", "dataFileShifts": "shifts.csv"},
                 "scheduleInput": {"dataFile": "schedule_input.csv"}}
                """.formatted(version, id);
    }

    private static Map<String, String> validPackage(String problemName, String id) {
        Map<String, String> files = new LinkedHashMap<>();
        files.put(problemName, problem(id, "4.0"));
        for (String csv : new String[]{"days.csv", "periods.csv", "shifts.csv", "schedule_input.csv"}) {
            files.put(csv, "header\n");
        }
        return files;
    }

    private static byte[] zip(Map<String, String> entries) throws IOException {
        ByteArrayOutputStream bytes = new ByteArrayOutputStream();
        try (ZipOutputStream zip = new ZipOutputStream(bytes)) {
            for (Map.Entry<String, String> e : entries.entrySet()) {
                zip.putNextEntry(new ZipEntry(e.getKey()));
                zip.write(e.getValue().getBytes(StandardCharsets.UTF_8));
                zip.closeEntry();
            }
        }
        return bytes.toByteArray();
    }

    private static Map<String, byte[]> read(Map<String, String> entries) throws IOException {
        return ProblemPackageImporter.readZip(new ByteArrayInputStream(zip(entries)), 64, 1 << 20);
    }

    private static ProblemPackageImporter.PackageRejected rejection(Runnable action) {
        return assertThrows(ProblemPackageImporter.PackageRejected.class, action::run);
    }

    @Test
    void readZipRejectsAPathThatClimbsOutOfTheFolder() {
        var e = rejection(() -> {
            try {
                read(Map.of("../evil.csv", "x"));
            } catch (IOException ex) {
                throw new RuntimeException(ex);
            }
        });
        assertTrue(e.getMessage().contains("unsafe entry name"));
    }

    @Test
    void readZipRejectsTwoFilesWithTheSameName() {
        Map<String, String> entries = new LinkedHashMap<>();
        entries.put("a/x.csv", "1");
        entries.put("b/x.csv", "2");
        var e = rejection(() -> {
            try {
                read(entries);
            } catch (IOException ex) {
                throw new RuntimeException(ex);
            }
        });
        assertTrue(e.getMessage().contains("two entries are named x.csv"));
    }

    @Test
    void readZipKeepsOnlyJsonAndCsvByBaseName() throws IOException {
        Map<String, String> entries = new LinkedHashMap<>(validPackage("problem.json", "P1"));
        entries.put("README.md", "notes");
        entries.put("__MACOSX/._problem.json", "junk");
        entries.put("nested/.DS_Store", "junk");
        Map<String, byte[]> files = read(entries);
        assertEquals(validPackage("problem.json", "P1").keySet(), files.keySet());
    }

    @Test
    void inspectNamesEveryMissingCsv() throws IOException {
        Map<String, String> entries = validPackage("problem.json", "P1");
        entries.remove("periods.csv");
        var e = rejection(() -> {
            try {
                ProblemPackageImporter.inspect(read(entries), MAPPER);
            } catch (IOException ex) {
                throw new RuntimeException(ex);
            }
        });
        assertTrue(e.getMessage().contains("missing periods.csv"));
    }

    @Test
    void inspectRejectsANonV4Problem() throws IOException {
        Map<String, String> entries = validPackage("problem.json", "P1");
        entries.put("problem.json", problem("P1", "2.2"));
        var e = rejection(() -> {
            try {
                ProblemPackageImporter.inspect(read(entries), MAPPER);
            } catch (IOException ex) {
                throw new RuntimeException(ex);
            }
        });
        assertTrue(e.getMessage().contains("must be schema v4"));
    }

    @Test
    void inspectRejectsAProblemIdThatIsNotAFolderName() throws IOException {
        for (String id : new String[]{"..", "a/b", "has space", ""}) {
            Map<String, byte[]> files = read(validPackage("problem.json", id));
            var e = rejection(() -> ProblemPackageImporter.inspect(files, MAPPER));
            assertTrue(e.getMessage().contains("metadata.problemId"), id);
        }
    }

    @Test
    void inspectWritesTheProblemAsProblemJson() throws IOException {
        var pkg = ProblemPackageImporter.inspect(read(validPackage("C2_v4.json", "C2")), MAPPER);
        assertEquals("C2", pkg.problemId());
        assertTrue(pkg.files().containsKey("problem.json"));
        assertFalse(pkg.files().containsKey("C2_v4.json"));
    }

    @Test
    void importZipStoresUnderUploadsAndRefusesADuplicateUnlessReplaced(@TempDir Path repo) throws IOException {
        ProblemService problems = mock(ProblemService.class);
        when(problems.resolveRepoRoot()).thenReturn(repo);
        when(problems.getDefinitionByProblemId("C2")).thenReturn(Optional.empty());
        when(problems.getProblemListItem("C2")).thenReturn(Optional.of(Map.of("problemId", "C2")));
        ProblemPackageImporter importer = new ProblemPackageImporter(problems);
        MockMultipartFile upload = new MockMultipartFile("file", "C2_v4.zip", "application/zip",
                zip(validPackage("problem.json", "C2")));

        assertEquals(Map.of("problemId", "C2"), importer.importZip(upload, false));
        Path stored = repo.resolve("data/problems/uploads/C2/problem.json");
        assertTrue(Files.isRegularFile(stored));
        assertTrue(Files.getPosixFilePermissions(stored.getParent())
                .contains(java.nio.file.attribute.PosixFilePermission.OTHERS_READ), "upload folder must be readable");
        verify(problems).save(argThat((ProblemDefinition d) ->
                "C2".equals(d.getProblemId()) && "data/problems/uploads/C2/problem.json".equals(d.getProblemPath())));

        ProblemDefinition uploaded = ProblemDefinition.builder().problemId("C2")
                .problemPath("data/problems/uploads/C2/problem.json").build();
        when(problems.getDefinitionByProblemId("C2")).thenReturn(Optional.of(uploaded));
        assertEquals(409, rejection(() -> importer.importZip(upload, false)).getStatus());
        assertEquals(Map.of("problemId", "C2"), importer.importZip(upload, true));

        ProblemDefinition builtIn = ProblemDefinition.builder().problemId("C2")
                .problemPath("data/problems/V4_C2/problem.json").build();
        when(problems.getDefinitionByProblemId("C2")).thenReturn(Optional.of(builtIn));
        assertEquals(409, rejection(() -> importer.importZip(upload, true)).getStatus());
        verify(problems, times(2)).save(any());
    }
}
