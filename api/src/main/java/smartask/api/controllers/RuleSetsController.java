package smartask.api.controllers;

import org.springframework.http.ResponseEntity;
import org.springframework.web.bind.annotation.*;

import smartask.api.models.Rule;
import smartask.api.models.RuleSet;
import smartask.api.services.RuleSetService;

import java.util.List;

@RestController
@RequestMapping("/rulesets")
public class RuleSetsController {

    private final RuleSetService ruleSetService;

    public RuleSetsController(RuleSetService ruleSetService) {
        this.ruleSetService = ruleSetService;
    }

    @GetMapping
    public ResponseEntity<List<RuleSet>> getAllRuleSets() {
        return ResponseEntity.ok(ruleSetService.getAllRuleSets());
    }

    @GetMapping("/{name}")
    public ResponseEntity<RuleSet> getRuleSet(@PathVariable String name) {
        return ruleSetService.getRuleSet(name)
                .map(ResponseEntity::ok)
                .orElse(ResponseEntity.notFound().build());
    }

    @PostMapping
    public ResponseEntity<RuleSet> saveRuleSet(@RequestBody RuleSet ruleSet) {
        return ResponseEntity.ok(ruleSetService.saveRuleSet(ruleSet));
    }

    @PutMapping("/{name}")
    public ResponseEntity<RuleSet> updateRuleSet(@PathVariable String name, @RequestBody RuleSet ruleSet) {
        return ruleSetService.updateRuleSet(name, ruleSet)
                .map(ResponseEntity::ok)
                .orElse(ResponseEntity.notFound().build());
    }

    @DeleteMapping("/{name}")
    public ResponseEntity<Void> deleteRuleSet(@PathVariable String name) {
        ruleSetService.deleteRuleSet(name);
        return ResponseEntity.noContent().build();
    }

    @GetMapping("/rules/available")
    public ResponseEntity<List<Rule>> getAvailableRules() {
        return ResponseEntity.ok(ruleSetService.getAvailableRules());
    }
}
