import React from 'react';
import { Box, Button } from '@mui/material';
import { ArrowBack, ArrowForward, Download } from '@mui/icons-material';
import { useWizard } from '../../context/WizardContext';
import { LAST_STEP_INDEX } from '../../constants/wizardSteps';

/**
 * Previous / Next for a wizard step. `onNext` may return false (or a promise
 * of false) to stay; on the last step it is the action itself (the download).
 */
const NavigationButtons = ({
  onNext,
  onPrevious,
  nextDisabled = false,
  previousDisabled = false,
  nextLabel,
  previousLabel = 'Previous'
}) => {
  const { state, goToStep, completeStep } = useWizard();
  const { currentStep } = state;
  const isFirstStep = currentStep === 0;
  const isLastStep = currentStep === LAST_STEP_INDEX;

  const handlePrevious = () => {
    if (onPrevious) onPrevious();
    goToStep(currentStep - 1);
  };

  const handleNext = async () => {
    if (onNext) {
      const canProceed = await onNext();
      if (canProceed === false) return;
    }
    completeStep(currentStep);
    if (!isLastStep) goToStep(currentStep + 1);
  };

  return (
    <Box sx={{ display: 'flex', justifyContent: 'space-between', mt: 2, pt: 2, borderTop: '1px solid', borderColor: 'divider' }}>
      {!isFirstStep ? (
        <Button variant="outlined" startIcon={<ArrowBack />} onClick={handlePrevious} disabled={previousDisabled}>
          {previousLabel}
        </Button>
      ) : <Box />}
      <Button
        variant="contained"
        endIcon={isLastStep ? <Download /> : <ArrowForward />}
        onClick={handleNext}
        disabled={nextDisabled}
      >
        {nextLabel || (isLastStep ? 'Download ZIP' : 'Next')}
      </Button>
    </Box>
  );
};

export default NavigationButtons;
