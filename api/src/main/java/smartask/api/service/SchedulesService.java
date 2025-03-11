package smartask.api.service;

import lombok.NoArgsConstructor;
import org.springframework.stereotype.Service;
import smartask.api.dataAccess.FShandler;
import smartask.api.dataAccess.SchedulesRepository;

import java.util.List;

@Service
@NoArgsConstructor
public class SchedulesService {

    private final FShandler repo = new FShandler();

    public List<String[]> readex1(){
        return  repo.readex1();
    }
}
