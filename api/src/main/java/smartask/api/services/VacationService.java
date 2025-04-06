package smartask.api.services;

import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.stereotype.Service;
import smartask.api.models.VacationTemplate;
import smartask.api.repositories.VacationTemplateRepository;

import java.util.List;
import java.util.Map;

@Service
public class VacationService {

    @Autowired
    VacationTemplateRepository vacationTemplateRepository;

    public void newTemplate(String name, Map<String, List<String>> vacations){
        this.vacationTemplateRepository.save(VacationTemplate.builder().name(name).vacations(vacations).build());
    }

    public List<VacationTemplate> getAll(){return this.vacationTemplateRepository.findAll();}
}
