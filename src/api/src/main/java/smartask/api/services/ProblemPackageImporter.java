package smartask.api.services;

import com.fasterxml.jackson.databind.ObjectMapper;
import org.springframework.stereotype.Service;
import org.springframework.web.multipart.MultipartFile;
import smartask.api.models.ProblemDefinition;

import java.io.ByteArrayOutputStream;
import java.io.IOException;
import java.io.InputStream;
import java.nio.file.AtomicMoveNotSupportedException;
import java.nio.file.Files;
import java.nio.file.Path;
import java.nio.file.StandardCopyOption;
import java.util.ArrayList;
import java.util.Comparator;
import java.util.LinkedHashMap;
import java.util.LinkedHashSet;
import java.util.List;
import java.util.Locale;
import java.util.Map;
import java.util.Optional;
import java.util.Set;
import java.util.regex.Pattern;
import java.util.stream.Stream;
import java.util.zip.ZipEntry;
import java.util.zip.ZipException;
import java.util.zip.ZipInputStream;

/**
 * Imports a schema v4 package uploaded as a ZIP - the flat ZIP the JSON wizard downloads -
 * into data/problems/uploads/&lt;problemId&gt;/ and registers it as a problem.
 *
 * Only the package's shape is checked here (one v4 input problem, every CSV it names present);
 * the scheduler's parser validates the contents when the problem is solved.
 */
@Service
public class ProblemPackageImporter {

    public static final String UPLOADS_DIR = "data/problems/uploads";
    static final int MAX_ENTRIES = 64;
    static final long MAX_BYTES = 50L * 1024 * 1024;   // uncompressed, across all entries
    private static final Pattern PROBLEM_ID = Pattern.compile("^[A-Za-z0-9][A-Za-z0-9_.-]{0,63}$");

    /** An upload the API refuses, with the HTTP status to answer and every reason found. */
    public static class PackageRejected extends RuntimeException {
        private final int status;
        private final List<String> problems;

        public PackageRejected(int status, List<String> problems) {
            super(String.join("; ", problems));
            this.status = status;
            this.problems = List.copyOf(problems);
        }

        public int getStatus() {
            return status;
        }

        public List<String> getProblems() {
            return problems;
        }
    }

    /** A package that passed inspection: its problemId and the files to write (the problem as problem.json). */
    public record Inspected(String problemId, Map<String, byte[]> files) {
    }

    private final ProblemService problemService;
    private final ObjectMapper mapper = new ObjectMapper();

    public ProblemPackageImporter(ProblemService problemService) {
        this.problemService = problemService;
    }

    public Map<String, Object> importZip(MultipartFile file, boolean replace) {
        if (file == null || file.isEmpty()) {
            throw rejected(400, "no file uploaded (multipart field 'file')");
        }
        Map<String, byte[]> files;
        try (InputStream in = file.getInputStream()) {
            files = readZip(in, MAX_ENTRIES, MAX_BYTES);
        } catch (IOException e) {
            throw rejected(400, "could not read the upload: " + e.getMessage());
        }
        Inspected pkg = inspect(files, mapper);

        Path repoRoot = problemService.resolveRepoRoot();
        if (repoRoot == null) {
            throw rejected(500, "data/problems is not reachable from the API");
        }
        Path uploads = repoRoot.resolve(UPLOADS_DIR).normalize();
        Path target = uploads.resolve(pkg.problemId()).normalize();
        if (!uploads.equals(target.getParent())) {
            throw rejected(400, "problemId " + pkg.problemId() + " does not name a folder under " + UPLOADS_DIR);
        }

        Optional<ProblemDefinition> existing = problemService.getDefinitionByProblemId(pkg.problemId());
        if (existing.isPresent()) {
            String path = existing.get().getProblemPath();
            boolean uploaded = path != null && path.startsWith(UPLOADS_DIR + "/");
            if (!uploaded) {
                throw rejected(409, "problem " + pkg.problemId() + " is built in and cannot be replaced; "
                        + "give the package another metadata.problemId");
            }
            if (!replace) {
                throw rejected(409, "problem " + pkg.problemId() + " already exists; upload with replace=true to overwrite it");
            }
        }

        try {
            write(uploads, target, pkg.files());
        } catch (IOException e) {
            throw rejected(500, "could not store the package: " + e.getMessage());
        }
        ProblemDefinition definition = existing.orElseGet(
                () -> ProblemDefinition.builder().problemId(pkg.problemId()).build());
        definition.setProblemPath(repoRoot.relativize(target.resolve("problem.json")).toString());
        problemService.save(definition);
        return problemService.getProblemListItem(pkg.problemId()).orElseGet(Map::of);
    }

    /** Write into a temporary folder first, then move it into place, so a failed upload leaves nothing half-written. */
    private static void write(Path uploads, Path target, Map<String, byte[]> files) throws IOException {
        Files.createDirectories(uploads);
        Path staging = Files.createTempDirectory(uploads, ".tmp-");
        try {
            for (Map.Entry<String, byte[]> entry : files.entrySet()) {
                Files.write(staging.resolve(entry.getKey()), entry.getValue());
            }
            deleteRecursively(target);
            try {
                Files.move(staging, target, StandardCopyOption.ATOMIC_MOVE);
            } catch (AtomicMoveNotSupportedException e) {
                Files.move(staging, target);
            }
        } finally {
            deleteRecursively(staging);
        }
    }

    private static void deleteRecursively(Path path) throws IOException {
        if (!Files.exists(path)) {
            return;
        }
        try (Stream<Path> walk = Files.walk(path)) {
            for (Path p : walk.sorted(Comparator.reverseOrder()).toList()) {
                Files.delete(p);
            }
        }
    }

    // ------------------------------------------------------------------
    // pure checks (unit-tested)
    // ------------------------------------------------------------------

    /**
     * {file name: bytes} for the .json and .csv entries of a ZIP, by base name.
     * Folders, __MACOSX, dotfiles and other file types (a README) are ignored; a ".."
     * path segment, a repeated file name, or too many or too large entries reject it.
     */
    static Map<String, byte[]> readZip(InputStream in, int maxEntries, long maxBytes) throws IOException {
        Map<String, byte[]> files = new LinkedHashMap<>();
        List<String> problems = new ArrayList<>();
        int entries = 0;
        long total = 0;
        try (ZipInputStream zip = new ZipInputStream(in)) {
            ZipEntry entry;
            while ((entry = zip.getNextEntry()) != null) {
                if (++entries > maxEntries) {
                    throw rejected(400, "the ZIP holds more than " + maxEntries + " entries");
                }
                String raw = entry.getName().replace('\\', '/');
                if (entry.isDirectory() || raw.startsWith("__MACOSX/") || raw.contains("/__MACOSX/")) {
                    continue;
                }
                if (List.of(raw.split("/")).contains("..")) {
                    problems.add("unsafe entry name " + raw);
                    continue;
                }
                String name = raw.substring(raw.lastIndexOf('/') + 1);
                String lower = name.toLowerCase(Locale.ROOT);
                if (name.isEmpty() || name.startsWith(".") || !(lower.endsWith(".json") || lower.endsWith(".csv"))) {
                    continue;
                }
                if (files.containsKey(name)) {
                    problems.add("two entries are named " + name);
                    continue;
                }
                byte[] data = readCapped(zip, maxBytes - total);
                total += data.length;
                files.put(name, data);
            }
        } catch (ZipException e) {
            throw rejected(400, "not a readable ZIP archive: " + e.getMessage());
        }
        if (!problems.isEmpty()) {
            throw new PackageRejected(400, problems);
        }
        if (files.isEmpty()) {
            throw rejected(400, "the upload holds no .json or .csv files - is it the ZIP the JSON wizard downloads?");
        }
        return files;
    }

    private static byte[] readCapped(InputStream in, long budget) throws IOException {
        ByteArrayOutputStream out = new ByteArrayOutputStream();
        byte[] buffer = new byte[8192];
        int n;
        while ((n = in.read(buffer)) != -1) {
            if (out.size() + n > budget) {
                throw rejected(400, "the ZIP unpacks to more than " + (MAX_BYTES / (1024 * 1024)) + " MB");
            }
            out.write(buffer, 0, n);
        }
        return out.toByteArray();
    }

    /** Check the package's shape: one v4 input problem, a safe problemId, every CSV it names present. */
    @SuppressWarnings("unchecked")
    static Inspected inspect(Map<String, byte[]> files, ObjectMapper mapper) {
        List<String> problems = new ArrayList<>();
        String problemName = null;
        Map<String, Object> problem = null;
        int results = 0;
        for (Map.Entry<String, byte[]> entry : files.entrySet()) {
            if (!entry.getKey().toLowerCase(Locale.ROOT).endsWith(".json")) {
                continue;
            }
            Object doc;
            try {
                doc = mapper.readValue(entry.getValue(), Object.class);
            } catch (IOException e) {
                problems.add(entry.getKey() + " is not valid JSON");
                continue;
            }
            if (!(doc instanceof Map<?, ?> map)) {
                continue;
            }
            if ("input".equals(map.get("form"))) {
                if (problemName != null) {
                    problems.add("more than one input problem: " + problemName + " and " + entry.getKey());
                    continue;
                }
                problemName = entry.getKey();
                problem = (Map<String, Object>) map;
            } else if (map.containsKey("OutRosterTeamDays")) {
                results++;
            }
        }
        if (problem == null) {
            problems.add("no input problem in the upload (a JSON with \"form\": \"input\")");
            throw new PackageRejected(400, problems);
        }
        if (results > 1) {
            problems.add("a package carries at most one result, this one has " + results);
        }
        if (!"4.0".equals(String.valueOf(problem.get("schemaVersion")))) {
            problems.add("schemaVersion is " + problem.get("schemaVersion") + "; uploads must be schema v4 (\"4.0\") packages");
        }
        Object metadata = problem.get("metadata");
        Object idValue = metadata instanceof Map<?, ?> m ? m.get("problemId") : null;
        String problemId = idValue == null ? null : String.valueOf(idValue);
        if (problemId == null || !PROBLEM_ID.matcher(problemId).matches()) {
            problems.add("metadata.problemId " + (problemId == null ? "is missing" : "'" + problemId + "' is not usable")
                    + ": use letters, digits, '_', '-' or '.', starting with a letter or digit, at most 64 characters");
        }
        for (String dataFile : dataFileNames(problem)) {
            if (dataFile.contains("/") || dataFile.contains("\\")) {
                problems.add(dataFile + ": an uploaded package names its CSVs by plain file name");
            } else if (!files.containsKey(dataFile)) {
                problems.add("missing " + dataFile + " (named by " + problemName + ")");
            }
        }
        if (!problemName.equals("problem.json") && files.containsKey("problem.json")) {
            problems.add("problem.json is not the input problem (" + problemName + " is)");
        }
        if (!problems.isEmpty()) {
            throw new PackageRejected(400, problems);
        }

        Map<String, byte[]> toWrite = new LinkedHashMap<>();
        for (Map.Entry<String, byte[]> entry : files.entrySet()) {
            // The seeder looks for problem.json; everything else keeps its name,
            // since a result's sidecar is found by the result's stem.
            toWrite.put(entry.getKey().equals(problemName) ? "problem.json" : entry.getKey(), entry.getValue());
        }
        return new Inspected(problemId, toWrite);
    }

    /** Every file a problem names, under any key starting with "dataFile" (dataFileDays, scheduleInput.dataFile, ...). */
    static Set<String> dataFileNames(Object node) {
        Set<String> names = new LinkedHashSet<>();
        collectDataFileNames(node, names);
        return names;
    }

    private static void collectDataFileNames(Object node, Set<String> names) {
        if (node instanceof Map<?, ?> map) {
            for (Map.Entry<?, ?> entry : map.entrySet()) {
                if (String.valueOf(entry.getKey()).startsWith("dataFile") && entry.getValue() instanceof String value
                        && !value.isBlank()) {
                    names.add(value.trim());
                } else {
                    collectDataFileNames(entry.getValue(), names);
                }
            }
        } else if (node instanceof List<?> list) {
            for (Object item : list) {
                collectDataFileNames(item, names);
            }
        }
    }

    private static PackageRejected rejected(int status, String message) {
        return new PackageRejected(status, List.of(message));
    }
}
