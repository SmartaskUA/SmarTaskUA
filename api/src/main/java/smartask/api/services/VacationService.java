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
        if (!validateVacationTemplateFormat(vacations)) {
            throw new IllegalArgumentException("Invalid vacation format. Each employee must have 30 days between 1 and 365.");
        }

        final VacationTemplate vact = VacationTemplate.builder()
                .name(name)
                .vacations(vacations)
                .build();

        this.vacationTemplateRepository.save(vact);
    }

    public List<VacationTemplate> getAll() {
        return this.vacationTemplateRepository.findAll();
    }

    public boolean validateVacationTemplateFormat(Map<String, List<String>> vacations) {
        if (vacations == null || vacations.isEmpty()) return false;

        for (Map.Entry<String, List<String>> entry : vacations.entrySet()) {
            List<String> days = entry.getValue();

            // Verifica se há exatamente 30 dias
            if (days == null || days.size() != 30) {
                return false;
            }

            // Verifica se todos os valores são numéricos entre 1 e 365
            for (String dayStr : days) {
                try {
                    int day = Integer.parseInt(dayStr);
                    if (day < 1 || day > 365) {
                        return false;
                    }
                } catch (NumberFormatException e) {
                    return false;
                }
            }
        }

        return true;
    }
}
