
package smartask.api.service;

import lombok.RequiredArgsConstructor;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.stereotype.Service;
import smartask.api.dataAccess.FShandler;
import smartask.api.dataAccess.SchedulesRepository;
import smartask.api.entity.Schedule;

import java.util.List;
import java.util.stream.Collectors;

@Service
@RequiredArgsConstructor
public class SchedulesService {

    private final FShandler FShandler = new FShandler();

    @Autowired
    private SchedulesRepository repository;

    public List<String[]> readex1() {
        saveSchedule();
        return FShandler.readex1();
    }

    private Schedule saveSchedule() {
        List<String[]> rawData = FShandler.readex1();
        List<List<String>> structuredData = rawData.stream()
                .map(List::of)
                .collect(Collectors.toList());
        Schedule schedule = new Schedule(structuredData);
        return repository.save(schedule);
    }

    public List<Schedule> getAllSchedules() {
        return repository.findAll();
    }
}