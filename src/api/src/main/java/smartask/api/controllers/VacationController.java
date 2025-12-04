package smartask.api.controllers;

import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.http.HttpStatus;
import org.springframework.http.ResponseEntity;
import org.springframework.web.bind.annotation.*;
import smartask.api.models.VacationTemplate;
import smartask.api.models.requests.VacationTemplateRequest;
import smartask.api.services.VacationService;
import org.springframework.web.multipart.MultipartFile;
import java.io.IOException;
import java.util.List;

@RestController
@RequestMapping("/vacation")
public class VacationController {

    @Autowired
    private VacationService service;

    @PostMapping("/")
    public ResponseEntity<String> newTemplate(@RequestBody VacationTemplateRequest req) {
        try {
            this.service.newTemplate(req.getName(), req.getVacations());
            return ResponseEntity.ok("Template with data " + req + " created");
        } catch (IllegalArgumentException e) {
            return ResponseEntity
                    .status(HttpStatus.BAD_REQUEST)
                    .body("Invalid vacation template: " + e.getMessage());
        } catch (Exception e) {
            return ResponseEntity
                    .status(HttpStatus.INTERNAL_SERVER_ERROR)
                    .body("An unexpected error occurred: " + e.getMessage());
        }
    }

    @PostMapping("/csv/{name}")
    public ResponseEntity<String> uploadCsvAndGenerateTemplate(@PathVariable String name, @RequestParam("file") MultipartFile file) {
        try {
            // Salva o arquivo temporariamente
            String filePath = "/tmp/" + file.getOriginalFilename();
            file.transferTo(new java.io.File(filePath));

            // Processa o arquivo CSV e gera o template
            service.processCsvFileAndGenerateTemplate(name, filePath);

            return ResponseEntity.ok("Vacation template generated from CSV for " + name);

        } catch (IOException e) {
            return ResponseEntity.status(HttpStatus.INTERNAL_SERVER_ERROR).body("Error reading the file: " + e.getMessage());
        } catch (IllegalArgumentException e) {
            return ResponseEntity.status(HttpStatus.BAD_REQUEST).body("Error: " + e.getMessage());
        }
    }

    @PostMapping("/random/{name}")
    public ResponseEntity<String> newRandomTemplate(@PathVariable String name)
    {
        this.service.newRandomTemplate(name);
        return ResponseEntity.ok("New randomly generated vacation template");

    }

    @GetMapping("/")
    public ResponseEntity<List<VacationTemplate>> getTemplates(){
        return ResponseEntity.ok(
                this.service.getAll()
        );
    }

    @DeleteMapping("/{id}")
    public ResponseEntity<String> deleteTemplateById(@PathVariable String id) {
        try {
            service.deleteTemplateById(id);
            return ResponseEntity.ok("Template deletado com sucesso (ID: " + id + ")");
        } catch (Exception e) {
            return ResponseEntity.status(HttpStatus.NOT_FOUND).body("Erro ao deletar: " + e.getMessage());
        }
    }

    @DeleteMapping("/by-name/{name}")
    public ResponseEntity<String> deleteTemplateByName(@PathVariable String name) {
        try {
            service.deleteTemplateByName(name);
            return ResponseEntity.ok("Template deletado com sucesso (nome: " + name + ")");
        } catch (Exception e) {
            return ResponseEntity.status(HttpStatus.NOT_FOUND).body("Erro ao deletar: " + e.getMessage());
        }
    }

}
