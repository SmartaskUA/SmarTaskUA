package smartask.api.services;

import org.apache.commons.csv.CSVFormat;
import org.apache.commons.csv.CSVParser;
import org.apache.commons.csv.CSVRecord;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.stereotype.Service;
import smartask.api.models.Employee;
import smartask.api.models.VacationTemplate;
import smartask.api.repositories.EmployeesRepository;
import smartask.api.repositories.VacationTemplateRepository;

import java.io.FileReader;
import java.io.IOException;
import java.util.*;

@Service
public class VacationService {

    @Autowired
    VacationTemplateRepository vacationTemplateRepository;

    @Autowired
    EmployeeService employeeService;

    @Autowired
    EmployeesRepository employeeRepository;

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

    public void processCsvFileAndGenerateTemplate(String name, String filePath) throws IOException {
        Map<String, List<String>> vacations = new HashMap<>();

        // Ler o CSV
        try (FileReader reader = new FileReader(filePath);
             CSVParser csvParser = new CSVParser(reader, CSVFormat.DEFAULT.withHeader())) {

            for (CSVRecord record : csvParser) {
                String employeeName = record.get(0); // Nome do funcionário
                Employee employee = employeeRepository.findByName(employeeName)
                        .orElseThrow(() -> new IllegalArgumentException("Employee " + employeeName + " not found in the database."));


                List<String> vacationDays = new ArrayList<>();
                // Para cada coluna (exceto a primeira), verifica se é 1 (férias)
                for (int i = 1; i < record.size(); i++) {
                    String dayStatus = record.get(i);
                    if (dayStatus.equals("1")) {
                        vacationDays.add(String.valueOf(i)); // O dia de férias será o número da coluna
                    }
                }

                // Verifica se o funcionário tem férias válidas (30 dias)
                if (vacationDays.size() != 30) {
                    throw new IllegalArgumentException("Employee " + employeeName + " must have exactly 30 vacation days.");
                }

                vacations.put(employeeName, vacationDays);
            }
        }

        // Criar o template de férias
        VacationTemplate template = VacationTemplate.builder()
                .name(name)
                .vacations(vacations)
                .build();

        // Salvar o template de férias no banco de dados
        vacationTemplateRepository.save(template);
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
