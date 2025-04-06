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
        System.out.println("\n vacations "+vacations);
        final VacationTemplate vact = VacationTemplate.builder().name(name).vacations(vacations).build();
        System.out.println(vact.getVacations());
        this.vacationTemplateRepository.save(vact);
    }

    public List<VacationTemplate> getAll(){return this.vacationTemplateRepository.findAll();}
}
