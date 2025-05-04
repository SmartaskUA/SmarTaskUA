package smartask.api.controllers;

import io.swagger.v3.oas.annotations.Operation;
import lombok.RequiredArgsConstructor;
import org.springframework.http.ResponseEntity;
import org.springframework.web.bind.annotation.*;
import org.springframework.web.multipart.MultipartFile;
import smartask.api.models.ReferenceTemplate;
import smartask.api.services.ReferenceService;

import java.util.List;

@RestController
@RequestMapping("reference/")
@RequiredArgsConstructor
public class ReferenceController {

    private final ReferenceService referenceService;

    @Operation(summary = "Criar novo template de referência a partir de CSV")
    @PostMapping("create")
    public ResponseEntity<ReferenceTemplate> createTemplate(
            @RequestParam("name") String name,
            @RequestParam("file") MultipartFile file
    ) {
        ReferenceTemplate created = referenceService.createTemplateFromCsv(name, file);
        return ResponseEntity.ok(created);
    }

    @Operation(summary = "Listar todos os templates de referência")
    @GetMapping
    public ResponseEntity<List<ReferenceTemplate>> getAllTemplates() {
        return ResponseEntity.ok(referenceService.getAllTemplates());
    }

    @Operation(summary = "Buscar template de referência por ID")
    @GetMapping("{id}")
    public ResponseEntity<ReferenceTemplate> getTemplateById(@PathVariable String id) {
        return ResponseEntity.ok(referenceService.getTemplateById(id));
    }

    @Operation(summary = "Atualizar template de referência existente por ID")
    @PutMapping("{id}")
    public ResponseEntity<ReferenceTemplate> updateTemplate(
            @PathVariable String id,
            @RequestBody ReferenceTemplate updated
    ) {
        return ResponseEntity.ok(referenceService.updateTemplate(id, updated));
    }

    @Operation(summary = "Excluir template de referência por ID")
    @DeleteMapping("{id}")
    public ResponseEntity<Void> deleteTemplate(@PathVariable String id) {
        referenceService.deleteTemplate(id);
        return ResponseEntity.noContent().build();
    }
}
