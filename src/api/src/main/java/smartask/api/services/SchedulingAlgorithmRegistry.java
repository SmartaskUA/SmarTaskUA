package smartask.api.services;

import org.springframework.stereotype.Component;

import java.util.Collections;
import java.util.LinkedHashMap;
import java.util.Map;
import java.util.Optional;

@Component
public class SchedulingAlgorithmRegistry {

    public enum UiMode {
        PROBLEM,
        MANUAL
    }

    public enum Granularity {
        SHIFT,
        HOURS
    }

    public enum InputKind {
        CONVERTED_TEMPLATE,
        PROBLEM_BUNDLE
    }

    public static final class AlgorithmSpec {
        private final String name;
        private final UiMode uiMode;
        private final Granularity granularity;
        private final InputKind inputKind;

        public AlgorithmSpec(String name, UiMode uiMode, Granularity granularity, InputKind inputKind) {
            this.name = name;
            this.uiMode = uiMode;
            this.granularity = granularity;
            this.inputKind = inputKind;
        }

        public String getName() {
            return name;
        }

        public UiMode getUiMode() {
            return uiMode;
        }

        public Granularity getGranularity() {
            return granularity;
        }

        public InputKind getInputKind() {
            return inputKind;
        }
    }

    private final Map<String, AlgorithmSpec> algorithmsByKey;

    public SchedulingAlgorithmRegistry() {
        Map<String, AlgorithmSpec> specs = new LinkedHashMap<>();

        register(specs, "ILP General", UiMode.PROBLEM, Granularity.SHIFT, InputKind.CONVERTED_TEMPLATE);
        register(specs, "CSP General", UiMode.PROBLEM, Granularity.SHIFT, InputKind.CONVERTED_TEMPLATE);
        register(specs, "ILP_Sisqual_Hours", UiMode.PROBLEM, Granularity.HOURS, InputKind.PROBLEM_BUNDLE);

        register(specs, "hill climbing", UiMode.MANUAL, Granularity.SHIFT, InputKind.CONVERTED_TEMPLATE);
        register(specs, "linear programming", UiMode.MANUAL, Granularity.SHIFT, InputKind.CONVERTED_TEMPLATE);
        register(specs, "linear programming 2", UiMode.MANUAL, Granularity.SHIFT, InputKind.CONVERTED_TEMPLATE);
        register(specs, "ILP Engine", UiMode.MANUAL, Granularity.SHIFT, InputKind.CONVERTED_TEMPLATE);
        register(specs, "Greedy Randomized", UiMode.MANUAL, Granularity.SHIFT, InputKind.CONVERTED_TEMPLATE);
        register(specs, "Greedy Randomized + Hill Climbing", UiMode.MANUAL, Granularity.SHIFT, InputKind.CONVERTED_TEMPLATE);
        register(specs, "CSP", UiMode.MANUAL, Granularity.SHIFT, InputKind.CONVERTED_TEMPLATE);
        register(specs, "CSP Scheduling", UiMode.MANUAL, Granularity.SHIFT, InputKind.CONVERTED_TEMPLATE);
        register(specs, "CSPv2", UiMode.MANUAL, Granularity.SHIFT, InputKind.CONVERTED_TEMPLATE);
        register(specs, "CSP_ENGINE", UiMode.MANUAL, Granularity.SHIFT, InputKind.CONVERTED_TEMPLATE);
        register(specs, "GRHC_ENGINE", UiMode.MANUAL, Granularity.SHIFT, InputKind.CONVERTED_TEMPLATE);
        register(specs, "Greedy Randomized Engine", UiMode.MANUAL, Granularity.SHIFT, InputKind.CONVERTED_TEMPLATE);
        register(specs, "Heuristic Solver", UiMode.MANUAL, Granularity.SHIFT, InputKind.CONVERTED_TEMPLATE);
        register(specs, "Heuristic General", UiMode.MANUAL, Granularity.SHIFT, InputKind.CONVERTED_TEMPLATE);
        register(specs, "ilp_greedy", UiMode.MANUAL, Granularity.SHIFT, InputKind.CONVERTED_TEMPLATE);

        register(specs, "CSP_Afonso_Hours", UiMode.MANUAL, Granularity.HOURS, InputKind.CONVERTED_TEMPLATE);
        register(specs, "ILP_2", UiMode.MANUAL, Granularity.HOURS, InputKind.CONVERTED_TEMPLATE);
        register(specs, "ILP_2_Half_Intervals", UiMode.MANUAL, Granularity.HOURS, InputKind.CONVERTED_TEMPLATE);
        register(specs, "ILP_3", UiMode.MANUAL, Granularity.HOURS, InputKind.CONVERTED_TEMPLATE);
        register(specs, "ILP_3_Half_Intervals", UiMode.MANUAL, Granularity.HOURS, InputKind.CONVERTED_TEMPLATE);
        register(specs, "ILP_4", UiMode.MANUAL, Granularity.HOURS, InputKind.CONVERTED_TEMPLATE);
        register(specs, "ILP_4_Half_Intervals", UiMode.MANUAL, Granularity.HOURS, InputKind.CONVERTED_TEMPLATE);
        register(specs, "COP_1", UiMode.MANUAL, Granularity.HOURS, InputKind.CONVERTED_TEMPLATE);
        register(specs, "COP_1_Half_Intervals", UiMode.MANUAL, Granularity.HOURS, InputKind.CONVERTED_TEMPLATE);
        register(specs, "COP_2", UiMode.MANUAL, Granularity.HOURS, InputKind.CONVERTED_TEMPLATE);
        register(specs, "COP_2_Half_Intervals", UiMode.MANUAL, Granularity.HOURS, InputKind.CONVERTED_TEMPLATE);
        register(specs, "Heuristica_1", UiMode.MANUAL, Granularity.HOURS, InputKind.CONVERTED_TEMPLATE);
        register(specs, "Heuristica_Half_Intervals", UiMode.MANUAL, Granularity.HOURS, InputKind.CONVERTED_TEMPLATE);

        algorithmsByKey = Collections.unmodifiableMap(specs);
    }

    public Optional<AlgorithmSpec> find(String algorithmName) {
        if (algorithmName == null) {
            return Optional.empty();
        }
        return Optional.ofNullable(algorithmsByKey.get(normalize(algorithmName)));
    }

    public boolean isProblemAlgorithm(String algorithmName) {
        return find(algorithmName)
                .map(spec -> spec.getUiMode() == UiMode.PROBLEM)
                .orElse(false);
    }

    public boolean isManualAlgorithm(String algorithmName) {
        return find(algorithmName)
                .map(spec -> spec.getUiMode() == UiMode.MANUAL)
                .orElse(false);
    }

    private void register(
            Map<String, AlgorithmSpec> specs,
            String name,
            UiMode uiMode,
            Granularity granularity,
            InputKind inputKind
    ) {
        specs.put(normalize(name), new AlgorithmSpec(name, uiMode, granularity, inputKind));
    }

    private String normalize(String value) {
        return value == null ? "" : value.trim().toLowerCase();
    }
}
