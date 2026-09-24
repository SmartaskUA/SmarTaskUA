import React from 'react';
import StepLayout from '../components/wizard/StepLayout';
import StepCard from '../components/wizard/StepCard';
import PriorityHierarchyEditor from '../components/rules/PriorityHierarchyEditor';
import LabourLawEditor from '../components/rules/LabourLawEditor';
import { useWizard } from '../context/WizardContext';

/**
 * Step 8: Rules — the priority hierarchy and roster-wide labour law, both
 * optional. v4.0 is the problem definition only: solver settings are not part
 * of it (FUTURE.md §6).
 */
const Step8_Rules = () => {
  const { state, updateState } = useWizard();
  return (
    <StepLayout
      stepId="rules"
      title="Rules"
      subtitle="Fill order and the labour law above the contracts. Both are optional."
    >
      <StepCard>
        <PriorityHierarchyEditor
          entries={state.priorityHierarchy}
          dimensions={state.demand.dimensions}
          onChange={(entries) => updateState('priorityHierarchy', entries)}
        />
      </StepCard>
      <StepCard>
        <LabourLawEditor
          entries={state.constraints.hard}
          scopeStart={state.temporalScope.start}
          onChange={(hard) => updateState('constraints.hard', hard)}
        />
      </StepCard>
    </StepLayout>
  );
};

export default Step8_Rules;
