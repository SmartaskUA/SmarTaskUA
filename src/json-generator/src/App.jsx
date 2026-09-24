import React, { useState } from 'react';
import { ThemeProvider } from '@mui/material/styles';
import {
  CssBaseline, Container, Box, Typography, AppBar, Toolbar, Button, Dialog, DialogTitle, DialogContent,
  DialogActions, DialogContentText, IconButton, Tooltip
} from '@mui/material';
import { RestartAlt, FolderSpecial } from '@mui/icons-material';
import { WizardProvider, useWizard } from './context/WizardContext';
import theme from './theme';
import WizardStepper from './components/wizard/WizardStepper';
import { STEP_COUNT, WIZARD_STEPS } from './constants/wizardSteps';
import ProjectManagerDialog from './components/project/ProjectManagerDialog';

import Step1_Setup from './steps/Step1_Setup';
import Step2_Contracts from './steps/Step2_Contracts';
import Step3_Dimensions from './steps/Step3_Dimensions';
import Step4_Employees from './steps/Step4_Employees';
import Step5_ScheduleInput from './steps/Step5_ScheduleInput';
import Step6_Demand from './steps/Step6_Demand';
import Step7_ShiftMenu from './steps/Step7_ShiftMenu';
import Step8_Rules from './steps/Step8_Rules';
import Step9_Review from './steps/Step9_Review';

const STEP_COMPONENTS = {
  setup: Step1_Setup,
  contracts: Step2_Contracts,
  dimensions: Step3_Dimensions,
  employees: Step4_Employees,
  scheduleInput: Step5_ScheduleInput,
  demand: Step6_Demand,
  schedules: Step7_ShiftMenu,
  rules: Step8_Rules,
  review: Step9_Review
};

const WizardContent = () => {
  const { state, resetWizard } = useWizard();
  const [resetOpen, setResetOpen] = useState(false);
  const [projectsOpen, setProjectsOpen] = useState(false);
  const step = WIZARD_STEPS[state.currentStep] || WIZARD_STEPS[0];
  const StepComponent = STEP_COMPONENTS[step.id];

  return (
    <Box sx={{ minHeight: '100vh', bgcolor: 'background.default' }}>
      <AppBar position="static" elevation={0} sx={{ borderBottom: '2px solid', borderColor: 'divider' }}>
        <Toolbar sx={{ minHeight: 64 }}>
          <Typography variant="h6" sx={{ flexGrow: 1, fontWeight: 600 }}>JSON Generator — Schema v4.0</Typography>
          <Typography variant="body2" sx={{ opacity: 0.8, mr: 2 }}>Step {state.currentStep + 1} of {STEP_COUNT}</Typography>
          <Tooltip title="Projects — save, load, import a v4 bundle">
            <IconButton color="inherit" size="small" onClick={() => setProjectsOpen(true)} sx={{ mr: 0.5 }}><FolderSpecial /></IconButton>
          </Tooltip>
          <Tooltip title="Reset — clears all data">
            <IconButton color="inherit" size="small" onClick={() => setResetOpen(true)}><RestartAlt /></IconButton>
          </Tooltip>
        </Toolbar>
      </AppBar>

      <ProjectManagerDialog open={projectsOpen} onClose={() => setProjectsOpen(false)} />

      <Dialog open={resetOpen} onClose={() => setResetOpen(false)}>
        <DialogTitle>Reset the wizard?</DialogTitle>
        <DialogContent>
          <DialogContentText>This clears everything and returns to step 1. Saved projects are kept.</DialogContentText>
        </DialogContent>
        <DialogActions>
          <Button onClick={() => setResetOpen(false)}>Cancel</Button>
          <Button onClick={() => { resetWizard(); setResetOpen(false); }} color="error" variant="contained">Reset</Button>
        </DialogActions>
      </Dialog>

      <Container maxWidth="xl" sx={{ py: 3 }}>
        <WizardStepper />
        <Box sx={{ mt: 2 }}>
          <StepComponent key={step.id} />
        </Box>
      </Container>
    </Box>
  );
};

function App() {
  return (
    <ThemeProvider theme={theme}>
      <CssBaseline />
      <WizardProvider>
        <WizardContent />
      </WizardProvider>
    </ThemeProvider>
  );
}

export default App;
