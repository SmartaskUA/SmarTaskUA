package smartask.api.services;

import lombok.RequiredArgsConstructor;
import org.springframework.stereotype.Service;
import org.springframework.web.multipart.MultipartFile;
import smartask.api.models.ReferenceTemplate;
import smartask.api.models.Team;
import smartask.api.repositories.ReferenceTemplateRepository;

import java.io.BufferedReader;
import java.io.InputStreamReader;
import java.nio.charset.StandardCharsets;
import java.util.*;

@Service
@RequiredArgsConstructor
public class ReferenceService {

    private final ReferenceTemplateRepository repository;
    private final TeamService teamService;

    public ReferenceTemplate createTemplateFromCsv(String name, MultipartFile file) {
        try (BufferedReader reader = new BufferedReader(
                new InputStreamReader(file.getInputStream(), StandardCharsets.UTF_8))) {

            Map<String, List<String>> dataMap = new HashMap<>();
            Set<String> teamsInCsv = new HashSet<>();

            String headerLine = reader.readLine(); // header
            if (headerLine == null) throw new RuntimeException("CSV vazio");

            String[] headers = headerLine.split(",");

            String line;
            String currentTeam = null;

            while ((line = reader.readLine()) != null) {
                String[] values = line.split(",");
                if (values.length < 4) continue;

                if (!values[0].isBlank()) {
                    currentTeam = values[0].trim();
                }

                if (currentTeam == null) {
                    throw new RuntimeException("Equipa não especificada em uma linha");
                }

                teamsInCsv.add(currentTeam);

                String tipo = values[1].trim();     // "Minimo" ou "Ideal"
                String turno = values[2].trim();    // "M" ou "T"

                String key = currentTeam + "-" + tipo + "-" + turno;
                List<String> diaList = new ArrayList<>();

                for (int i = 3; i < values.length; i++) {
                    diaList.add(values[i].trim());
                }

                dataMap.put(key, diaList);
            }

            // Validação das equipas
            List<Team> existingTeams = teamService.getTeams();
            Set<String> existingTeamNames = new HashSet<>();
            for (Team t : existingTeams) {
                existingTeamNames.add(t.getName());
            }

            for (String teamName : teamsInCsv) {
                if (!existingTeamNames.contains(teamName)) {
                    throw new IllegalArgumentException("Equipa inexistente no sistema: " + teamName);
                }
            }

            ReferenceTemplate template = ReferenceTemplate.builder()
                    .name(name)
                    .minimuns(dataMap)
                    .build();

            return repository.save(template);

        } catch (Exception e) {
            throw new RuntimeException("Erro ao processar CSV: " + e.getMessage(), e);
        }
    }

    public List<ReferenceTemplate> getAllTemplates() {
        return repository.findAll();
    }

    public ReferenceTemplate getTemplateById(String id) {
        return repository.findById(id)
                .orElseThrow(() -> new NoSuchElementException("Template não encontrado com ID: " + id));
    }

    public ReferenceTemplate updateTemplate(String id, ReferenceTemplate updated) {
        ReferenceTemplate existing = getTemplateById(id);
        existing.setName(updated.getName());
        existing.setMinimuns(updated.getMinimuns());
        return repository.save(existing);
    }

    public void deleteTemplate(String id) {
        repository.deleteById(id);
    }
}
