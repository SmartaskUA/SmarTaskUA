package smartask.api.services;

import lombok.RequiredArgsConstructor;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.stereotype.Service;

import smartask.api.event.RabbitMqProducer;
import smartask.api.models.Schedule;
import smartask.api.models.VacationTemplate;
import smartask.api.models.requests.ScheduleRequest;
import smartask.api.repositories.*;

import java.util.List;
import java.util.Optional;
import java.util.Set;
import java.util.stream.Collectors;

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

    public String requestScheduleGeneration(ScheduleRequest schedule) {

        boolean exists = schedulerepository.existsByTitleAndAlgorithm(schedule.getTitle(), schedule.getAlgorithm());

        if (exists) {
            return "Schedule with the same title and algorithm exists!";
        }

        // ⛔ Validação do VacationTemplate
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

        // Verificar se quantidade de funcionários do template é igual ao do banco
        if (namesInTemplate.size() != employeeNamesInDb.size()) {
            return "Vacation template contains " + namesInTemplate.size() +
                    " employees, but the system has " + employeeNamesInDb.size() + " employees.";
        }

        // ✅ Enviar a requisição se tudo estiver certo
        final String res = producer.requestScheduleMessage(schedule);
        System.out.println("\n" + res);
        System.out.println(schedule);

        if (res.equals("Sent task request")) {
            return "Sent task request";
        }
        return res;
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

}
