import React from 'react';
import {
  Typography,
  Box,
  Slider,
  Divider,
  Paper,
  Chip,
  Alert
} from '@mui/material';
import { Timer as TimerIcon } from '@mui/icons-material';
import StepCard from '../components/wizard/StepCard';
import NavigationButtons from '../components/wizard/NavigationButtons';
import AlgorithmSelector from '../components/optimization/AlgorithmSelector';
import ObjectivesTable from '../components/optimization/ObjectivesTable';
import { useWizard } from '../context/WizardContext';

/**
 * Step 9: Optimization Settings
 *
 * Configure solver algorithm, time limits, and custom objectives.
 *
 * - Algorithm: Solver type (ILP, CSPv2, Heuristic, Hybrid)
 * - Max Time: Maximum solver runtime (1-60 minutes)
 * - Objectives: Optional custom optimization goals
 */
const Step9_Optimization = () => {
  const { state, updateState } = useWizard();

  const optimization = state.optimization || {
    algorithm: 'ILP',
    maxTimeMinutes: 10,
    objectives: []
  };

  // Handle algorithm change
  const handleAlgorithmChange = (algorithm) => {
    updateState('optimization.algorithm', algorithm);
  };

  // Handle time limit change
  const handleTimeChange = (event, newValue) => {
    updateState('optimization.maxTimeMinutes', newValue);
  };

  // Handle objectives change
  const handleObjectivesChange = (newObjectives) => {
    updateState('optimization.objectives', newObjectives);
  };

  // Format time label
  const formatTimeLabel = (value) => {
    if (value === 1) return '1 min';
    if (value >= 60) return '60 min';
    return `${value} min`;
  };

  return (
    <Box
      sx={{
        height: 'calc(100vh - 280px)',
        display: 'flex',
        flexDirection: 'column'
      }}
    >
      {/* HEADER - Fixed */}
      <Box sx={{ flexShrink: 0, mb: 2 }}>
        <Typography variant="h4" gutterBottom fontWeight={600}>
          Optimization Settings
        </Typography>
        <Typography variant="body1" color="text.secondary">
          Configure the solver algorithm, time limits, and custom optimization objectives.
          These settings control how schedules are generated.
        </Typography>
      </Box>

      {/* CONTENT - Scrollable */}
      <Box
        sx={{
          flexGrow: 1,
          overflowY: 'auto',
          overflowX: 'hidden',
          pr: 1
        }}
      >
        <StepCard>
          {/* Summary Card */}
          <Paper
            sx={{
              p: 2,
              mb: 3,
              backgroundColor: 'primary.main',
              color: 'primary.contrastText'
            }}
          >
            <Typography variant="h6" gutterBottom>
              Current Configuration
            </Typography>
            <Box sx={{ display: 'flex', gap: 2, flexWrap: 'wrap', mt: 1 }}>
              <Chip
                label={`Algorithm: ${optimization.algorithm}`}
                sx={{
                  backgroundColor: 'background.paper',
                  color: 'text.primary',
                  fontWeight: 'bold'
                }}
              />
              <Chip
                label={`Time Limit: ${optimization.maxTimeMinutes} minutes`}
                icon={<TimerIcon />}
                sx={{
                  backgroundColor: 'background.paper',
                  color: 'text.primary',
                  fontWeight: 'bold'
                }}
              />
              <Chip
                label={`Custom Objectives: ${optimization.objectives?.length || 0}`}
                sx={{
                  backgroundColor: 'background.paper',
                  color: 'text.primary',
                  fontWeight: 'bold'
                }}
              />
            </Box>
          </Paper>

          {/* Algorithm Selector */}
          <AlgorithmSelector
            value={optimization.algorithm}
            onChange={handleAlgorithmChange}
          />

          <Divider sx={{ my: 4 }} />

          {/* Time Limit Slider */}
          <Box>
            <Typography variant="h6" gutterBottom fontWeight={600}>
              Maximum Solver Time
            </Typography>
            <Typography variant="body2" color="text.secondary" sx={{ mb: 2 }}>
              How long the solver should run before returning the best solution found.
              Longer times may produce better schedules but take more time.
            </Typography>

            <Box sx={{ px: 2 }}>
              <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', mb: 2 }}>
                <Typography variant="body2" color="text.secondary">
                  Time Limit
                </Typography>
                <Chip
                  label={formatTimeLabel(optimization.maxTimeMinutes)}
                  color="primary"
                  sx={{ fontWeight: 'bold', minWidth: 80 }}
                />
              </Box>

              <Slider
                value={optimization.maxTimeMinutes}
                onChange={handleTimeChange}
                min={1}
                max={60}
                step={1}
                marks={[
                  { value: 1, label: '1m' },
                  { value: 5, label: '5m' },
                  { value: 10, label: '10m' },
                  { value: 15, label: '15m' },
                  { value: 30, label: '30m' },
                  { value: 60, label: '60m' }
                ]}
                valueLabelDisplay="auto"
                valueLabelFormat={formatTimeLabel}
              />
            </Box>

            <Alert severity="info" sx={{ mt: 2 }}>
              <Typography variant="body2">
                <strong>Recommended:</strong> 5-15 minutes for most problems. Very large problems (100+ employees,
                365 days) may benefit from longer times (30-60 minutes).
              </Typography>
            </Alert>
          </Box>

          <Divider sx={{ my: 4 }} />

          {/* Objectives Table */}
          <ObjectivesTable
            objectives={optimization.objectives || []}
            onChange={handleObjectivesChange}
          />
        </StepCard>
      </Box>

      {/* NAVIGATION - Fixed at bottom */}
      <Box sx={{ flexShrink: 0, mt: 2 }}>
        <NavigationButtons />
      </Box>
    </Box>
  );
};

export default Step9_Optimization;
