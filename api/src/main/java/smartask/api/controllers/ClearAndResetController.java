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
}
