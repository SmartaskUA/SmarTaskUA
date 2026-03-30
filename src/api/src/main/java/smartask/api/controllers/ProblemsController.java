package smartask.api.controllers;

import org.springframework.http.ResponseEntity;
import org.springframework.web.bind.annotation.*;
import smartask.api.models.ProblemDefinition;
import smartask.api.models.requests.ProblemSolveRequest;
import smartask.api.models.requests.ScheduleRequest;
import smartask.api.services.ProblemService;
import smartask.api.services.SchedulesService;

import java.util.List;
import java.util.Map;
import java.util.Optional;

@RestController
@RequestMapping("/problems")
public class ProblemsController {

    private final ProblemService problemService;
    private final SchedulesService schedulesService;

    public ProblemsController(ProblemService problemService, SchedulesService schedulesService) {
        this.problemService = problemService;
        this.schedulesService = schedulesService;
    }

    @GetMapping
    public ResponseEntity<List<Map<String, Object>>> getAllProblems() {
        return ResponseEntity.ok(problemService.getAllProblemListItems());
    }

    @GetMapping("/{problemId}")
    public ResponseEntity<Map<String, Object>> getProblem(@PathVariable String problemId) {
        Optional<Map<String, Object>> problem = problemService.getProblemListItem(problemId);
        return problem.map(ResponseEntity::ok).orElse(ResponseEntity.notFound().build());
    }

    @GetMapping("/{problemId}/json")
    public ResponseEntity<Map<String, Object>> getProblemJson(@PathVariable String problemId) {
        Optional<Map<String, Object>> json = problemService.getProblemJson(problemId);
        return json.map(ResponseEntity::ok).orElse(ResponseEntity.notFound().build());
    }

    @PostMapping("/{problemId}/solve")
    public ResponseEntity<String> solveProblem(@PathVariable String problemId, @RequestBody ProblemSolveRequest request) {
        if (request.getAlgorithm() == null || request.getAlgorithm().isBlank()) {
            return ResponseEntity.badRequest().body("Missing required field: algorithm");
        }
        if (!problemService.isProblemAlgorithm(request.getAlgorithm())) {
            return ResponseEntity.badRequest().body("Unsupported algorithm for problem solve.");
        }

        Optional<ProblemDefinition> problemOpt = problemService.getDefinitionByProblemId(problemId);
        if (problemOpt.isEmpty()) {
            return ResponseEntity.notFound().build();
        }

        ScheduleRequest scheduleRequest;
        try {
            scheduleRequest = problemService.buildScheduleRequest(problemOpt.get(), request);
        } catch (IllegalStateException e) {
            return ResponseEntity.badRequest().body(e.getMessage());
        }
        String res = schedulesService.requestScheduleGeneration(scheduleRequest);

        if ("Sent task request".equals(res)) {
            return ResponseEntity.ok("Schedule generation started for problem " + problemId +
                    " with taskId " + scheduleRequest.getTaskId());
        }

        return ResponseEntity.badRequest().body("Failed to start schedule generation for problem " + problemId +
                ". Caused by: " + res);
    }
}
