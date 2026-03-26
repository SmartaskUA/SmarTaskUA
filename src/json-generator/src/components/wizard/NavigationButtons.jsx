import React from 'react';
import { Box, Button } from '@mui/material';
import { ArrowBack, ArrowForward, CheckCircle } from '@mui/icons-material';
import { useWizard } from '../../context/WizardContext';

/**
 * NavigationButtons - Consistent navigation buttons for wizard steps
 *
 * Provides Previous and Next buttons with proper logic
 * - Previous button hidden on first step
 * - Next button shows checkmark on last step
 * - Auto-save handled by WizardContext
 */
const NavigationButtons = ({
  onNext,
  onPrevious,
  nextDisabled = false,
  previousDisabled = false,
  nextLabel = 'Next',
  previousLabel = 'Previous'
}) => {
  const { state, goToStep, completeStep } = useWizard();
  const { currentStep } = state;

  const isFirstStep = currentStep === 0;
  const isLastStep = currentStep === 9; // 10 steps total (0-9)

  const handlePrevious = () => {
    if (onPrevious) {
      onPrevious();
    }
    goToStep(currentStep - 1);
  };

  const handleNext = async () => {
    if (onNext) {
      const canProceed = await onNext();
      if (canProceed === false) return;
    }

    // Mark current step as completed
    completeStep(currentStep);

    // Go to next step
    goToStep(currentStep + 1);
  };

  return (
    <Box
      sx={{
        display: 'flex',
        justifyContent: 'space-between',
        mt: 4,
        pt: 2,
        borderTop: '1px solid',
        borderColor: 'divider'
      }}
    >
      {/* Previous Button - Hidden on first step */}
      {!isFirstStep ? (
        <Button
          variant="outlined"
          startIcon={<ArrowBack />}
          onClick={handlePrevious}
          disabled={previousDisabled}
        >
          {previousLabel}
        </Button>
      ) : (
        <Box /> // Empty box to maintain spacing
      )}

      {/* Next/Finish Button - Always on the right */}
      <Button
        variant="contained"
        endIcon={isLastStep ? <CheckCircle /> : <ArrowForward />}
        onClick={handleNext}
        disabled={nextDisabled}
      >
        {isLastStep ? 'Generate Files' : nextLabel}
      </Button>
    </Box>
  );
};

export default NavigationButtons;
