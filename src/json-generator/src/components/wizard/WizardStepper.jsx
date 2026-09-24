import React from 'react';
import { Stepper, Step, StepLabel, StepButton, Box, Typography, Badge, Tooltip } from '@mui/material';
import { Warning } from '@mui/icons-material';
import { useWizard } from '../../context/WizardContext';
import { themeConfig } from '../../theme.config';
import { WIZARD_STEPS } from '../../constants/wizardSteps';

const WizardStepper = () => {
  const { state, goToStep, completeStep, findings } = useWizard();
  const { currentStep, stepCompleted = {} } = state;
  const primary = themeConfig.custom.stepperActive;

  // Leaving a step through the stepper marks it visited, like "Next" does, so
  // visited steps light up green (clean) or red (has errors).
  const handleStepClick = (index) => {
    if (index === currentStep) return;
    completeStep(currentStep);
    goToStep(index);
  };

  const icon = (step, index) => {
    const Icon = step.icon;
    const isCurrent = index === currentStep;
    const visited = !!stepCompleted[index];
    const errorCount = visited ? findings(step.id).errors.length : 0;

    let color = themeConfig.custom.stepperInactive;
    if (errorCount) color = themeConfig.error.main;
    else if (visited) color = themeConfig.custom.stepperCompleted;
    else if (isCurrent) color = primary;

    const el = (
      <Box sx={{ display: 'flex', alignItems: 'center', color, fontSize: isCurrent ? '2rem' : '1.5rem', transition: 'font-size 0.15s ease' }}>
        <Icon fontSize="inherit" />
      </Box>
    );
    if (!errorCount) return el;
    return (
      <Tooltip title={`${errorCount} validation error${errorCount === 1 ? '' : 's'}`} placement="top">
        <Badge
          badgeContent={<Warning sx={{ fontSize: 11, color: '#fff' }} />}
          sx={{ '& .MuiBadge-badge': { backgroundColor: themeConfig.error.main, minWidth: 16, height: 16, padding: 0, top: 2, right: 2 } }}
        >
          {el}
        </Badge>
      </Tooltip>
    );
  };

  return (
    <Box sx={{ width: '100%', mb: 3 }}>
      <Stepper activeStep={currentStep} alternativeLabel nonLinear sx={{ py: 2 }}>
        {WIZARD_STEPS.map((step, index) => {
          const isCurrent = index === currentStep;
          return (
            <Step key={step.id} completed={!!stepCompleted[index]}>
              <StepButton
                onClick={() => handleStepClick(index)}
                sx={{
                  py: 1.5,
                  '& .MuiStepLabel-label': {
                    fontSize: isCurrent ? '0.9rem' : '0.85rem',
                    fontWeight: isCurrent ? 700 : 400,
                    color: isCurrent ? primary : 'inherit'
                  }
                }}
              >
                <StepLabel
                  StepIconComponent={() => icon(step, index)}
                  optional={(
                    <Typography variant="caption" color={isCurrent ? primary : 'text.secondary'}>
                      {step.description}
                    </Typography>
                  )}
                >
                  {step.label}
                </StepLabel>
              </StepButton>
            </Step>
          );
        })}
      </Stepper>
    </Box>
  );
};

export default WizardStepper;
