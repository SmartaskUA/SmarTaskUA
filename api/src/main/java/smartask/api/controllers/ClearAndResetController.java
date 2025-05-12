package smartask.api.controllers;

import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.web.bind.annotation.*;
import smartask.api.services.ClearAndResetService;

@RestController
@RequestMapping("clearnreset/")
public class ClearAndResetController {

    @Autowired
    private ClearAndResetService service;

    /**
     * Endpoint para apagar e resetar os dados de funcionários e equipes.
     */
    @PostMapping("reset-employees-teams")
    public String resetEmployeesAndTeams() {
        service.clearAndResetData();
        return "Dados de funcionários e equipes foram resetados com sucesso.";
    }

    /**
     * Endpoint para deletar todos os documentos da coleção "schedules".
     */
    @DeleteMapping("delete-schedules")
    public String deleteAllSchedules() {
        service.deleteAllSchedules();
        return "Todos os documentos da coleção 'schedules' foram deletados com sucesso.";
    }

    @DeleteMapping("delete-reference-templates")
    public String deleteAllReferenceTemplates() {
        service.deleteAllReferenceTemplates();
        return "Todos os documentos da coleção 'reference' foram deletados com sucesso.";
    }

    /**
     * Endpoint para deletar todos os documentos da coleção "vacations".
     */
    @DeleteMapping("delete-vacation-templates")
    public String deleteAllVacationTemplates() {
        service.deleteAllVacationTemplates();
        return "Todos os documentos da coleção 'vacations' foram deletados com sucesso.";
    }




}
