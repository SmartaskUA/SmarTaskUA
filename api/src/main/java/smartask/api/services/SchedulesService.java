package smartask.api.services;

import lombok.RequiredArgsConstructor;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.stereotype.Service;

import smartask.api.event.RabbitMqProducer;
import smartask.api.models.Schedule;
import smartask.api.models.requests.ScheduleRequest;
import smartask.api.repositories.EmployeesRepository;
import smartask.api.repositories.FShandler;
import smartask.api.repositories.SchedulesRepository;

import java.util.List;
import java.util.Optional;
import java.util.stream.Collectors;

@Service
@RequiredArgsConstructor
public class SchedulesService {

    private final FShandler FShandler = new FShandler();

    @Autowired
    private SchedulesRepository schedulerepository;

    @Autowired
    private EmployeesRepository Emprepository;

    @Autowired
    private RabbitMqProducer producer;

    public boolean requestScheduleGeneration(ScheduleRequest schedule) {
        // ToDo: Verify if a schedule with the same configuration was already generated
        producer.requestScheduleMessage(schedule);
        System.out.println(schedule);
        return true;
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
}
