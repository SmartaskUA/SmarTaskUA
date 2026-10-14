package smartask.api.services;

import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.scheduling.annotation.Scheduled;
import org.springframework.stereotype.Component;
import smartask.api.models.TaskStatus;
import smartask.api.models.requests.ScheduleRequest;
import smartask.api.repositories.TaskStatusRepository;

import java.time.LocalDateTime;
import java.util.List;

/**
 * Marks tasks as STALE when the worker stopped reporting on them, so they no longer
 * show as "Queued..." / "Calculating schedule..." forever and can be cleaned up.
 *
 * If the worker does eventually report a real status, RabbitMqStatusConsumer overwrites
 * STALE with it, so a false positive corrects itself.
 */
@Component
public class StaleTaskSweeper {

    // Grace period on top of the requested maxTime before an IN_PROGRESS task counts as stuck.
    private static final long IN_PROGRESS_MARGIN_MINUTES = 30;
    // Used when the request has no usable maxTime.
    private static final long DEFAULT_MAX_TIME_MINUTES = 60;
    // Queued tasks can legitimately wait behind others, so they get a much longer window.
    private static final long PENDING_TIMEOUT_MINUTES = 24 * 60;

    @Autowired
    private TaskStatusRepository taskStatusRepository;

    @Scheduled(fixedDelay = 5 * 60 * 1000, initialDelay = 30 * 1000)
    public void markStaleTasks() {
        LocalDateTime now = LocalDateTime.now();
        List<TaskStatus> tasks = taskStatusRepository.findAll();

        for (TaskStatus task : tasks) {
            String status = task.getStatus();
            long timeoutMinutes;
            if ("IN_PROGRESS".equals(status)) {
                timeoutMinutes = requestedMaxTimeMinutes(task.getScheduleRequest()) + IN_PROGRESS_MARGIN_MINUTES;
            } else if ("PENDING".equals(status)) {
                timeoutMinutes = PENDING_TIMEOUT_MINUTES;
            } else {
                continue;
            }

            LocalDateTime lastUpdate = task.getUpdatedAt() != null ? task.getUpdatedAt() : task.getCreatedAt();
            if (lastUpdate == null || lastUpdate.plusMinutes(timeoutMinutes).isAfter(now)) {
                continue;
            }

            task.setStatus("STALE");
            task.setFailureType("STALE");
            task.setFailureSummary(
                    "No response from the worker for over " + timeoutMinutes + " minutes while "
                    + ("PENDING".equals(status) ? "queued" : "calculating") + ". The task is probably stuck."
            );
            task.setUpdatedAt(now);
            taskStatusRepository.save(task);
            System.out.println("[StaleTaskSweeper] Marked task " + task.getTaskId() + " as STALE (was " + status + ").");
        }
    }

    private long requestedMaxTimeMinutes(ScheduleRequest request) {
        if (request == null || request.getMaxTime() == null || request.getMaxTime().isBlank()) {
            return DEFAULT_MAX_TIME_MINUTES;
        }
        try {
            double minutes = Double.parseDouble(request.getMaxTime().trim());
            return minutes > 0 ? (long) Math.ceil(minutes) : DEFAULT_MAX_TIME_MINUTES;
        } catch (NumberFormatException e) {
            return DEFAULT_MAX_TIME_MINUTES;
        }
    }
}
