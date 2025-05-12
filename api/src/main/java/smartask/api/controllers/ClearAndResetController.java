package smartask.api.controllers;

import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.web.bind.annotation.*;
import smartask.api.services.ClearAndResetService;
import io.swagger.v3.oas.annotations.Operation;
import io.swagger.v3.oas.annotations.tags.Tag;

@RestController
@RequestMapping("clearnreset/")
@Tag(name = "Clear and Reset", description = "Endpoints to clear or reset internal system data for testing or maintenance purposes")
public class ClearAndResetController {

    @Autowired
    private ClearAndResetService service;

    @Operation(
            summary = "Reset employees and teams",
            description = "Deletes all current employees and teams, and recreates a default setup with teams 'Equipa A' and 'Equipa B' and 12 employees."
    )
    @PostMapping("reset-employees-teams")
    public String resetEmployeesAndTeams() {
        service.clearAndResetData();
        return "Dados de funcionários e equipes foram resetados com sucesso.";
    }

    @Operation(
            summary = "Delete all schedules",
            description = "Removes all documents from the 'schedules' collection in the database."
    )
    @DeleteMapping("clean-schedules")
    public String deleteAllSchedules() {
        service.deleteAllSchedules();
        return "Todos os documentos da coleção 'schedules' foram deletados com sucesso.";
    }

    @Operation(
            summary = "Delete all reference(minimuns and ideals) templates",
            description = "Removes all documents from the 'reference templates' collection in the database."
    )
    @DeleteMapping("clean-reference-templates")
    public String deleteAllReferenceTemplates() {
        service.deleteAllReferenceTemplates();
        return "Todos os documentos da coleção 'reference' foram deletados com sucesso.";
    }


    @Operation(
            summary = "Delete all vacation templates",
            description = "Removes all documents from the 'vacations' collection in the database."
    )
    @DeleteMapping("clean-vacation-templates")
    public String deleteAllVacationTemplates() {
        service.deleteAllVacationTemplates();
        return "Todos os documentos da coleção 'vacations' foram deletados com sucesso.";
    }




}
