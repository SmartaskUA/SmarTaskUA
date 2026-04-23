import React from 'react';
import {
  Accordion,
  AccordionSummary,
  AccordionDetails,
  Typography,
  Box,
  Chip,
  Button,
  Stack
} from '@mui/material';
import { ExpandMore, CheckCircle, Warning, Error } from '@mui/icons-material';

/**
 * Summary Accordions Component
 *
 * Displays collapsible summary of each wizard step with:
 * - Status icon (complete/warning/error)
 * - Key data summary
 * - Edit button to jump back to step
 */
const SummaryAccordions = ({ state, onJumpToStep }) => {
  const accordions = [
    {
      step: 1,
      title: 'Quick Setup',
      status: getStep1Status(state),
      summary: <Step1Summary data={state} />
    },
    {
      step: 2,
      title: 'Contracts',
      status: getStep2Status(state),
      summary: <Step2Summary contracts={state.contracts.definitions} />
    },
    {
      step: 3,
      title: 'Organizational Units',
      status: getStep3Status(state),
      summary: <Step3Summary units={state.organizationalUnits} model={state.employees.model} />
    },
    {
      step: 4,
      title: 'Employees',
      status: getStep4Status(state),
      summary: <Step4Summary employees={state.employees} />
    },
    {
      step: 5,
      title: 'Schedule Input',
      status: getStep5Status(state),
      summary: <Step5Summary scheduleInput={state.scheduleInput} />
    },
    {
      step: 6,
      title: 'Work Periods',
      status: getStep6Status(state),
      summary: <Step6Summary workPeriods={state.demand.workPeriods} />
    },
    {
      step: 7,
      title: 'Demand',
      status: getStep7Status(state),
      summary: <Step7Summary demand={state.demand} />
    },
    /* Constraints (step 8) and Optimization (step 9) are hidden — not yet in the solver */
  ];

  return (
    <Box sx={{ mb: 3 }}>
      <Typography variant="h6" gutterBottom fontWeight={600}>
        Configuration Summary
      </Typography>
      {accordions.map(acc => (
        <Accordion key={acc.step}>
          <AccordionSummary expandIcon={<ExpandMore />}>
            <Box sx={{ display: 'flex', alignItems: 'center', gap: 2, width: '100%' }}>
              {getStatusIcon(acc.status)}
              <Typography sx={{ flexGrow: 1 }}>
                Step {acc.step}: {acc.title}
              </Typography>
              {getStatusChip(acc.status)}
            </Box>
          </AccordionSummary>
          <AccordionDetails>
            <Stack spacing={2}>
              {acc.summary}
              {onJumpToStep && (
                <Button
                  variant="outlined"
                  size="small"
                  onClick={() => onJumpToStep(acc.step - 1)}
                  sx={{ alignSelf: 'flex-start' }}
                >
                  Edit Step {acc.step}
                </Button>
              )}
            </Stack>
          </AccordionDetails>
        </Accordion>
      ))}
    </Box>
  );
};

// Status icon helpers
function getStatusIcon(status) {
  switch (status) {
    case 'complete':
      return <CheckCircle color="success" />;
    case 'warning':
      return <Warning color="warning" />;
    case 'error':
      return <Error color="error" />;
    default:
      return null;
  }
}

function getStatusChip(status) {
  const config = {
    complete: { label: 'Complete', color: 'success' },
    warning: { label: 'Warning', color: 'warning' },
    error: { label: 'Error', color: 'error' }
  };

  const { label, color } = config[status] || { label: 'Unknown', color: 'default' };
  return <Chip label={label} color={color} size="small" />;
}

// Status check functions
function getStep1Status(state) {
  if (!state.metadata?.problemId || !state.temporalScope?.year) return 'error';
  if (!state.employees?.model) return 'error';
  return 'complete';
}

function getStep2Status(state) {
  if (!state.contracts?.definitions?.length) return 'error';
  return 'complete';
}

function getStep3Status(state) {
  const hasTeams = state.organizationalUnits?.teams?.length > 0;
  if (!hasTeams) return 'error';
  return 'complete';
}

function getStep4Status(state) {
  const employees = state.employees?.model === 'team'
    ? state.employees.simple
    : state.employees.competency;
  if (!employees?.length) return 'error';
  return 'complete';
}

function getStep5Status(state) {
  const hasData = Object.keys(state.scheduleInput?.dataMatrix || {}).length > 0;
  if (!hasData) return 'warning';
  return 'complete';
}

function getStep6Status(state) {
  if (!state.demand?.workPeriods?.length) return 'error';
  return 'complete';
}

function getStep7Status(state) {
  if (!state.demand?.demandData?.length) return 'warning';
  return 'complete';
}

function getStep8Status(state) {
  return 'complete'; // Constraints are optional
}

function getStep9Status(state) {
  if (!state.optimization?.algorithm) return 'warning';
  return 'complete';
}

// Summary components
const Step1Summary = ({ data }) => (
  <Box>
    <Typography variant="body2"><strong>Problem ID:</strong> {data.metadata?.problemId || 'Not set'}</Typography>
    <Typography variant="body2"><strong>Year:</strong> {data.temporalScope?.year || 'Not set'}</Typography>
    <Typography variant="body2"><strong>Days:</strong> {data.temporalScope?.numDays || 0}</Typography>
    <Typography variant="body2"><strong>Date Range:</strong> {data.temporalScope?.targetPeriod?.start || 'Not set'} to {data.temporalScope?.targetPeriod?.end || 'Not set'}</Typography>
    <Typography variant="body2"><strong>Employee Model:</strong> {data.employees?.model || 'Not set'}</Typography>
    <Typography variant="body2"><strong>Work Period Model:</strong> {data.demand?.workPeriodModel || 'Not set'}</Typography>
  </Box>
);

const Step2Summary = ({ contracts }) => (
  <Box>
    <Typography variant="body2"><strong>Total Contracts:</strong> {contracts?.length || 0}</Typography>
    {contracts?.slice(0, 3).map(c => (
      <Chip key={c.id} label={`${c.name} (${c.workHoursPerDay}h)`} size="small" sx={{ mr: 0.5, mt: 0.5 }} />
    ))}
    {contracts?.length > 3 && <Typography variant="caption"> +{contracts.length - 3} more</Typography>}
  </Box>
);

const Step3Summary = ({ units, model }) => (
  <Box>
    <Typography variant="body2"><strong>Teams:</strong> {units?.teams?.length || 0}</Typography>
    {units?.teams?.slice(0, 5).map((t, i) => (
      <Chip key={i} label={typeof t === 'string' ? t : t.code} size="small" sx={{ mr: 0.5, mt: 0.5 }} />
    ))}
    {units?.teams?.length > 5 && <Typography variant="caption"> +{units.teams.length - 5} more</Typography>}
    {model === 'competency' && units?.competencies && (
      <>
        <Typography variant="body2" sx={{ mt: 1 }}><strong>Competencies:</strong> {units.competencies.length}</Typography>
        {units.competencies.slice(0, 3).map((c, i) => (
          <Chip key={i} label={typeof c === 'string' ? c : c.code} size="small" sx={{ mr: 0.5, mt: 0.5 }} />
        ))}
      </>
    )}
  </Box>
);

const Step4Summary = ({ employees }) => {
  const list = employees?.model === 'team' ? employees.simple : employees.competency;
  return (
    <Box>
      <Typography variant="body2"><strong>Total Employees:</strong> {list?.length || 0}</Typography>
      <Typography variant="body2"><strong>Model:</strong> {employees?.model || 'Not set'}</Typography>
    </Box>
  );
};

const Step5Summary = ({ scheduleInput }) => {
  const employeeCount = Object.keys(scheduleInput?.dataMatrix || {}).length;
  let totalCells = 0;
  let filledCells = 0;

  Object.values(scheduleInput?.dataMatrix || {}).forEach(empData => {
    Object.values(empData).forEach(value => {
      totalCells++;
      if (value && value !== '' && value !== '-') {
        filledCells++;
      }
    });
  });

  const coverage = totalCells > 0 ? Math.round((filledCells / totalCells) * 100) : 0;

  return (
    <Box>
      <Typography variant="body2"><strong>Employees with data:</strong> {employeeCount}</Typography>
      <Typography variant="body2"><strong>Coverage:</strong> {coverage}% ({filledCells}/{totalCells} cells)</Typography>
    </Box>
  );
};

const Step6Summary = ({ workPeriods }) => (
  <Box>
    <Typography variant="body2"><strong>Work Periods:</strong> {workPeriods?.length || 0}</Typography>
    {workPeriods?.map(wp => (
      <Chip
        key={wp.code}
        label={`${wp.code}: ${wp.name}`}
        size="small"
        sx={{ mr: 0.5, mt: 0.5 }}
      />
    ))}
  </Box>
);

const Step7Summary = ({ demand }) => (
  <Box>
    <Typography variant="body2"><strong>Demand Entries:</strong> {demand?.demandData?.length || 0}</Typography>
    <Typography variant="body2"><strong>Priority Hierarchy:</strong> {demand?.priorityHierarchy?.length || 0} levels</Typography>
  </Box>
);

const Step8Summary = ({ constraints }) => {
  const hardEnabled = constraints?.hard?.filter(c => c.enabled).length || 0;
  const softEnabled = constraints?.soft?.filter(c => c.enabled).length || 0;

  return (
    <Box>
      <Typography variant="body2"><strong>Hard Constraints:</strong> {hardEnabled} enabled</Typography>
      <Typography variant="body2"><strong>Soft Constraints:</strong> {softEnabled} enabled</Typography>
      {constraints?.advanced?.dayOffSwapping?.enabled && (
        <Chip label="Day-off Swapping" size="small" sx={{ mt: 0.5, mr: 0.5 }} />
      )}
      {constraints?.advanced?.breaks?.enabled && (
        <Chip label="Break Rules" size="small" sx={{ mt: 0.5, mr: 0.5 }} />
      )}
    </Box>
  );
};

const Step9Summary = ({ optimization }) => (
  <Box>
    <Typography variant="body2"><strong>Algorithm:</strong> {optimization?.algorithm || 'Not set'}</Typography>
    <Typography variant="body2"><strong>Max Time:</strong> {optimization?.maxTimeMinutes || 10} minutes</Typography>
    <Typography variant="body2"><strong>Objectives:</strong> {optimization?.objectives?.length || 0}</Typography>
  </Box>
);

export default SummaryAccordions;
