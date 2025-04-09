package smartask.api.services;

import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.stereotype.Service;
import smartask.api.models.Employee;
import smartask.api.models.VacationTemplate;
import smartask.api.repositories.VacationTemplateRepository;

import java.util.*;

@Service
public class VacationService {

    @Autowired
    VacationTemplateRepository vacationTemplateRepository;

    @Autowired
    EmployeeService employeeService;

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

    public void newRandomTemplate(String name){
        final VacationTemplate template = VacationTemplate.builder()
                .name(name)
                .vacations(generateRandomVacationTemplate()).build();
        vacationTemplateRepository.save(template);
    }


    public Map<String, List<String>> generateRandomVacationTemplate() {
        List<Employee> employees = employeeService.getEmployees();
        Map<String, List<String>> vacations = new HashMap<>();
        Random rand = new Random();

        for (Employee emp : employees) {
            Set<Integer> uniqueDays = new HashSet<>();
            while (uniqueDays.size() < 30) {
                int day = rand.nextInt(365) + 1; // 1 a 365
                uniqueDays.add(day);
            }

            List<Integer> sorted = new ArrayList<>(uniqueDays);
            Collections.sort(sorted); // Opcional: mantém os dias ordenados
            List<String> stringDays = sorted.stream().map(String::valueOf).toList();

            vacations.put(emp.getName(), stringDays);
        }

        return vacations;
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
