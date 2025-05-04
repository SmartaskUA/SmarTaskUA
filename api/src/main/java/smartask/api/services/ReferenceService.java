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

            ArrayList<ArrayList<String>> lines = new ArrayList<>();
            Set<String> teamsInCsv = new HashSet<>();

            String headerLine = reader.readLine(); // Ignorar ou armazenar se quiser
            if (headerLine == null) throw new RuntimeException("CSV vazio");

            String line;
            while ((line = reader.readLine()) != null) {
                String[] values = line.split(",");
                if (values.length < 4) continue;

                String team = values[0].trim();
                if (!team.isEmpty()) {
                    teamsInCsv.add(team);
                }

                ArrayList<String> row = new ArrayList<>();
                for (String value : values) {
                    row.add(value.trim());
                }
                lines.add(row);
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
                    .minimuns(new ArrayList<>(lines))
                    .build();

            System.out.println("\nTemplate generated: " + template);
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
