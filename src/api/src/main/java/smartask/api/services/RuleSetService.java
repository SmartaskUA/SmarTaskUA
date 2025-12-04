package smartask.api.services;

import org.springframework.stereotype.Service;

import smartask.api.models.Rule;
import smartask.api.models.RuleSet;
import smartask.api.repositories.RuleSetRepository;

import java.util.List;
import java.util.Optional;

@Service
public class RuleSetService {

    private final RuleSetRepository ruleSetRepository;

    public RuleSetService(RuleSetRepository ruleSetRepository) {
        this.ruleSetRepository = ruleSetRepository;
    }

    // Save or update ruleset
    public RuleSet saveRuleSet(RuleSet ruleSet) {
        Optional<RuleSet> existing = ruleSetRepository.findByName(ruleSet.getName());
        if (existing.isPresent()) {
            RuleSet existingSet = existing.get();
            existingSet.setRules(ruleSet.getRules());
            existingSet.setDescription(ruleSet.getDescription());
            existingSet.setUpdatedAt(java.time.Instant.now());
            return ruleSetRepository.save(existingSet);
        }
        return ruleSetRepository.save(ruleSet);
    }

    public Optional<RuleSet> updateRuleSet(String name, RuleSet ruleSet) {
        return ruleSetRepository.findByName(name).map(existing -> {
            existing.setName(ruleSet.getName());
            existing.setDescription(ruleSet.getDescription());
            existing.setRules(ruleSet.getRules());
            existing.setUpdatedAt(java.time.Instant.now());
            return ruleSetRepository.save(existing);
        });
    }

    public Optional<RuleSet> getRuleSet(String name) {
        return ruleSetRepository.findByName(name);
    }

    public List<RuleSet> getAllRuleSets() {
        return ruleSetRepository.findAll();
    }

    public void deleteRuleSet(String name) {
        ruleSetRepository.findByName(name).ifPresent(ruleSetRepository::delete);
    }

    public List<Rule> getAvailableRules() {
        // Try the "default" catalog first, then fall back to "_catalog"
        for (String catalogName : List.of("default", "_catalog")) {
            Optional<RuleSet> rs = ruleSetRepository.findByName(catalogName);
            if (rs.isPresent() && rs.get().getRules() != null) {
                return rs.get().getRules(); // full Rule JSON
            }
        }
        return List.of();
    }

}
