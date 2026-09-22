import React, { useState } from 'react';
import { ThemeProvider } from '@mui/material/styles';
import {
  CssBaseline, Container, Box, Typography, AppBar, Toolbar,
  Button, Dialog, DialogTitle, DialogContent, DialogActions, DialogContentText, IconButton, Tooltip
} from '@mui/material';
import { RestartAlt, FolderSpecial } from '@mui/icons-material';
import { WizardProvider, useWizard } from './context/WizardContext';
import theme from './theme';
import WizardStepper from './components/wizard/WizardStepper';
import { getVisibleStepNumber, TOTAL_VISIBLE } from './constants/wizardSteps';
import ProjectManagerDialog from './components/project/ProjectManagerDialog';

// Import steps
import Step1_Setup from './steps/Step1_Setup';
import Step2_Contracts from './steps/Step2_Contracts';
import Step3_OrganizationalUnits from './steps/Step3_OrganizationalUnits';
import Step4_Employees from './steps/Step4_Employees';
import Step5_ScheduleInput from './steps/Step5_ScheduleInput';
import Step6_WorkPeriods from './steps/Step6_WorkPeriods';
import Step7_Demand from './steps/Step7_Demand';
import Step8_Constraints from './steps/Step8_Constraints';
import Step9_Optimization from './steps/Step9_Optimization';
import Step10_ReviewGenerate from './steps/Step10_ReviewGenerate';

/**
 * Main Wizard Component
 */
const WizardContent = () => {
  const { state, resetWizard } = useWizard();
  const { currentStep } = state;
  const [resetDialogOpen, setResetDialogOpen] = useState(false);
  const [projectsOpen, setProjectsOpen] = useState(false);

  const handleResetConfirm = () => {
    resetWizard();
    setResetDialogOpen(false);
  };

  // Render current step
  const renderStep = () => {
    switch (currentStep) {
      case 0: return <Step1_Setup />;
      case 1: return <Step2_Contracts />;
      case 2: return <Step3_OrganizationalUnits />;
      case 3: return <Step4_Employees />;
      case 4: return <Step5_ScheduleInput />;
      case 5: return <Step6_WorkPeriods />;
      case 6: return <Step7_Demand />;
      case 7: return <Step8_Constraints />;
      case 8: return <Step9_Optimization />;
      case 9: return <Step10_ReviewGenerate />;
      default: return <Step1_Setup />;
    }
  };

  return (
    <Box sx={{ minHeight: '100vh', bgcolor: 'background.default' }}>
      {/* Header - Full Width */}
      <AppBar
        position="static"
        elevation={0}
        sx={{
          borderBottom: '2px solid',
          borderColor: 'divider',
          bgcolor: 'primary.main'
        }}
      >
        <Toolbar sx={{ minHeight: '64px' }}>
          <Typography variant="h6" component="div" sx={{ flexGrow: 1, fontWeight: 600 }}>
            JSON Generator - Schema v2.6
          </Typography>
          <Typography variant="body2" sx={{ opacity: 0.8, mr: 2 }}>
            Step {getVisibleStepNumber(currentStep)} of {TOTAL_VISIBLE}
          </Typography>
          <Tooltip title="Projects — save, load, export, import">
            <IconButton
              color="inherit"
              size="small"
              onClick={() => setProjectsOpen(true)}
              sx={{ opacity: 0.8, '&:hover': { opacity: 1 }, mr: 0.5 }}
            >
              <FolderSpecial />
            </IconButton>
          </Tooltip>
          <Tooltip title="Reset wizard — clears all data">
            <IconButton
              color="inherit"
              size="small"
              onClick={() => setResetDialogOpen(true)}
              sx={{ opacity: 0.8, '&:hover': { opacity: 1 } }}
            >
              <RestartAlt />
            </IconButton>
          </Tooltip>
        </Toolbar>
      </AppBar>

      {/* Project Manager */}
      <ProjectManagerDialog open={projectsOpen} onClose={() => setProjectsOpen(false)} />

      {/* Reset Confirmation Dialog */}
      <Dialog open={resetDialogOpen} onClose={() => setResetDialogOpen(false)}>
        <DialogTitle>Reset Wizard?</DialogTitle>
        <DialogContent>
          <DialogContentText>
            This will clear all entered data and return to Step 1. This action cannot be undone.
          </DialogContentText>
        </DialogContent>
        <DialogActions>
          <Button onClick={() => setResetDialogOpen(false)}>Cancel</Button>
          <Button onClick={handleResetConfirm} color="error" variant="contained">
            Reset
          </Button>
        </DialogActions>
      </Dialog>

      {/* Main Content */}
      <Container maxWidth="lg" sx={{ py: 4 }}>
        {/* Stepper */}
        <WizardStepper />

        {/* Current Step Content */}
        <Box sx={{ mt: 4 }}>
          {renderStep()}
        </Box>
      </Container>
    </Box>
  );
};

/**
 * Main App Component
 */
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
