import React, { useEffect, useState } from 'react';
import { Typography, Box, Alert, CircularProgress, Button } from '@mui/material';
import { Refresh } from '@mui/icons-material';
import JSZip from 'jszip';
import { saveAs } from 'file-saver';
import StepCard from '../components/wizard/StepCard';
import NavigationButtons from '../components/wizard/NavigationButtons';
import SummaryAccordions from '../components/review/SummaryAccordions';
import ValidationPanel from '../components/review/ValidationPanel';
import PreviewTabs from '../components/review/PreviewTabs';
import DownloadPanel from '../components/review/DownloadPanel';
import { useWizard } from '../context/WizardContext';
import { generateProblemJson } from '../utils/generators/jsonGenerator';
import { generateDemandCsv } from '../utils/generators/demandCsvGenerator';
import { generateScheduleInputCsv } from '../utils/generators/scheduleInputCsvGenerator';
import { validateAll } from '../utils/validators';

/**
 * Step 10: Review & Generate
 *
 * This is the final step where users:
 * 1. Review their configuration (all 9 steps)
 * 2. See validation results
 * 3. Preview generated files
 * 4. Download problem.json + CSVs
 */
const Step10_ReviewGenerate = () => {
  const { state, goToStep } = useWizard();

  const [generatedFiles, setGeneratedFiles] = useState(null);
  const [validationResults, setValidationResults] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [zipping, setZipping] = useState(false);

  /**
   * Generate files on mount
   */
  useEffect(() => {
    generateFiles();
  }, []);

  /**
   * Main generation function
   * Generates problem.json and CSV files from wizard state
   */
  const generateFiles = async () => {
    try {
      setLoading(true);
      setError(null);

      // Generate problem.json
      const problemJson = generateProblemJson(state, state.schemaVersion || '2.2');

      // Get employees list (depends on model)
      const employees = state.employees.model === 'team'
        ? state.employees.simple
        : state.employees.competency;

      // Generate demand.csv (workPeriods needed to detect per-day time overrides)
      const demandCsv = generateDemandCsv(
        state.demand.demandData || [],
        state.employees.model,
        state.demand.workPeriods || []
      );

      // Generate schedule_input.csv
      const scheduleInputCsv = generateScheduleInputCsv(
        employees || [],
        state.scheduleInput.dataMatrix || {},
        state.temporalScope.targetPeriod.start
          ? generateDateRangeFromState(state)
          : []
      );

      setGeneratedFiles({ problemJson, demandCsv, scheduleInputCsv });

      // Run validation
      const validation = validateAll(state);
      setValidationResults(validation);

    } catch (err) {
      console.error('Generation error:', err);
      setError(err.message || 'Unknown error during file generation');
    } finally {
      setLoading(false);
    }
  };

  /**
   * Handle regeneration (when user clicks "Regenerate" or "Revalidate")
   */
  const handleRegenerate = () => {
    generateFiles();
  };

  /**
   * Download all files as ZIP — called by the "Generate Files" NavigationButton
   */
  const handleGenerateFiles = async () => {
    if (!generatedFiles) return false;
    try {
      setZipping(true);
      const zip = new JSZip();
      zip.file('problem.json', JSON.stringify(generatedFiles.problemJson, null, 2));
      zip.file('demand.csv', generatedFiles.demandCsv);
      zip.file('schedule_input.csv', generatedFiles.scheduleInputCsv);
      const blob = await zip.generateAsync({ type: 'blob' });
      const filename = `${state.metadata.problemId || 'problem'}_scheduling_problem.zip`;
      saveAs(blob, filename);
    } catch (err) {
      console.error('ZIP creation failed:', err);
    } finally {
      setZipping(false);
    }
    return false; // stay on this step
  };

  /**
   * Handle jumping to a specific step from summary
   */
  const handleJumpToStep = (stepIndex) => {
    if (goToStep) {
      goToStep(stepIndex);
    }
  };

  // Loading state
  if (loading) {
    return (
      <Box sx={{ height: 'calc(100vh - 280px)', display: 'flex', flexDirection: 'column' }}>
        <Box sx={{ flexShrink: 0, mb: 2 }}>
          <Typography variant="h4" gutterBottom fontWeight={600}>
            Review & Generate
          </Typography>
          <Typography variant="body1" color="text.secondary">
            Review your configuration, validate, and generate the JSON + CSV files.
          </Typography>
        </Box>

        <Box sx={{ flexGrow: 1, display: 'flex', justifyContent: 'center', alignItems: 'center' }}>
          <Box sx={{ textAlign: 'center' }}>
            <CircularProgress size={60} />
            <Typography sx={{ mt: 2 }} color="text.secondary">
              Generating files...
            </Typography>
          </Box>
        </Box>

        <Box sx={{ flexShrink: 0, mt: 2 }}>
          <NavigationButtons nextDisabled />
        </Box>
      </Box>
    );
  }

  // Error state
  if (error) {
    return (
      <Box sx={{ height: 'calc(100vh - 280px)', display: 'flex', flexDirection: 'column' }}>
        <Box sx={{ flexShrink: 0, mb: 2 }}>
          <Typography variant="h4" gutterBottom fontWeight={600}>
            Review & Generate
          </Typography>
        </Box>

        <Box sx={{ flexGrow: 1 }}>
          <StepCard>
            <Alert severity="error" sx={{ mb: 2 }}>
              <Typography variant="h6" gutterBottom>
                Generation Failed
              </Typography>
              <Typography variant="body2">
                {error}
              </Typography>
            </Alert>

            <Button
              variant="contained"
              startIcon={<Refresh />}
              onClick={handleRegenerate}
            >
              Retry Generation
            </Button>
          </StepCard>
        </Box>

        <Box sx={{ flexShrink: 0, mt: 2 }}>
          <NavigationButtons nextDisabled />
        </Box>
      </Box>
    );
  }

  // Success state
  return (
    <Box sx={{ height: 'calc(100vh - 280px)', display: 'flex', flexDirection: 'column' }}>
      {/* HEADER - Fixed */}
      <Box sx={{ flexShrink: 0, mb: 2 }}>
        <Typography variant="h4" gutterBottom fontWeight={600}>
          Review & Generate
        </Typography>
        <Typography variant="body1" color="text.secondary">
          Review your configuration, validate, and download the generated files.
        </Typography>
      </Box>

      {/* CONTENT - Scrollable */}
      <Box sx={{ flexGrow: 1, overflowY: 'auto', overflowX: 'hidden', pr: 1 }}>
        <StepCard>
          {/* Summary Accordions */}
          <SummaryAccordions state={state} onJumpToStep={handleJumpToStep} />

          {/* Validation Panel */}
          <ValidationPanel
            results={validationResults}
            onRevalidate={handleRegenerate}
          />

          {/* Preview Tabs */}
          {generatedFiles && (
            <PreviewTabs files={generatedFiles} />
          )}

          {/* Download Panel - Only show if validation passed */}
          {generatedFiles && validationResults?.valid && (
            <DownloadPanel
              files={generatedFiles}
              problemId={state.metadata.problemId}
            />
          )}

          {/* Warning if validation failed */}
          {validationResults && !validationResults.valid && (
            <Alert severity="warning" sx={{ mt: 2 }}>
              <Typography variant="body2">
                Please fix validation errors before downloading files.
                You can still preview the generated files, but they may not work correctly with the scheduler.
              </Typography>
            </Alert>
          )}
        </StepCard>
      </Box>

      {/* NAVIGATION - Fixed at bottom */}
      <Box sx={{ flexShrink: 0, mt: 2 }}>
        <NavigationButtons
          onNext={generatedFiles ? handleGenerateFiles : undefined}
          nextDisabled={!generatedFiles || zipping}
          nextLabel={zipping ? 'Creating ZIP…' : 'Generate Files'}
        />
      </Box>
    </Box>
  );
};

/**
 * Helper: Generate date range from state
 */
function generateDateRangeFromState(state) {
  const { start } = state.temporalScope.targetPeriod;
  const { numDays } = state.temporalScope;

  if (!start || !numDays) return [];

  const dates = [];
  const startDate = new Date(start);

  for (let i = 0; i < numDays; i++) {
    const date = new Date(startDate);
    date.setDate(date.getDate() + i);
    dates.push(date.toISOString().split('T')[0]);
  }

  return dates;
}

export default Step10_ReviewGenerate;
