package smartask.api.services;

import lombok.RequiredArgsConstructor;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.stereotype.Service;

import smartask.api.event.RabbitMqProducer;
import smartask.api.models.Schedule;
import smartask.api.models.VacationTemplate;
import smartask.api.models.ReferenceTemplate;
import smartask.api.models.requests.ScheduleRequest;
import smartask.api.repositories.*;

import java.util.List;
import java.util.Optional;
import java.util.Set;
import java.util.stream.Collectors;
import java.text.Normalizer;

@Service
@RequiredArgsConstructor
public class SchedulesService {

    private final FShandler FShandler = new FShandler();

    @Autowired
    private SchedulesRepository schedulerepository;

    @Autowired
    private VacationTemplateRepository vacationTemplateRepository;

    @Autowired
    private EmployeesRepository Emprepository;

    @Autowired
    private TaskStatusRepository taskStatusRepository;

    @Autowired
    private RabbitMqProducer producer;

    @Autowired 
    private ReferenceTemplateRepository referenceTemplateRepository;

    public String requestScheduleGeneration(ScheduleRequest schedule) {

        boolean exists = schedulerepository.existsByTitleAndAlgorithm(schedule.getTitle(), schedule.getAlgorithm());    


        if (exists) {
            return "Schedule with the same title and algorithm exists!";
        }

        // Validação do VacationTemplate
        Optional<VacationTemplate> optionalTemplate = vacationTemplateRepository.findByName(schedule.getVacationTemplate());

        if (optionalTemplate.isEmpty()) {
            return "Vacation template '" + schedule.getVacationTemplate() + "' not found.";
        }

        VacationTemplate template = optionalTemplate.get();
        List<List<String>> vacationRows = template.getVacations();

        // Extrair nomes de funcionários do template (primeira coluna de cada linha)
        Set<String> namesInTemplate = vacationRows.stream()
                .map(row -> row.get(0).replace("\uFEFF", "").trim())
                .collect(Collectors.toSet());

        // Carregar nomes de funcionários do banco
        Set<String> employeeNamesInDb = Emprepository.findAll().stream()
                .map(emp -> emp.getName().trim())
                .collect(Collectors.toSet());

        // Verificar existência de todos os nomes do template no banco
        for (String name : namesInTemplate) {
            if (!employeeNamesInDb.contains(name)) {
                return "Vacation template contains employee '" + name + "' who does not exist in the system.";
            }
        }

        if (schedule.getShifts() == null || (schedule.getShifts() != 2 && schedule.getShifts() != 3)) {
            return "Invalid 'shifts' value. Expected 2 or 3.";
        }

        Optional<ReferenceTemplate> refOpt =
                referenceTemplateRepository.findByName(schedule.getMinimuns());
        if (refOpt.isEmpty()) {
            return "Minimums template '" + schedule.getMinimuns() + "' not found.";
        }

        List<List<String>> minRows = refOpt.get().getMinimuns();
        Integer inferredShiftCount = inferShiftCount(minRows);
        if (inferredShiftCount == null) {
            return "Unable to infer shifts from minimums template '" + schedule.getMinimuns() + "'. " +
                   "Make sure the CSV has a 'Turno' column with values like M/T/N.";
        }

        if (!inferredShiftCount.equals(schedule.getShifts())) {
            return "Selected shifts (" + schedule.getShifts() + ") does not match minimums template '" +
                   schedule.getMinimuns() + "' (found " + inferredShiftCount + ").";
        }

        final String res = producer.requestScheduleMessage(schedule);
        return res.equals("Sent task request") ? "Sent task request" : res;
    }

    /**
     * Look at the CSV-like table and compute how many distinct shifts it defines.
     * Accepts Portuguese header 'Turno' and robustly maps values:
     *   - 'M'/'Manhã' -> M
     *   - 'T'/'Tarde' -> T
     *   - 'N'/'Noite'/'Night' -> N
     */
    private Integer inferShiftCount(List<List<String>> rows) {
        if (rows == null || rows.isEmpty()) return null;

        boolean hasM = false, hasT = false, hasN = false;

        for (List<String> r : rows) {
            if (r == null || r.size() < 3) continue;        // precisa pelo menos de 3 colunas
            String raw = (r.get(2) == null ? "" : r.get(2)).trim();
            String token = normalizeShiftToken(raw);         // "M" | "T" | "N" | ""

            if ("M".equals(token)) hasM = true;
            else if ("T".equals(token)) hasT = true;
            else if ("N".equals(token)) hasN = true;

            if (hasM && hasT && hasN) break; // já sabemos que são 3 turnos
        }

        int count = (hasM ? 1 : 0) + (hasT ? 1 : 0) + (hasN ? 1 : 0);
        return count == 0 ? null : count;
    }

    /** Normaliza o valor do campo 'Turno' para M/T/N (tolerante a acentos e palavras completas). */
    private String normalizeShiftToken(String s) {
        if (s == null) return "";
        String u = s.toUpperCase().trim();

        if (u.startsWith("M") || u.contains("MANH")) return "M";   // M, Manha/Manhã
        if (u.startsWith("T") || u.contains("TARD")) return "T";   // T, Tarde
        if (u.startsWith("N") || u.contains("NOIT") || u.contains("NIGH")) return "N"; // N, Noite, Night

        return "";
    }

    public Optional<Schedule> getByTitle(String title) {
        return schedulerepository.findByTitle(title);
    }

    public List<String[]> readex1() {
        saveSampleSchedule();
        return FShandler.readex1();
    }

    private void saveSampleSchedule() {
        List<String[]> rawData = FShandler.readex1();
        List<List<String>> structuredData = rawData.stream()
                .map(List::of)
                .collect(Collectors.toList());

        Schedule schedule = new Schedule(
                structuredData,
                "Sample", "Glutony search");
        saveSchedule(schedule);

        List<String[]> rawData2 = FShandler.readex2();
        List<List<String>> structuredData2 = rawData.stream()
                .map(List::of)
                .collect(Collectors.toList());

        Schedule schedule2 = new Schedule(
                structuredData2,
                "Sample2", "Glutony search");
        saveSchedule(schedule2);
    }

    public List<Schedule> getAllSchedules() {
        return schedulerepository.findAll();
    }

    public void saveSchedule(Schedule schedule) {
        schedulerepository.save(schedule);
    }

    public Optional<Schedule> getScheduleById(String id) {
        return schedulerepository.findById(id);
    }

    public boolean deleteScheduleById(String id) {
        Optional<Schedule> schedule = schedulerepository.findById(id);
        if (schedule.isPresent()) {
            String title = schedule.get().getTitle();

            // Deletar Schedule
            schedulerepository.deleteById(id);

            // Deletar todos os TaskStatus com mesmo title
            taskStatusRepository.deleteAllByScheduleRequest_Title(title);

            return true;
        }
        return false;
    }

    public boolean deleteScheduleByTitle(String title) {
        Optional<Schedule> schedule = schedulerepository.findByTitle(title);
        if (schedule.isPresent()) {
            // Deletar Schedule
            schedulerepository.delete(schedule.get());

            // Deletar todos os TaskStatus com mesmo title
            taskStatusRepository.deleteAllByScheduleRequest_Title(title);

            return true;
        }
        return false;
    }


    public TaskStatusRepository getTaskStatusRepository() {
        return taskStatusRepository;
    }
}
