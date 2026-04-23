import React from 'react';
import {
  Stepper,
  Step,
  StepLabel,
  StepButton,
  Box,
  Typography,
  Badge,
  Tooltip as MuiTooltip
} from '@mui/material';
import { Warning } from '@mui/icons-material';
import { useWizard } from '../../context/WizardContext';
import { themeConfig } from '../../theme.config';
import { VISIBLE_STEPS } from '../../constants/wizardSteps';
import { validateStep } from '../../utils/validators/stepValidators';

const WizardStepper = () => {
  const { state, goToStep } = useWizard();
  const { currentStep, stepCompleted } = state;

  const primary = themeConfig.custom.stepperActive;

  // Map real step index to visible index (-1 when on a hidden step)
  const visibleIndex = VISIBLE_STEPS.findIndex(s => s.realIndex === currentStep);
  const activeVisibleStep = visibleIndex >= 0 ? visibleIndex : -1;

  // For completed steps, check validation errors to show indicator
  const stepHasErrors = (realIndex) => {
    if (!stepCompleted[realIndex]) return false;
    const result = validateStep(realIndex, state);
    return !result.valid;
  };

  const getStepIcon = (realIndex, isCurrent) => {
    const Icon = VISIBLE_STEPS.find(s => s.realIndex === realIndex)?.icon;
    if (!Icon) return null;

    const isCompleted = stepCompleted[realIndex];
    const hasErrors = stepHasErrors(realIndex);

    let color = themeConfig.custom.stepperInactive;
    if (hasErrors) color = '#d32f2f'; // error red
    else if (isCompleted) color = themeConfig.custom.stepperCompleted;
    else if (isCurrent) color = primary;

    const iconEl = (
      <Box
        sx={{
          display: 'flex',
          alignItems: 'center',
          color,
          fontSize: isCurrent ? '2rem' : '1.5rem',
          transition: 'font-size 0.15s ease'
        }}
      >
        <Icon fontSize="inherit" />
      </Box>
    );

    if (hasErrors) {
      return (
        <MuiTooltip title="This step has validation errors" placement="top">
          <Badge
            badgeContent={<Warning sx={{ fontSize: 11, color: '#fff' }} />}
            sx={{
              '& .MuiBadge-badge': {
                backgroundColor: '#d32f2f',
                minWidth: 16,
                height: 16,
                padding: 0,
                top: 2,
                right: 2
              }
            }}
          >
            {iconEl}
          </Badge>
        </MuiTooltip>
      );
    }

    return iconEl;
  };

  return (
    <Box sx={{ width: '100%', mb: 4 }}>
      <Stepper activeStep={activeVisibleStep} alternativeLabel nonLinear sx={{ py: 2 }}>
        {VISIBLE_STEPS.map((step) => {
          const { realIndex } = step;
          const isCompleted = stepCompleted[realIndex];
          const isCurrent  = realIndex === currentStep;

          return (
            <Step key={step.label} completed={isCompleted}>
              <StepButton
                onClick={() => { if (realIndex !== currentStep) goToStep(realIndex); }}
                sx={{
                  py: 1.5,
                  '& .MuiStepLabel-label': {
                    fontSize: isCurrent ? '0.9rem' : '0.875rem',
                    fontWeight: isCurrent ? 700 : 400,
                    color: isCurrent ? primary : 'inherit'
                  }
                }}
              >
                <StepLabel
                  StepIconComponent={() => getStepIcon(realIndex, isCurrent)}
                  optional={
                    <Typography variant="caption" color={isCurrent ? primary : 'text.secondary'}>
                      {step.description}
                    </Typography>
                  }
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
