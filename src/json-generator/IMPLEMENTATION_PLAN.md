# 🎯 JSON Generation Frontend - Comprehensive Development Plan

**Project**: Complete the JSON Generation Wizard for SmarTask Schema v2.2/v2.5
**Current State**: 11-step wizard with Steps 1-3 complete, Steps 4-9 partial, Step 10 missing
**Goal**: Deliver a fully functional wizard that generates problem.json + CSVs without manual editing
**Estimated Effort**: 8-12 development days (72-104 hours)
**Priority**: High - blocks user adoption of JSON generation workflow
**Created**: 2026-04-21
**Last Updated**: 2026-04-21

---

## 📊 Executive Summary

### Current State Analysis

**What Exists (Verified)**:
- ✅ Infrastructure: WizardContext, navigation, theme system
- ✅ Step 1: Quick Setup (metadata, temporal scope)
- ✅ Step 2: Contracts (add/edit/delete contracts with constraints)
- ✅ Step 3: Organizational Units (teams table)
- ✅ Step 7: Demand (advanced weekly template + calendar grid)
- ✅ 42 JSX files already created

**Critical Gaps**:
- ❌ **Step 10: Generation & Download** - BLOCKER: No way to export files
- ❌ **Step 5: Schedule Input Matrix** - Core feature, complex UI
- 🟡 Steps 4, 6, 8, 9: Files exist but completeness unknown
- ❌ Generation utilities (jsonGenerator, CSV generators)
- ❌ Validation system
- ❌ Preview components

---

## 📋 Table of Contents

1. [Development Phases Overview](#development-phases-overview)
2. [Phase 1: Unblock End-to-End (Days 1-4)](#phase-1-unblock-end-to-end-days-1-4)
3. [Phase 2: Complete Steps 4-9 (Days 5-8)](#phase-2-complete-steps-4-9-days-5-8)
4. [Phase 3: Polish & Advanced Features (Days 9-11)](#phase-3-polish--advanced-features-days-9-11)
5. [Phase 4: Testing & Documentation (Days 12-13)](#phase-4-testing--documentation-days-12-13)
6. [Success Criteria](#success-criteria)
7. [Risk Management](#risk-management)

---

## Development Phases Overview

| Phase | Focus | Duration | Priority | Deliverable |
|-------|-------|----------|----------|-------------|
| **1** | Unblock End-to-End | 3-4 days | 🔴 Critical | Working file generation |
| **2** | Complete Steps 4-9 | 3-4 days | 🟡 High | All steps functional |
| **3** | Polish & Advanced | 2-3 days | 🟢 Medium | Production-ready |
| **4** | Testing & Docs | 1-2 days | 🟢 Medium | Release candidate |

**Total Estimate**: 9-13 days (72-104 hours)

---

# PHASE 1: Unblock End-to-End (Days 1-4)

## Objective
Enable users to complete all 11 steps and download generated files. This makes the wizard immediately useful.

## Critical Path
1. ✅ Generation utilities (jsonGenerator, CSV generators)
2. ✅ Step 10 UI (preview, validation, download)
3. ✅ Schedule Input Matrix (Step 5)
4. ✅ Basic validation system

---

## Task 1.1: Create Generation Utilities (Day 1, 6-8 hours)

**Location**: `src/utils/generators/`

### 1.1.1 - jsonGenerator.js

**Purpose**: Convert wizard state to problem.json

**File**: `src/utils/generators/jsonGenerator.js`

```javascript
/**
 * Generates problem.json from wizard state
 * Handles both schema v2.2 and v2.5
 *
 * @param {Object} state - Complete wizard state from WizardContext
 * @param {string} schemaVersion - "2.2" or "2.5"
 * @returns {Object} - Valid problem.json object
 */
export function generateProblemJson(state, schemaVersion = "2.2") {
  const problemJson = {
    schemaVersion: schemaVersion,
    problemType: "employee_scheduling",
    metadata: buildMetadata(state.metadata),
    features: detectFeatures(state), // Auto-detect from config
    temporalScope: buildTemporalScope(state.temporalScope),
    contracts: buildContracts(state.contracts),
    employees: buildEmployees(state.employees),
    scheduleInput: buildScheduleInputRef(state.scheduleInput),
    demand: buildDemand(state.demand, state.organizationalUnits),
    constraints: buildConstraints(state.constraints),
    optimization: buildOptimization(state.optimization)
  };

  // v2.5 specific additions
  if (schemaVersion === "2.5" && state.operatingHours?.enabled) {
    problemJson.operatingHours = buildOperatingHours(state.operatingHours);
  }

  return problemJson;
}

/**
 * Build metadata section
 */
function buildMetadata(metadata) {
  return {
    problemId: metadata.problemId,
    createdAt: metadata.createdAt || new Date().toISOString(),
    description: metadata.description || "",
    source: metadata.source || ""
  };
}

/**
 * Auto-detect feature flags from configuration
 */
function detectFeatures(state) {
  return {
    useWorkPeriodBasedScheduling: (state.demand?.workPeriods?.length || 0) > 0,
    useAdvancedConstraints: state.constraints?.advanced?.enabled || false,
    usePriorityHierarchy: (state.demand?.priorityHierarchy?.length || 0) > 0
  };
}

/**
 * Build temporal scope section
 */
function buildTemporalScope(scope) {
  return {
    year: scope.year,
    numDays: scope.numDays,
    targetPeriod: {
      start: scope.targetPeriod.start,
      end: scope.targetPeriod.end
    }
  };
}

/**
 * Build contracts section
 */
function buildContracts(contracts) {
  return {
    definitions: (contracts.definitions || []).map(contract => ({
      id: contract.id,
      name: contract.name,
      workHoursPerDay: contract.workHoursPerDay,
      ...(contract.constraints && { constraints: contract.constraints })
    }))
  };
}

/**
 * Build employees section (handles team vs competency model)
 */
function buildEmployees(employees) {
  const result = {
    model: employees.model
  };

  if (employees.model === 'team') {
    result.simple = (employees.simple || []).map(emp => ({
      id: emp.id,
      name: emp.name || "",
      teams: emp.teams || [],
      contractType: emp.contractType
    }));
  } else {
    result.competency = (employees.competency || []).map(emp => ({
      id: emp.id,
      name: emp.name || "",
      teams: emp.teams || [],
      contractType: emp.contractType,
      ...(emp.contractPeriods && { contractPeriods: emp.contractPeriods }),
      ...(emp.restrictions && { restrictions: emp.restrictions })
    }));
  }

  return result;
}

/**
 * Build schedule input reference section
 */
function buildScheduleInputRef(scheduleInput) {
  return {
    enabled: true,
    dataFile: "schedule_input.csv",
    markingTypes: scheduleInput.markingTypes || {}
  };
}

/**
 * Build demand section with organizational units
 */
function buildDemand(demand, organizationalUnits) {
  const result = {
    workPeriodModel: demand.workPeriodModel || "fixed",
    dataFile: "demand.csv",
    workPeriods: (demand.workPeriods || []).map(wp => ({
      code: wp.code,
      name: wp.name,
      order: wp.order,
      timeRange: wp.timeRange,
      ...(wp.breaks && { breaks: wp.breaks })
    })),
    organizationalUnits: {}
  };

  // Add teams or competencies based on model
  if (organizationalUnits.teams && organizationalUnits.teams.length > 0) {
    result.organizationalUnits.teams = organizationalUnits.teams;
  }
  if (organizationalUnits.competencies && organizationalUnits.competencies.length > 0) {
    result.organizationalUnits.competencies = organizationalUnits.competencies;
  }

  // Add priority hierarchy if present
  if (demand.priorityHierarchy && demand.priorityHierarchy.length > 0) {
    result.priorityHierarchy = demand.priorityHierarchy;
  }

  return result;
}

/**
 * Build constraints section
 */
function buildConstraints(constraints) {
  return {
    hard: constraints.hard || [],
    soft: constraints.soft || []
  };
}

/**
 * Build optimization section
 */
function buildOptimization(optimization) {
  return {
    algorithm: optimization.algorithm || "CSPv2",
    maxTimeMinutes: optimization.maxTimeMinutes || 10,
    objectives: optimization.objectives || []
  };
}

/**
 * Build operating hours section (v2.5 only)
 */
function buildOperatingHours(operatingHours) {
  return {
    enabled: true,
    dataFile: operatingHours.dataFile || "operating_hours.csv",
    enforcement: operatingHours.enforcement || "hard",
    validation: operatingHours.validation || {},
    options: operatingHours.options || {}
  };
}
```

**Acceptance Criteria**:
- [ ] Generates valid problem.json for team model
- [ ] Generates valid problem.json for competency model
- [ ] Auto-detects all feature flags correctly
- [ ] Handles missing optional fields gracefully
- [ ] Unit tests pass (10+ test cases)

---

### 1.1.2 - demandCsvGenerator.js

**Purpose**: Convert demand data to CSV format

**File**: `src/utils/generators/demandCsvGenerator.js`

```javascript
import Papa from 'papaparse';

/**
 * Generates demand.csv from wizard demand data
 *
 * @param {Array} demandData - Array of demand entries
 * @param {Array} workPeriods - Work period definitions
 * @param {Array} teams - Team/competency list
 * @returns {string} - CSV content
 */
export function generateDemandCsv(demandData, workPeriods, teams) {
  const rows = demandData.map(entry => ({
    date: formatDate(entry.date), // YYYY-MM-DD
    workPeriod: entry.workPeriod,
    team: entry.team,
    minimum: entry.minimum || 0,
    ideal: entry.ideal || 0,
    estimated: entry.estimated || 0
  }));

  // Sort by date, then workPeriod, then team
  rows.sort((a, b) => {
    if (a.date !== b.date) return a.date.localeCompare(b.date);
    if (a.workPeriod !== b.workPeriod) return a.workPeriod.localeCompare(b.workPeriod);
    return a.team.localeCompare(b.team);
  });

  return Papa.unparse(rows, {
    columns: ['date', 'workPeriod', 'team', 'minimum', 'ideal', 'estimated'],
    header: true
  });
}

/**
 * Format date to YYYY-MM-DD
 */
function formatDate(date) {
  if (typeof date === 'string') return date;
  return date.toISOString().split('T')[0];
}

/**
 * Validates demand CSV content
 * @returns {Array} - Array of validation errors
 */
export function validateDemandCsv(demandData, workPeriods, teams, dateRange) {
  const errors = [];

  const workPeriodCodes = new Set(workPeriods.map(wp => wp.code));
  const teamSet = new Set(teams);
  const dateSet = new Set(dateRange);

  demandData.forEach((entry, index) => {
    // Date validation
    if (!dateSet.has(entry.date)) {
      errors.push({
        row: index + 1,
        field: 'date',
        message: `Date ${entry.date} is outside temporal scope`
      });
    }

    // Work period validation
    if (!workPeriodCodes.has(entry.workPeriod)) {
      errors.push({
        row: index + 1,
        field: 'workPeriod',
        message: `Invalid work period: ${entry.workPeriod}`
      });
    }

    // Team validation
    if (!teamSet.has(entry.team)) {
      errors.push({
        row: index + 1,
        field: 'team',
        message: `Invalid team: ${entry.team}`
      });
    }

    // Logical order validation
    const { minimum, ideal, estimated } = entry;
    if (minimum > estimated || estimated > ideal) {
      errors.push({
        row: index + 1,
        field: 'values',
        message: `Invalid order: minimum (${minimum}) <= estimated (${estimated}) <= ideal (${ideal})`
      });
    }
  });

  return errors;
}
```

**Acceptance Criteria**:
- [ ] Generates valid CSV with correct headers
- [ ] Sorts rows logically (date → workPeriod → team)
- [ ] Validates minimum ≤ estimated ≤ ideal
- [ ] Handles empty demand data gracefully

---

### 1.1.3 - scheduleInputCsvGenerator.js

**Purpose**: Convert schedule matrix to CSV format

**File**: `src/utils/generators/scheduleInputCsvGenerator.js`

```javascript
import Papa from 'papaparse';
import { generateDateRange } from '../helpers/dateHelpers';

/**
 * Generates schedule_input.csv from wizard schedule matrix
 *
 * @param {Array} employees - Employee list
 * @param {Object} dataMatrix - {employeeId: {date: value}}
 * @param {Object} temporalScope - Date range info
 * @returns {string} - CSV content
 */
export function generateScheduleInputCsv(employees, dataMatrix, temporalScope) {
  const dateRange = generateDateRange(
    temporalScope.targetPeriod.start,
    temporalScope.targetPeriod.end
  );

  const headers = ['employee_id', ...dateRange];

  const rows = employees.map(emp => {
    const row = { employee_id: emp.id };
    dateRange.forEach(date => {
      row[date] = dataMatrix[emp.id]?.[date] || '';
    });
    return row;
  });

  return Papa.unparse(rows, {
    columns: headers,
    header: true
  });
}

/**
 * Validates schedule input CSV
 * @returns {Array} - Validation errors
 */
export function validateScheduleInputCsv(dataMatrix, employees, contracts, markingTypes) {
  const errors = [];

  const contractMap = new Map(contracts.definitions.map(c => [c.id, c]));
  const employeeMap = new Map(employees.map(e => [e.id, e]));
  const validMarkings = new Set([
    'A', 'VAC', 'NOT',
    ...Object.keys(markingTypes)
  ]);

  Object.entries(dataMatrix).forEach(([empId, dates]) => {
    const employee = employeeMap.get(empId);

    if (!employee) {
      errors.push({
        employee: empId,
        message: `Employee ${empId} not found in employee list`
      });
      return;
    }

    Object.entries(dates).forEach(([date, value]) => {
      if (!value) return; // Empty is valid

      // Check if it's a valid number (1-16)
      if (/^\d+$/.test(value)) {
        const hours = parseInt(value);
        if (hours < 1 || hours > 16) {
          errors.push({
            employee: empId,
            date,
            value,
            message: `Invalid hours: ${hours}. Must be 1-16`
          });
        }
        return;
      }

      // Check if it's a time window constraint
      if (value.startsWith('EQUALS:') || value.startsWith('INCLUDE:') || value.startsWith('EXCEPT:')) {
        const timeConstraintError = validateTimeConstraint(value);
        if (timeConstraintError) {
          errors.push({
            employee: empId,
            date,
            value,
            message: timeConstraintError
          });
        }
        return;
      }

      // Check if it's 'A' (auto-allocate)
      if (value === 'A') {
        const contract = contractMap.get(employee.contractType);
        if (!contract || !contract.workHoursPerDay) {
          errors.push({
            employee: empId,
            date,
            value,
            message: `Employee uses 'A' but has no contract with workHoursPerDay`
          });
        }
        return;
      }

      // Check if it's a valid marking
      if (!validMarkings.has(value)) {
        errors.push({
          employee: empId,
          date,
          value,
          message: `Unknown marking: ${value}. Define it in markingTypes or use A, 1-16, VAC, NOT`
        });
      }
    });
  });

  return errors;
}

/**
 * Validate time window constraint format
 */
function validateTimeConstraint(value) {
  const match = value.match(/^(EQUALS|INCLUDE|EXCEPT):(\d{2}:\d{2})-(\d{2}:\d{2})$/);

  if (!match) {
    return 'Invalid time constraint format. Use MODE:HH:MM-HH:MM';
  }

  const [, mode, startTime, endTime] = match;
  const [startHH, startMM] = startTime.split(':').map(Number);
  const [endHH, endMM] = endTime.split(':').map(Number);

  if (startHH > 23 || startMM > 59 || endHH > 23 || endMM > 59) {
    return 'Invalid time format. Hours: 00-23, Minutes: 00-59';
  }

  if (startHH * 60 + startMM >= endHH * 60 + endMM) {
    return 'Start time must be before end time';
  }

  return null;
}
```

**Acceptance Criteria**:
- [ ] Generates CSV with employee_id + date columns
- [ ] Handles sparse matrix (empty cells)
- [ ] Validates cell values (A, 1-16, markings)
- [ ] Validates time window constraints format

---

### 1.1.4 - operatingHoursCsvGenerator.js (v2.5 only)

**Purpose**: Generate operating_hours.csv for schema v2.5

**File**: `src/utils/generators/operatingHoursCsvGenerator.js`

```javascript
import Papa from 'papaparse';

/**
 * Generates operating_hours.csv (v2.5 feature)
 *
 * @param {Array} operatingHoursData - Operating hours entries
 * @returns {string} - CSV content
 */
export function generateOperatingHoursCsv(operatingHoursData) {
  const rows = operatingHoursData.map(entry => ({
    date: entry.date,
    team: entry.team || 'ALL',
    open: entry.open || 'CLOSED',
    close: entry.close || 'CLOSED'
  }));

  // Sort by date, then team
  rows.sort((a, b) => {
    if (a.date !== b.date) return a.date.localeCompare(b.date);
    return a.team.localeCompare(b.team);
  });

  return Papa.unparse(rows, {
    columns: ['date', 'team', 'open', 'close'],
    header: true
  });
}

/**
 * Validate operating hours data
 */
export function validateOperatingHours(operatingHoursData, dateRange, teams) {
  const errors = [];
  const dateSet = new Set(dateRange);
  const teamSet = new Set(['ALL', ...teams]);

  operatingHoursData.forEach((entry, index) => {
    if (!dateSet.has(entry.date)) {
      errors.push({
        row: index + 1,
        message: `Date ${entry.date} is outside temporal scope`
      });
    }

    if (!teamSet.has(entry.team)) {
      errors.push({
        row: index + 1,
        message: `Invalid team: ${entry.team}`
      });
    }

    if (entry.open !== 'CLOSED' && entry.close !== 'CLOSED') {
      const openValid = /^\d{2}:\d{2}$/.test(entry.open);
      const closeValid = /^\d{2}:\d{2}$/.test(entry.close);

      if (!openValid || !closeValid) {
        errors.push({
          row: index + 1,
          message: 'Invalid time format. Use HH:MM or CLOSED'
        });
      }
    }
  });

  return errors;
}
```

**Acceptance Criteria**:
- [ ] Generates CSV with correct format
- [ ] Handles CLOSED days
- [ ] Supports team-specific hours

---

### 1.1.5 - Helper: dateHelpers.js

**File**: `src/utils/helpers/dateHelpers.js`

```javascript
import { format, eachDayOfInterval, parseISO } from 'date-fns';

/**
 * Generate array of dates between start and end (inclusive)
 *
 * @param {string|Date} start - Start date
 * @param {string|Date} end - End date
 * @returns {Array<string>} - Array of YYYY-MM-DD strings
 */
export function generateDateRange(start, end) {
  const startDate = typeof start === 'string' ? parseISO(start) : start;
  const endDate = typeof end === 'string' ? parseISO(end) : end;

  const dates = eachDayOfInterval({ start: startDate, end: endDate });

  return dates.map(date => format(date, 'yyyy-MM-dd'));
}

/**
 * Format date header for display (e.g., "Jan 15")
 */
export function formatDateHeader(dateString) {
  const date = parseISO(dateString);
  return format(date, 'MMM dd');
}

/**
 * Generate week dates (Monday-Friday)
 */
export function generateWeekDates(weekStart) {
  const start = typeof weekStart === 'string' ? parseISO(weekStart) : weekStart;
  const dates = [];

  for (let i = 0; i < 5; i++) {
    const date = new Date(start);
    date.setDate(date.getDate() + i);
    dates.push(format(date, 'yyyy-MM-dd'));
  }

  return dates;
}
```

---

## Task 1.2: Implement Step 10 UI (Day 2, 6-8 hours)

**Location**: `src/steps/Step10_ReviewGenerate.jsx`

### Main Step Component

**File**: `src/steps/Step10_ReviewGenerate.jsx`

```jsx
import React, { useEffect, useState } from 'react';
import { Box, Typography, Alert, CircularProgress } from '@mui/material';
import { useWizard } from '../context/WizardContext';
import { generateProblemJson } from '../utils/generators/jsonGenerator';
import { generateDemandCsv } from '../utils/generators/demandCsvGenerator';
import { generateScheduleInputCsv } from '../utils/generators/scheduleInputCsvGenerator';
import { validateAll } from '../utils/validators';
import StepCard from '../components/wizard/StepCard';
import NavigationButtons from '../components/wizard/NavigationButtons';
import SummaryAccordions from '../components/review/SummaryAccordions';
import ValidationPanel from '../components/review/ValidationPanel';
import PreviewTabs from '../components/review/PreviewTabs';
import DownloadPanel from '../components/review/DownloadPanel';

const Step10_ReviewGenerate = () => {
  const { state } = useWizard();
  const [generatedFiles, setGeneratedFiles] = useState(null);
  const [validationResults, setValidationResults] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  // Generate files on mount or when state changes
  useEffect(() => {
    generateFiles();
  }, []); // Only run once on mount

  const generateFiles = async () => {
    try {
      setLoading(true);
      setError(null);

      // Generate files
      const problemJson = generateProblemJson(state, '2.2');

      const employees = state.employees.model === 'team'
        ? state.employees.simple
        : state.employees.competency;

      const demandCsv = generateDemandCsv(
        state.demand.demandData || [],
        state.demand.workPeriods || [],
        state.organizationalUnits.teams || []
      );

      const scheduleInputCsv = generateScheduleInputCsv(
        employees || [],
        state.scheduleInput.dataMatrix || {},
        state.temporalScope
      );

      setGeneratedFiles({ problemJson, demandCsv, scheduleInputCsv });

      // Run validation
      const validation = validateAll(state);
      setValidationResults(validation);

    } catch (err) {
      console.error('Generation error:', err);
      setError(err.message);
    } finally {
      setLoading(false);
    }
  };

  const handleRegenerate = () => {
    generateFiles();
  };

  if (loading) {
    return (
      <Box sx={{ display: 'flex', justifyContent: 'center', alignItems: 'center', height: '60vh' }}>
        <CircularProgress />
        <Typography sx={{ ml: 2 }}>Generating files...</Typography>
      </Box>
    );
  }

  if (error) {
    return (
      <Box>
        <Alert severity="error" sx={{ mb: 2 }}>
          <Typography variant="h6">Generation Failed</Typography>
          <Typography>{error}</Typography>
        </Alert>
        <NavigationButtons onNext={handleRegenerate} nextLabel="Retry" />
      </Box>
    );
  }

  return (
    <Box sx={{ height: 'calc(100vh - 280px)', display: 'flex', flexDirection: 'column' }}>
      <Box sx={{ flexShrink: 0, mb: 2 }}>
        <Typography variant="h4" gutterBottom fontWeight={600}>
          Review & Generate
        </Typography>
        <Typography variant="body2" color="text.secondary">
          Review your configuration, validate, and download the generated files.
        </Typography>
      </Box>

      <Box sx={{ flexGrow: 1, overflow: 'auto' }}>
        <StepCard>
          {/* Summary Section */}
          <SummaryAccordions state={state} />

          {/* Validation Section */}
          <ValidationPanel
            results={validationResults}
            onRevalidate={handleRegenerate}
          />

          {/* Preview Tabs */}
          {generatedFiles && (
            <PreviewTabs files={generatedFiles} />
          )}

          {/* Download Actions */}
          {generatedFiles && validationResults?.valid && (
            <DownloadPanel files={generatedFiles} problemId={state.metadata.problemId} />
          )}

          {validationResults && !validationResults.valid && (
            <Alert severity="warning" sx={{ mt: 2 }}>
              Please fix validation errors before downloading files.
            </Alert>
          )}
        </StepCard>
      </Box>

      <Box sx={{ flexShrink: 0, mt: 2 }}>
        <NavigationButtons
          showNext={false}
          customNextButton={
            validationResults?.valid && (
              <Typography variant="body2" color="success.main">
                ✓ Ready to download!
              </Typography>
            )
          }
        />
      </Box>
    </Box>
  );
};

export default Step10_ReviewGenerate;
```

---

### Sub-Component: SummaryAccordions

**File**: `src/components/review/SummaryAccordions.jsx`

```jsx
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
import { useNavigate } from 'react-router-dom';

/**
 * Displays collapsible summary of each wizard step
 * Shows completion status, key data, and "Edit" button to jump back
 */
const SummaryAccordions = ({ state }) => {
  const navigate = useNavigate();

  const jumpToStep = (step) => {
    // Navigate to specific step (implementation depends on routing)
    // For now, just scroll to top
    window.scrollTo(0, 0);
  };

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
    {
      step: 8,
      title: 'Constraints',
      status: getStep8Status(state),
      summary: <Step8Summary constraints={state.constraints} />
    },
    {
      step: 9,
      title: 'Optimization',
      status: getStep9Status(state),
      summary: <Step9Summary optimization={state.optimization} />
    }
  ];

  return (
    <Box sx={{ mb: 3 }}>
      <Typography variant="h6" gutterBottom>Configuration Summary</Typography>
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
              <Button
                variant="outlined"
                size="small"
                onClick={() => jumpToStep(acc.step)}
                sx={{ alignSelf: 'flex-start' }}
              >
                Edit
              </Button>
            </Stack>
          </AccordionDetails>
        </Accordion>
      ))}
    </Box>
  );
};

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
    <Typography variant="body2"><strong>Problem ID:</strong> {data.metadata?.problemId}</Typography>
    <Typography variant="body2"><strong>Year:</strong> {data.temporalScope?.year}</Typography>
    <Typography variant="body2"><strong>Days:</strong> {data.temporalScope?.numDays}</Typography>
    <Typography variant="body2"><strong>Model:</strong> {data.employees?.model || 'Not set'}</Typography>
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
    {units?.teams?.slice(0, 5).map(t => (
      <Chip key={t} label={t} size="small" sx={{ mr: 0.5, mt: 0.5 }} />
    ))}
  </Box>
);

const Step4Summary = ({ employees }) => {
  const list = employees?.model === 'team' ? employees.simple : employees.competency;
  return (
    <Box>
      <Typography variant="body2"><strong>Total Employees:</strong> {list?.length || 0}</Typography>
    </Box>
  );
};

const Step5Summary = ({ scheduleInput }) => {
  const employeeCount = Object.keys(scheduleInput?.dataMatrix || {}).length;
  return (
    <Box>
      <Typography variant="body2"><strong>Employees with data:</strong> {employeeCount}</Typography>
    </Box>
  );
};

const Step6Summary = ({ workPeriods }) => (
  <Box>
    <Typography variant="body2"><strong>Work Periods:</strong> {workPeriods?.length || 0}</Typography>
    {workPeriods?.map(wp => (
      <Chip key={wp.code} label={`${wp.name} (${wp.code})`} size="small" sx={{ mr: 0.5, mt: 0.5 }} />
    ))}
  </Box>
);

const Step7Summary = ({ demand }) => (
  <Box>
    <Typography variant="body2"><strong>Demand Entries:</strong> {demand?.demandData?.length || 0}</Typography>
  </Box>
);

const Step8Summary = ({ constraints }) => (
  <Box>
    <Typography variant="body2"><strong>Hard Constraints:</strong> {constraints?.hard?.length || 0}</Typography>
    <Typography variant="body2"><strong>Soft Constraints:</strong> {constraints?.soft?.length || 0}</Typography>
  </Box>
);

const Step9Summary = ({ optimization }) => (
  <Box>
    <Typography variant="body2"><strong>Algorithm:</strong> {optimization?.algorithm || 'Not set'}</Typography>
    <Typography variant="body2"><strong>Max Time:</strong> {optimization?.maxTimeMinutes || 10} minutes</Typography>
    <Typography variant="body2"><strong>Objectives:</strong> {optimization?.objectives?.length || 0}</Typography>
  </Box>
);

export default SummaryAccordions;
```

---

### Sub-Component: ValidationPanel

**File**: `src/components/review/ValidationPanel.jsx`

```jsx
import React from 'react';
import {
  Card,
  CardHeader,
  CardContent,
  Typography,
  Alert,
  AlertTitle,
  List,
  ListItem,
  ListItemText,
  Button,
  Badge,
  Box
} from '@mui/material';
import { CheckCircle, Error as ErrorIcon, Warning } from '@mui/icons-material';

/**
 * Displays validation results with errors and warnings
 * Allows filtering and jumping to error locations
 */
const ValidationPanel = ({ results, onRevalidate }) => {
  if (!results) {
    return (
      <Card sx={{ mb: 3 }}>
        <CardContent>
          <Typography>Running validation...</Typography>
        </CardContent>
      </Card>
    );
  }

  const { valid, errors, warnings, stats } = results;

  return (
    <Card sx={{ mb: 3 }}>
      <CardHeader
        title="Validation Results"
        action={
          <Button size="small" onClick={onRevalidate}>
            Revalidate
          </Button>
        }
      />
      <CardContent>
        {/* Success State */}
        {valid && errors.length === 0 && (
          <Alert severity="success" icon={<CheckCircle />}>
            <AlertTitle>All Validations Passed!</AlertTitle>
            <Typography variant="body2">
              Your configuration is valid and ready to download.
            </Typography>
            {stats && (
              <Box sx={{ mt: 1 }}>
                <Typography variant="caption">
                  {stats.totalEmployees} employees • {stats.totalContracts} contracts •
                  {stats.totalWorkPeriods} work periods • {stats.dateRange} days
                </Typography>
              </Box>
            )}
          </Alert>
        )}

        {/* Errors */}
        {errors && errors.length > 0 && (
          <Alert severity="error" icon={<ErrorIcon />} sx={{ mb: 2 }}>
            <AlertTitle>
              <Badge badgeContent={errors.length} color="error">
                Errors Found
              </Badge>
            </AlertTitle>
            <List dense>
              {errors.map((err, i) => (
                <ListItem key={i} sx={{ pl: 0 }}>
                  <ListItemText
                    primary={err.message}
                    secondary={`Location: Step ${err.step}${err.field ? ` - ${err.field}` : ''}`}
                  />
                </ListItem>
              ))}
            </List>
            <Typography variant="caption" color="text.secondary">
              Fix these errors to enable file download.
            </Typography>
          </Alert>
        )}

        {/* Warnings */}
        {warnings && warnings.length > 0 && (
          <Alert severity="warning" icon={<Warning />}>
            <AlertTitle>
              <Badge badgeContent={warnings.length} color="warning">
                Warnings
              </Badge>
            </AlertTitle>
            <List dense>
              {warnings.map((warn, i) => (
                <ListItem key={i} sx={{ pl: 0 }}>
                  <ListItemText
                    primary={warn.message}
                    secondary={`Location: Step ${warn.step}${warn.field ? ` - ${warn.field}` : ''}`}
                  />
                </ListItem>
              ))}
            </List>
            <Typography variant="caption" color="text.secondary">
              Warnings don't prevent file download, but you should review them.
            </Typography>
          </Alert>
        )}
      </CardContent>
    </Card>
  );
};

export default ValidationPanel;
```

---

### Sub-Component: PreviewTabs

**File**: `src/components/review/PreviewTabs.jsx`

```jsx
import React, { useState } from 'react';
import { Box, Tabs, Tab, Card, CardContent } from '@mui/material';
import JsonPreview from '../preview/JsonPreview';
import CsvPreview from '../preview/CsvPreview';

/**
 * Tabbed preview of generated files
 * - problem.json: Syntax-highlighted JSON
 * - demand.csv: Table view
 * - schedule_input.csv: Table view
 */
const PreviewTabs = ({ files }) => {
  const [activeTab, setActiveTab] = useState(0);

  return (
    <Card sx={{ mb: 3 }}>
      <Tabs value={activeTab} onChange={(e, v) => setActiveTab(v)}>
        <Tab label="problem.json" />
        <Tab label="demand.csv" />
        <Tab label="schedule_input.csv" />
      </Tabs>

      <CardContent>
        {activeTab === 0 && (
          <JsonPreview json={files.problemJson} />
        )}

        {activeTab === 1 && (
          <CsvPreview csv={files.demandCsv} filename="demand.csv" />
        )}

        {activeTab === 2 && (
          <CsvPreview csv={files.scheduleInputCsv} filename="schedule_input.csv" />
        )}
      </CardContent>
    </Card>
  );
};

export default PreviewTabs;
```

---

### Sub-Component: JsonPreview

**File**: `src/components/preview/JsonPreview.jsx`

```jsx
import React, { useState } from 'react';
import { Box, IconButton, Tooltip, Typography } from '@mui/material';
import { ContentCopy, Check } from '@mui/icons-material';

/**
 * Syntax-highlighted, collapsible JSON viewer
 */
const JsonPreview = ({ json }) => {
  const [copied, setCopied] = useState(false);

  const handleCopy = () => {
    navigator.clipboard.writeText(JSON.stringify(json, null, 2));
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };

  const jsonString = JSON.stringify(json, null, 2);

  return (
    <Box>
      <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', mb: 1 }}>
        <Typography variant="caption" color="text.secondary">
          {jsonString.split('\n').length} lines
        </Typography>
        <Tooltip title={copied ? "Copied!" : "Copy to clipboard"}>
          <IconButton onClick={handleCopy} size="small">
            {copied ? <Check color="success" /> : <ContentCopy />}
          </IconButton>
        </Tooltip>
      </Box>

      <Box
        component="pre"
        sx={{
          fontFamily: 'ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, monospace',
          fontSize: 12,
          lineHeight: 1.5,
          maxHeight: 500,
          overflow: 'auto',
          backgroundColor: '#1e1e1e',
          color: '#d4d4d4',
          p: 2,
          borderRadius: 1,
          '&::-webkit-scrollbar': {
            width: 8,
            height: 8
          },
          '&::-webkit-scrollbar-thumb': {
            backgroundColor: '#555',
            borderRadius: 4
          }
        }}
      >
        {jsonString}
      </Box>
    </Box>
  );
};

export default JsonPreview;
```

---

### Sub-Component: CsvPreview

**File**: `src/components/preview/CsvPreview.jsx`

```jsx
import React, { useMemo } from 'react';
import {
  Table,
  TableBody,
  TableCell,
  TableContainer,
  TableHead,
  TableRow,
  Typography,
  Box
} from '@mui/material';
import Papa from 'papaparse';

/**
 * Table preview of CSV content
 * Shows first 50 rows with scroll
 */
const CsvPreview = ({ csv, filename }) => {
  const parsed = useMemo(() => {
    return Papa.parse(csv, { header: true });
  }, [csv]);

  const { data, meta } = parsed;
  const displayRows = data.slice(0, 50);

  return (
    <Box>
      <Typography variant="caption" color="text.secondary" sx={{ mb: 1, display: 'block' }}>
        {data.length} rows • {meta.fields?.length} columns
        {data.length > 50 && ` (showing first 50 rows)`}
      </Typography>

      <TableContainer sx={{ maxHeight: 400, border: 1, borderColor: 'divider', borderRadius: 1 }}>
        <Table size="small" stickyHeader>
          <TableHead>
            <TableRow>
              {meta.fields?.map(field => (
                <TableCell
                  key={field}
                  sx={{
                    fontWeight: 'bold',
                    backgroundColor: 'grey.100',
                    whiteSpace: 'nowrap'
                  }}
                >
                  {field}
                </TableCell>
              ))}
            </TableRow>
          </TableHead>
          <TableBody>
            {displayRows.map((row, i) => (
              <TableRow key={i} hover>
                {meta.fields?.map(field => (
                  <TableCell key={field} sx={{ whiteSpace: 'nowrap' }}>
                    {row[field]}
                  </TableCell>
                ))}
              </TableRow>
            ))}
          </TableBody>
        </Table>
      </TableContainer>
    </Box>
  );
};

export default CsvPreview;
```

---

### Sub-Component: DownloadPanel

**File**: `src/components/review/DownloadPanel.jsx`

```jsx
import React, { useState } from 'react';
import {
  Card,
  CardContent,
  Typography,
  Button,
  Stack,
  Divider,
  CircularProgress
} from '@mui/material';
import { Download, ContentCopy } from '@mui/icons-material';
import JSZip from 'jszip';
import { saveAs } from 'file-saver';

/**
 * Download buttons for individual files and ZIP bundle
 */
const DownloadPanel = ({ files, problemId }) => {
  const [downloading, setDownloading] = useState(false);

  const downloadJson = () => {
    const blob = new Blob(
      [JSON.stringify(files.problemJson, null, 2)],
      { type: 'application/json' }
    );
    saveAs(blob, 'problem.json');
  };

  const downloadDemandCsv = () => {
    const blob = new Blob([files.demandCsv], { type: 'text/csv;charset=utf-8' });
    saveAs(blob, 'demand.csv');
  };

  const downloadScheduleInputCsv = () => {
    const blob = new Blob([files.scheduleInputCsv], { type: 'text/csv;charset=utf-8' });
    saveAs(blob, 'schedule_input.csv');
  };

  const downloadZip = async () => {
    try {
      setDownloading(true);
      const zip = new JSZip();

      zip.file('problem.json', JSON.stringify(files.problemJson, null, 2));
      zip.file('demand.csv', files.demandCsv);
      zip.file('schedule_input.csv', files.scheduleInputCsv);

      const blob = await zip.generateAsync({ type: 'blob' });
      const filename = `${problemId || 'problem'}_scheduling_problem.zip`;
      saveAs(blob, filename);
    } catch (error) {
      console.error('ZIP creation failed:', error);
      alert('Failed to create ZIP file. Try downloading individual files instead.');
    } finally {
      setDownloading(false);
    }
  };

  const copyJsonToClipboard = () => {
    navigator.clipboard.writeText(JSON.stringify(files.problemJson, null, 2));
    // Could add a snackbar notification here
  };

  return (
    <Card>
      <CardContent>
        <Typography variant="h6" gutterBottom>Download Files</Typography>

        <Stack spacing={2}>
          {/* Main ZIP Download */}
          <Button
            variant="contained"
            size="large"
            startIcon={downloading ? <CircularProgress size={20} /> : <Download />}
            onClick={downloadZip}
            disabled={downloading}
            fullWidth
          >
            {downloading ? 'Creating ZIP...' : 'Download as ZIP (Recommended)'}
          </Button>

          <Divider />

          {/* Individual Downloads */}
          <Typography variant="subtitle2" color="text.secondary">
            Individual Files
          </Typography>

          <Stack direction="row" spacing={1} flexWrap="wrap">
            <Button
              variant="outlined"
              size="small"
              onClick={downloadJson}
            >
              problem.json
            </Button>
            <Button
              variant="outlined"
              size="small"
              onClick={downloadDemandCsv}
            >
              demand.csv
            </Button>
            <Button
              variant="outlined"
              size="small"
              onClick={downloadScheduleInputCsv}
            >
              schedule_input.csv
            </Button>
          </Stack>

          <Divider />

          {/* Copy to Clipboard */}
          <Button
            variant="text"
            size="small"
            startIcon={<ContentCopy />}
            onClick={copyJsonToClipboard}
          >
            Copy JSON to Clipboard
          </Button>
        </Stack>
      </CardContent>
    </Card>
  );
};

export default DownloadPanel;
```

**Acceptance Criteria for Task 1.2**:
- [ ] Step 10 renders without errors
- [ ] Summary accordions show all steps
- [ ] Validation panel displays errors/warnings
- [ ] Preview tabs show all 3 files
- [ ] Download buttons work (ZIP + individual)
- [ ] Copy to clipboard works

---

## Task 1.3: Create Validation System (Day 2, 2-3 hours)

**Location**: `src/utils/validators/`

### Master Validator

**File**: `src/utils/validators/index.js`

```javascript
import { validateStep1 } from './step1Validator';
import { validateStep2 } from './step2Validator';
import { validateStep3 } from './step3Validator';
import { validateStep4 } from './step4Validator';
import { validateStep5 } from './step5Validator';
import { validateStep6 } from './step6Validator';
import { validateStep7 } from './step7Validator';
import { validateStep8 } from './step8Validator';
import { validateStep9 } from './step9Validator';
import { validateCrossStep } from './crossStepValidator';

/**
 * Central validation runner
 * Runs all step validators and returns consolidated results
 */
export function validateAll(state) {
  const errors = [];
  const warnings = [];

  // Run each step validator
  errors.push(...validateStep1(state));
  errors.push(...validateStep2(state));
  errors.push(...validateStep3(state));
  errors.push(...validateStep4(state));
  errors.push(...validateStep5(state));
  errors.push(...validateStep6(state));
  errors.push(...validateStep7(state));
  errors.push(...validateStep8(state));
  errors.push(...validateStep9(state));

  // Cross-step validations
  const crossStepIssues = validateCrossStep(state);
  errors.push(...crossStepIssues.errors);
  warnings.push(...crossStepIssues.warnings);

  return {
    valid: errors.length === 0,
    errors,
    warnings,
    stats: {
      totalEmployees: getEmployeeCount(state),
      totalContracts: state.contracts?.definitions?.length || 0,
      totalWorkPeriods: state.demand?.workPeriods?.length || 0,
      dateRange: state.temporalScope?.numDays || 0
    }
  };
}

function getEmployeeCount(state) {
  const employees = state.employees?.model === 'team'
    ? state.employees.simple
    : state.employees.competency;
  return employees?.length || 0;
}

/**
 * Error object structure
 */
export function createError(step, field, message, severity = 'error') {
  return {
    step,
    field,
    message,
    severity, // 'error' | 'warning'
    timestamp: new Date().toISOString()
  };
}
```

---

### Step Validators (Examples)

**File**: `src/utils/validators/step1Validator.js`

```javascript
import { createError } from './index';

export function validateStep1(state) {
  const errors = [];

  // Metadata validation
  if (!state.metadata?.problemId?.trim()) {
    errors.push(createError(1, 'metadata.problemId', 'Problem ID is required'));
  }

  // Temporal scope validation
  if (!state.temporalScope?.year) {
    errors.push(createError(1, 'temporalScope.year', 'Year is required'));
  }

  if (!state.temporalScope?.numDays || state.temporalScope.numDays < 1) {
    errors.push(createError(1, 'temporalScope.numDays', 'Number of days must be at least 1'));
  }

  if (!state.temporalScope?.targetPeriod?.start) {
    errors.push(createError(1, 'temporalScope.targetPeriod.start', 'Start date is required'));
  }

  if (!state.temporalScope?.targetPeriod?.end) {
    errors.push(createError(1, 'temporalScope.targetPeriod.end', 'End date is required'));
  }

  // Employee model validation
  if (!state.employees?.model) {
    errors.push(createError(1, 'employees.model', 'Employee model must be selected (team or competency)'));
  }

  return errors;
}
```

**File**: `src/utils/validators/step2Validator.js`

```javascript
import { createError } from './index';

export function validateStep2(state) {
  const errors = [];
  const { definitions } = state.contracts || {};

  if (!definitions || definitions.length === 0) {
    errors.push(createError(2, 'contracts.definitions', 'At least one contract definition is required'));
    return errors;
  }

  const contractIds = new Set();
  definitions.forEach((contract, index) => {
    // Unique ID check
    if (contractIds.has(contract.id)) {
      errors.push(createError(
        2,
        `contracts.definitions[${index}].id`,
        `Duplicate contract ID: ${contract.id}`
      ));
    }
    contractIds.add(contract.id);

    // Required fields
    if (!contract.id?.trim()) {
      errors.push(createError(2, `contracts.definitions[${index}].id`, 'Contract ID is required'));
    }

    if (!contract.name?.trim()) {
      errors.push(createError(2, `contracts.definitions[${index}].name`, 'Contract name is required'));
    }

    // Work hours validation
    if (contract.workHoursPerDay == null) {
      errors.push(createError(2, `contracts.definitions[${index}].workHoursPerDay`, 'Work hours per day is required'));
    } else if (contract.workHoursPerDay < 0 || contract.workHoursPerDay > 24) {
      errors.push(createError(
        2,
        `contracts.definitions[${index}].workHoursPerDay`,
        `Invalid work hours for contract ${contract.id}: must be 0-24`
      ));
    }

    // Constraint validation
    if (contract.constraints) {
      const { weekendsOnly, weekdaysOnly } = contract.constraints;
      if (weekendsOnly && weekdaysOnly) {
        errors.push(createError(
          2,
          `contracts.definitions[${index}].constraints`,
          `Contract ${contract.id}: weekendsOnly and weekdaysOnly are mutually exclusive`
        ));
      }
    }
  });

  return errors;
}
```

**File**: `src/utils/validators/crossStepValidator.js`

```javascript
import { createError } from './index';

export function validateCrossStep(state) {
  const errors = [];
  const warnings = [];

  // 1. Employee contract references must exist
  const contractIds = new Set((state.contracts?.definitions || []).map(c => c.id));
  const employees = state.employees?.model === 'team'
    ? state.employees.simple
    : state.employees.competency;

  (employees || []).forEach((emp, i) => {
    if (emp.contractType && !contractIds.has(emp.contractType)) {
      errors.push(createError(
        4,
        `employees[${i}].contractType`,
        `Employee ${emp.id} references non-existent contract: ${emp.contractType}`
      ));
    }
  });

  // 2. Demand team references must exist
  const teamSet = new Set(state.organizationalUnits?.teams || []);
  const demandData = state.demand?.demandData || [];

  demandData.forEach((entry, i) => {
    if (!teamSet.has(entry.team)) {
      errors.push(createError(
        7,
        `demand.demandData[${i}].team`,
        `Demand entry references non-existent team: ${entry.team}`
      ));
    }
  });

  // 3. Schedule input employees must exist
  const employeeIds = new Set((employees || []).map(e => e.id));
  const scheduleMatrix = state.scheduleInput?.dataMatrix || {};

  Object.keys(scheduleMatrix).forEach(empId => {
    if (!employeeIds.has(empId)) {
      warnings.push(createError(
        5,
        'scheduleInput.dataMatrix',
        `Schedule contains data for non-existent employee: ${empId}`,
        'warning'
      ));
    }
  });

  // 4. Employees using 'A' must have contracts with workHoursPerDay
  const contractMap = new Map(
    (state.contracts?.definitions || []).map(c => [c.id, c])
  );

  Object.entries(scheduleMatrix).forEach(([empId, dates]) => {
    Object.entries(dates).forEach(([date, value]) => {
      if (value === 'A') {
        const emp = (employees || []).find(e => e.id === empId);
        if (emp) {
          const contract = contractMap.get(emp.contractType);
          if (!contract || contract.workHoursPerDay == null) {
            errors.push(createError(
              5,
              `scheduleInput.dataMatrix[${empId}][${date}]`,
              `Employee ${empId} uses 'A' on ${date} but has no contract with workHoursPerDay`
            ));
          }
        }
      }
    });
  });

  // 5. Work period references in demand must exist
  const workPeriodCodes = new Set((state.demand?.workPeriods || []).map(wp => wp.code));

  demandData.forEach((entry, i) => {
    if (!workPeriodCodes.has(entry.workPeriod)) {
      errors.push(createError(
        7,
        `demand.demandData[${i}].workPeriod`,
        `Demand entry references non-existent work period: ${entry.workPeriod}`
      ));
    }
  });

  return { errors, warnings };
}
```

**Acceptance Criteria for Task 1.3**:
- [ ] All step validators implemented
- [ ] Cross-step validation catches invalid references
- [ ] Error objects have consistent structure
- [ ] Warnings don't block generation
- [ ] Unit tests cover major validation cases

---

## Task 1.4: Build Schedule Input Matrix (Day 3-4, 12-16 hours)

**This is the most complex UI component in the entire wizard.**

**Location**: `src/steps/Step5_ScheduleInput.jsx`

### Main Component

**File**: `src/steps/Step5_ScheduleInput.jsx`

```jsx
import React, { useState, useEffect, useMemo } from 'react';
import { Typography, Box, Alert } from '@mui/material';
import StepCard from '../components/wizard/StepCard';
import NavigationButtons from '../components/wizard/NavigationButtons';
import MatrixToolbar from '../components/scheduleInput/MatrixToolbar';
import ScheduleMatrix from '../components/scheduleInput/ScheduleMatrix';
import MatrixLegend from '../components/scheduleInput/MatrixLegend';
import MarkingTypesDialog from '../components/scheduleInput/MarkingTypesDialog';
import { useWizard } from '../context/WizardContext';
import { generateDateRange } from '../utils/helpers/dateHelpers';
import { parseScheduleInputCsv } from '../utils/parsers/scheduleInputCsvParser';
import { generateScheduleInputCsv } from '../utils/generators/scheduleInputCsvGenerator';
import { getDefaultMarkingTypes } from '../utils/helpers/markingTypesHelpers';

const Step5_ScheduleInput = () => {
  const { state, updateState } = useWizard();

  const [dataMatrix, setDataMatrix] = useState(state.scheduleInput?.dataMatrix || {});
  const [markingTypes, setMarkingTypes] = useState(
    state.scheduleInput?.markingTypes || getDefaultMarkingTypes()
  );
  const [selectedCell, setSelectedCell] = useState(null);
  const [markingTypesDialogOpen, setMarkingTypesDialogOpen] = useState(false);
  const [error, setError] = useState('');

  const employees = state.employees?.model === 'team'
    ? state.employees.simple
    : state.employees.competency;

  const dateRange = useMemo(() => {
    if (!state.temporalScope?.targetPeriod) return [];
    return generateDateRange(
      state.temporalScope.targetPeriod.start,
      state.temporalScope.targetPeriod.end
    );
  }, [state.temporalScope]);

  // Save to context on change (debounced)
  useEffect(() => {
    const timeout = setTimeout(() => {
      updateState('scheduleInput.dataMatrix', dataMatrix);
      updateState('scheduleInput.markingTypes', markingTypes);
    }, 500);

    return () => clearTimeout(timeout);
  }, [dataMatrix, markingTypes]);

  const handleCellChange = (employeeId, date, value) => {
    setDataMatrix(prev => ({
      ...prev,
      [employeeId]: {
        ...(prev[employeeId] || {}),
        [date]: value
      }
    }));
  };

  const handleImportCsv = (csvContent) => {
    try {
      const parsed = parseScheduleInputCsv(csvContent);
      if (parsed.errors.length > 0) {
        setError(`CSV import errors: ${parsed.errors.join(', ')}`);
        return;
      }
      setDataMatrix(parsed.matrix);
      setError('');
    } catch (err) {
      setError(`Failed to import CSV: ${err.message}`);
    }
  };

  const handleExportCsv = () => {
    const csv = generateScheduleInputCsv(employees || [], dataMatrix, state.temporalScope);

    // Download CSV
    const blob = new Blob([csv], { type: 'text/csv;charset=utf-8' });
    const url = URL.createObjectURL(blob);
    const link = document.createElement('a');
    link.href = url;
    link.download = 'schedule_input.csv';
    link.click();
    URL.revokeObjectURL(url);
  };

  const handleClearAll = () => {
    if (confirm('Clear all schedule input data? This cannot be undone.')) {
      setDataMatrix({});
    }
  };

  const validate = () => {
    if (!employees || employees.length === 0) {
      setError('Please add employees in Step 4 first');
      return false;
    }
    if (dateRange.length === 0) {
      setError('Please configure temporal scope in Step 1 first');
      return false;
    }
    return true;
  };

  const handleNext = () => validate();

  if (!employees || employees.length === 0) {
    return (
      <Box sx={{ height: 'calc(100vh - 280px)', display: 'flex', flexDirection: 'column' }}>
        <Box sx={{ flexShrink: 0, mb: 2 }}>
          <Typography variant="h4" gutterBottom fontWeight={600}>
            Schedule Input Matrix
          </Typography>
        </Box>
        <Box sx={{ flexGrow: 1 }}>
          <StepCard>
            <Alert severity="warning">
              Please add employees in Step 4 before configuring schedule input.
            </Alert>
          </StepCard>
        </Box>
        <Box sx={{ flexShrink: 0, mt: 2 }}>
          <NavigationButtons />
        </Box>
      </Box>
    );
  }

  return (
    <Box sx={{ height: 'calc(100vh - 280px)', display: 'flex', flexDirection: 'column' }}>
      <Box sx={{ flexShrink: 0, mb: 2 }}>
        <Typography variant="h4" gutterBottom fontWeight={600}>
          Schedule Input Matrix
        </Typography>
        <Typography variant="body2" color="text.secondary">
          Define work requirements and availability constraints for each employee and date.
        </Typography>
      </Box>

      {error && (
        <Alert severity="error" onClose={() => setError('')} sx={{ mb: 2 }}>
          {error}
        </Alert>
      )}

      <Box sx={{ flexGrow: 1, overflow: 'auto' }}>
        <StepCard>
          <MatrixToolbar
            onImport={handleImportCsv}
            onExport={handleExportCsv}
            onDefineMarkings={() => setMarkingTypesDialogOpen(true)}
            onClearAll={handleClearAll}
          />

          <MatrixLegend markingTypes={markingTypes} />

          <ScheduleMatrix
            employees={employees}
            dateRange={dateRange}
            dataMatrix={dataMatrix}
            markingTypes={markingTypes}
            onCellChange={handleCellChange}
            selectedCell={selectedCell}
            onCellSelect={setSelectedCell}
          />
        </StepCard>
      </Box>

      <Box sx={{ flexShrink: 0, mt: 2 }}>
        <NavigationButtons onNext={handleNext} />
      </Box>

      <MarkingTypesDialog
        open={markingTypesDialogOpen}
        markingTypes={markingTypes}
        onChange={setMarkingTypes}
        onClose={() => setMarkingTypesDialogOpen(false)}
      />
    </Box>
  );
};

export default Step5_ScheduleInput;
```

---

### Matrix Sub-Components

Due to length constraints, I'll provide the key components with abbreviated implementations. Full implementations would be provided during actual development.

**File**: `src/components/scheduleInput/ScheduleMatrix.jsx`

```jsx
import React, { useRef, useEffect } from 'react';
import { Box, Table, TableBody, TableCell, TableContainer, TableHead, TableRow } from '@mui/material';
import MatrixCell from './MatrixCell';
import { formatDateHeader } from '../../utils/helpers/dateHelpers';

const ScheduleMatrix = ({
  employees,
  dateRange,
  dataMatrix,
  markingTypes,
  onCellChange,
  selectedCell,
  onCellSelect
}) => {
  const matrixRef = useRef(null);

  // Keyboard navigation
  useEffect(() => {
    const handleKeyDown = (e) => {
      if (!selectedCell) return;

      const { employeeId, date } = selectedCell;
      const empIndex = employees.findIndex(e => e.id === employeeId);
      const dateIndex = dateRange.indexOf(date);

      let newEmpIndex = empIndex;
      let newDateIndex = dateIndex;

      switch (e.key) {
        case 'ArrowRight':
          newDateIndex = Math.min(dateIndex + 1, dateRange.length - 1);
          break;
        case 'ArrowLeft':
          newDateIndex = Math.max(dateIndex - 1, 0);
          break;
        case 'ArrowDown':
          newEmpIndex = Math.min(empIndex + 1, employees.length - 1);
          break;
        case 'ArrowUp':
          newEmpIndex = Math.max(empIndex - 1, 0);
          break;
        case 'Delete':
        case 'Backspace':
          e.preventDefault();
          onCellChange(employeeId, date, '');
          return;
        default:
          return;
      }

      if (newEmpIndex !== empIndex || newDateIndex !== dateIndex) {
        e.preventDefault();
        onCellSelect({
          employeeId: employees[newEmpIndex].id,
          date: dateRange[newDateIndex]
        });
      }
    };

    document.addEventListener('keydown', handleKeyDown);
    return () => document.removeEventListener('keydown', handleKeyDown);
  }, [selectedCell, employees, dateRange, onCellChange, onCellSelect]);

  return (
    <TableContainer
      ref={matrixRef}
      sx={{
        maxHeight: '60vh',
        overflow: 'auto',
        border: 1,
        borderColor: 'divider',
        borderRadius: 1
      }}
    >
      <Table size="small" stickyHeader>
        <TableHead>
          <TableRow>
            <TableCell
              sx={{
                position: 'sticky',
                left: 0,
                zIndex: 3,
                backgroundColor: 'background.paper',
                fontWeight: 'bold',
                minWidth: 120
              }}
            >
              Employee ID
            </TableCell>
            {dateRange.map(date => (
              <TableCell
                key={date}
                align="center"
                sx={{
                  position: 'sticky',
                  top: 0,
                  zIndex: 2,
                  backgroundColor: 'background.paper',
                  minWidth: 80,
                  fontWeight: 'bold',
                  fontSize: 11
                }}
              >
                {formatDateHeader(date)}
              </TableCell>
            ))}
          </TableRow>
        </TableHead>
        <TableBody>
          {employees.map(emp => (
            <TableRow key={emp.id} hover>
              <TableCell
                sx={{
                  position: 'sticky',
                  left: 0,
                  zIndex: 1,
                  backgroundColor: 'background.paper',
                  fontWeight: 'bold'
                }}
              >
                {emp.id}
              </TableCell>
              {dateRange.map(date => (
                <MatrixCell
                  key={`${emp.id}-${date}`}
                  employeeId={emp.id}
                  date={date}
                  value={dataMatrix[emp.id]?.[date] || ''}
                  markingTypes={markingTypes}
                  onChange={onCellChange}
                  selected={
                    selectedCell?.employeeId === emp.id &&
                    selectedCell?.date === date
                  }
                  onSelect={() => onCellSelect({ employeeId: emp.id, date })}
                />
              ))}
            </TableRow>
          ))}
        </TableBody>
      </Table>
    </TableContainer>
  );
};

export default ScheduleMatrix;
```

**File**: `src/components/scheduleInput/MatrixCell.jsx`

```jsx
import React, { useState, useEffect, useRef } from 'react';
import { TableCell, TextField, Typography } from '@mui/material';
import { getCellColor } from '../../utils/helpers/matrixHelpers';

const MatrixCell = ({
  employeeId,
  date,
  value,
  markingTypes,
  onChange,
  selected,
  onSelect
}) => {
  const [editing, setEditing] = useState(false);
  const [tempValue, setTempValue] = useState(value);
  const inputRef = useRef(null);

  const cellColor = getCellColor(value, markingTypes);

  useEffect(() => {
    setTempValue(value);
  }, [value]);

  useEffect(() => {
    if (editing && inputRef.current) {
      inputRef.current.focus();
      inputRef.current.select();
    }
  }, [editing]);

  const handleDoubleClick = () => {
    setEditing(true);
  };

  const handleBlur = () => {
    setEditing(false);
    if (tempValue !== value) {
      onChange(employeeId, date, tempValue);
    }
  };

  const handleKeyDown = (e) => {
    if (e.key === 'Enter') {
      e.preventDefault();
      setEditing(false);
      onChange(employeeId, date, tempValue);
    } else if (e.key === 'Escape') {
      setEditing(false);
      setTempValue(value);
    }
  };

  const handleClick = (e) => {
    onSelect();
    if (e.detail === 2) { // Double click
      setEditing(true);
    }
  };

  return (
    <TableCell
      onClick={handleClick}
      align="center"
      sx={{
        backgroundColor: cellColor,
        border: selected ? '2px solid' : '1px solid',
        borderColor: selected ? 'primary.main' : 'divider',
        padding: '2px',
        cursor: 'pointer',
        transition: 'all 0.2s',
        '&:hover': {
          backgroundColor: cellColor ? `${cellColor}dd` : 'action.hover',
          borderColor: 'primary.light'
        },
        minWidth: 80,
        maxWidth: 80
      }}
    >
      {editing ? (
        <TextField
          ref={inputRef}
          size="small"
          value={tempValue}
          onChange={(e) => setTempValue(e.target.value)}
          onBlur={handleBlur}
          onKeyDown={handleKeyDown}
          sx={{
            width: '100%',
            '& .MuiInputBase-root': {
              fontSize: 12
            },
            '& .MuiInputBase-input': {
              padding: '2px 4px',
              textAlign: 'center'
            }
          }}
        />
      ) : (
        <Typography variant="body2" sx={{ fontSize: 12, fontWeight: value ? 'bold' : 'normal' }}>
          {value || '-'}
        </Typography>
      )}
    </TableCell>
  );
};

export default MatrixCell;
```

**File**: `src/utils/helpers/matrixHelpers.js`

```javascript
/**
 * Determine cell background color based on value type
 */
export function getCellColor(value, markingTypes) {
  if (!value) return null;

  // Work requirements (A, numbers)
  if (value === 'A') return '#c8e6c9'; // Light green
  if (/^\d+$/.test(value)) {
    const hours = parseInt(value);
    if (hours >= 1 && hours <= 16) return '#a5d6a7'; // Green
    return '#ffcdd2'; // Red for invalid
  }

  // Standard constraints
  if (value === 'VAC') return '#fff9c4'; // Light yellow
  if (value === 'NOT') return '#ffcdd2'; // Light red

  // Time window constraints
  if (value.startsWith('EQUALS:') || value.startsWith('INCLUDE:') || value.startsWith('EXCEPT:')) {
    return '#bbdefb'; // Light blue
  }

  // Custom markings
  if (markingTypes[value]) {
    return '#e1bee7'; // Light purple
  }

  // Unknown value
  return '#f5f5f5'; // Light gray
}
```

**File**: `src/utils/helpers/markingTypesHelpers.js`

```javascript
/**
 * Get default marking types for schedule input
 */
export function getDefaultMarkingTypes() {
  return {
    'A': 'Auto-allocate hours from contract (work requirement)',
    'VAC': 'Vacation (standard constraint - always valid)',
    'NOT': 'Unavailable (standard constraint - always valid)',
    'EQUALS:HH:MM-HH:MM': 'Must work exactly this time range (v2.2)',
    'INCLUDE:HH:MM-HH:MM': 'Must cover this entire range minimum (v2.2)',
    'EXCEPT:HH:MM-HH:MM': 'Unavailable during this time window (v2.2)',
    'DL': 'Day off (custom constraint - must be defined)',
    'DLF': 'Fixed day off (custom constraint - must be defined)',
    'DLV': 'Variable day off (custom constraint - must be defined)'
  };
}
```

**Acceptance Criteria for Task 1.4**:
- [ ] Matrix renders with sticky headers
- [ ] Cell editing works (click, type, enter)
- [ ] Keyboard navigation works (arrows, enter, delete)
- [ ] Color-coding works for all value types
- [ ] CSV import/export works
- [ ] Performance acceptable for 30 employees × 31 days

---

## PHASE 1 Summary

**Deliverable**: Working end-to-end wizard
- ✅ Users can complete all 11 steps
- ✅ Step 10 generates problem.json + 2 CSVs
- ✅ Download as ZIP or individual files
- ✅ Validation shows errors/warnings
- ✅ Preview tabs show generated files
- ✅ Schedule matrix works for basic use cases

**Time Estimate**: 3-4 days (24-32 hours)

**Testing Checklist**:
- [ ] Complete wizard with team model
- [ ] Complete wizard with competency model
- [ ] Generate files and validate with Python validator
- [ ] Import generated schedule_input.csv back into wizard
- [ ] Test with 100 employees × 365 days (performance)

---

# PHASE 2: Complete Steps 4-9 (Days 5-8)

## Objective
Ensure all wizard steps are fully functional with all planned features.

## Tasks Overview

| Task | Step | Est. Hours | Priority |
|------|------|------------|----------|
| 2.1 | Step 4: Employees CSV Import | 4-6 | High |
| 2.2 | Step 6: Work Periods Breaks | 3-4 | Medium |
| 2.3 | Step 8: Constraints UI | 4-6 | High |
| 2.4 | Step 9: Optimization Settings | 3-4 | Medium |

**Total**: 14-20 hours (2-3 days)

---

## Task 2.1: Complete Step 4 - Employees (Day 5, 4-6 hours)

### Add CSV Import Tab

See PLAN.md Section "Phase 2: Core Data Entry → Step 4: Employees" for full implementation details.

**Key Components**:
- `EmployeeCsvImporter.jsx` - File upload, preview, column mapping
- `ColumnMapper.jsx` - Map CSV columns to expected fields
- CSV parsing for team model: `employee_id,name,teams,contract_type`
- CSV parsing for competency model: `employee_id,name,competencies,contract_type`

**Acceptance Criteria**:
- [ ] CSV file upload works (drag-drop or button)
- [ ] Preview shows first 5 rows
- [ ] Column mapper auto-detects fields
- [ ] Validation catches errors before import
- [ ] Import adds employees to wizard state

---

## Task 2.2: Complete Step 6 - Work Periods (Day 5-6, 3-4 hours)

### Add Breaks Configuration

See PLAN.md Section "Phase 2 → Task 2.2" for full implementation details.

**Key Components**:
- `BreakBuilder.jsx` - List of breaks with add/edit/delete
- `BreakDialog.jsx` - Configure break (type, duration, timing, paid, required)
- Support 3 timing modes: fixed, window, after work

**Acceptance Criteria**:
- [ ] Can add/edit/delete breaks for work periods
- [ ] All timing modes work
- [ ] Validation prevents invalid configurations
- [ ] Breaks show in work period summary

---

## Task 2.3: Complete Step 8 - Constraints (Day 6-7, 4-6 hours)

### Add Constraint Configuration UI

See PLAN.md Section "Phase 2 → Task 2.3" for full implementation details.

**Key Components**:
- `ConstraintsList.jsx` - List of available constraints with toggle
- `ConstraintCard.jsx` - Individual constraint with parameters and weight slider
- Predefined constraints (hard: max_consecutive_days, min_rest_hours, etc.)
- Predefined constraints (soft: min_coverage, balance_workload, etc.)

**Acceptance Criteria**:
- [ ] All predefined constraints listed
- [ ] Toggle on/off works
- [ ] Parameter configuration works
- [ ] Soft constraint weight slider works

---

## Task 2.4: Complete Step 9 - Optimization (Day 7, 3-4 hours)

### Add Algorithm Selector and Objectives

See PLAN.md Section "Phase 2 → Task 2.4" for full implementation details.

**Key Components**:
- Algorithm selector with descriptions
- Time limit slider (1-60 minutes)
- `ObjectivesTable.jsx` - Add/edit/delete objectives
- `ObjectiveDialog.jsx` - Configure objective (goal, weight, priority)

**Acceptance Criteria**:
- [ ] Algorithm selector works
- [ ] Time slider works
- [ ] Can add/edit/delete objectives
- [ ] Validation ensures at least 1 objective

---

## PHASE 2 Summary

**Deliverable**: All steps fully functional
- ✅ Step 4: CSV import for employees
- ✅ Step 6: Breaks configuration
- ✅ Step 8: Full constraint configuration
- ✅ Step 9: Algorithm and objectives setup

**Time Estimate**: 3-4 days (24-32 hours)

---

# PHASE 3: Polish & Advanced Features (Days 9-11)

## Objective
Optimize performance, add advanced features, improve UX.

## Tasks Overview

| Task | Feature | Est. Hours | Priority |
|------|---------|------------|----------|
| 3.1 | Matrix Virtualization | 4-6 | High |
| 3.2 | Time Window Constraint Picker | 4-6 | Medium |
| 3.3 | Python Validator Integration | 3-4 | Low |
| 3.4 | Project Save/Load | 3-4 | Low |
| 3.5 | Dark Mode Support | 2-3 | Low |

**Total**: 16-23 hours (2-3 days)

---

## Task 3.1: Matrix Virtualization (Day 9, 4-6 hours)

**Problem**: 100 employees × 365 days = 36,500 cells causes performance issues

**Solution**: Use `react-window` for virtualization

See PLAN.md Section "Phase 3 → Task 3.1" for implementation details.

**Acceptance Criteria**:
- [ ] Renders 1000+ employees smoothly
- [ ] Scroll performance acceptable
- [ ] Sticky headers still work

---

## Task 3.2: Time Window Constraint Picker (Day 9-10, 4-6 hours)

Add visual time picker for EQUALS/INCLUDE/EXCEPT constraints.

See PLAN.md Section "Phase 3 → Task 3.2" for implementation details.

**Acceptance Criteria**:
- [ ] Time picker opens from cell
- [ ] All 3 modes work
- [ ] Validation ensures start < end
- [ ] Constraint saved in correct format

---

## Task 3.3: Python Validator Integration (Day 10, 3-4 hours)

Call backend Python validator for comprehensive validation.

**Requires backend endpoint**: `POST /api/validate-problem`

See PLAN.md Section "Phase 3 → Task 3.3" for implementation details.

**Acceptance Criteria**:
- [ ] Button in Step 10 to run Python validation
- [ ] Shows loading state
- [ ] Displays Python validator output
- [ ] Gracefully handles validation unavailable

---

## Task 3.4: Project Save/Load (Day 10-11, 3-4 hours)

Save/load projects from localStorage.

See PLAN.md Section "Phase 3 → Task 3.4" for implementation details.

**Acceptance Criteria**:
- [ ] Can save current wizard state
- [ ] Can load saved projects
- [ ] Can delete saved projects
- [ ] List shows project name and save date

---

## Task 3.5: Dark Mode Support (Day 11, 2-3 hours)

Add theme toggle for dark mode.

See PLAN.md Section "Phase 3 → Task 3.5" for implementation details.

**Acceptance Criteria**:
- [ ] Toggle switches between light/dark
- [ ] All components render correctly in both modes
- [ ] Preference saved to localStorage

---

## PHASE 3 Summary

**Deliverable**: Production-ready wizard
- ✅ Performance optimized
- ✅ Advanced features added
- ✅ QoL improvements implemented

**Time Estimate**: 2-3 days (16-24 hours)

---

# PHASE 4: Testing & Documentation (Days 12-13)

## Task 4.1: Unit Tests (Day 12, 4-6 hours)

**Test Coverage Goal**: 70%+

**Test Files**:
- `jsonGenerator.test.js`
- `demandCsvGenerator.test.js`
- `scheduleInputCsvGenerator.test.js`
- `validators/*.test.js`
- `matrixHelpers.test.js`

---

## Task 4.2: Integration Tests (Day 12, 2-3 hours)

Test complete wizard flow from Step 1 to Step 10.

---

## Task 4.3: Documentation (Day 13, 4-6 hours)

Create:
- User Guide (`USER_GUIDE.md`)
- Update Developer Guide (`DEVELOPMENT.md`)
- API documentation for generation utilities

---

## PHASE 4 Summary

**Deliverable**: Release candidate
- ✅ Unit tests (70%+ coverage)
- ✅ Integration tests
- ✅ Documentation complete
- ✅ Ready for production

**Time Estimate**: 1-2 days (8-16 hours)

---

# Success Criteria

## Functional Requirements
- [ ] All 11 steps functional
- [ ] Users can generate problem.json + CSVs
- [ ] Files validate with Python validator
- [ ] Schedule matrix handles 365 days × 100 employees
- [ ] CSV import/export works for all data types

## Technical Requirements
- [ ] 70%+ test coverage
- [ ] No console errors
- [ ] Passes accessibility checks
- [ ] Works on Chrome, Firefox, Safari, Edge
- [ ] Responsive design (tablet + desktop)

## Documentation
- [ ] User guide complete
- [ ] Developer guide updated
- [ ] All components documented
- [ ] README accurate

---

# Risk Management

## Risks & Mitigation

| Risk | Probability | Impact | Mitigation |
|------|-------------|--------|------------|
| Matrix performance issues | High | High | Implement virtualization early (Task 3.1) |
| Validation complexity | Medium | Medium | Start with basic rules, iterate |
| Scope creep | High | High | Stick to plan, phase 3 optional |
| CSV parsing edge cases | Medium | Low | Use PapaParse, add unit tests |
| Browser compatibility | Low | Medium | Test early, use polyfills |

---

# Implementation Checklist

## Before Starting
- [ ] Review existing Steps 4, 6, 8, 9 implementations
- [ ] Set up testing framework (Jest + React Testing Library)
- [ ] Install dependencies (jszip, file-saver, react-window)
- [ ] Confirm Python validator accessibility
- [ ] Get example problem files from users

## Phase 1 (Days 1-4)
- [ ] Task 1.1: Generation utilities
- [ ] Task 1.2: Step 10 UI
- [ ] Task 1.3: Validation system
- [ ] Task 1.4: Schedule matrix
- [ ] Test end-to-end flow

## Phase 2 (Days 5-8)
- [ ] Task 2.1: Step 4 CSV import
- [ ] Task 2.2: Step 6 breaks
- [ ] Task 2.3: Step 8 constraints
- [ ] Task 2.4: Step 9 optimization

## Phase 3 (Days 9-11)
- [ ] Task 3.1: Virtualization
- [ ] Task 3.2: Time picker
- [ ] Task 3.3: Python validator
- [ ] Task 3.4: Save/load
- [ ] Task 3.5: Dark mode

## Phase 4 (Days 12-13)
- [ ] Task 4.1: Unit tests
- [ ] Task 4.2: Integration tests
- [ ] Task 4.3: Documentation

---

# Questions for Clarification

Before implementation, clarify:

1. **Schema Version**: Target v2.2 or v2.5?
   - v2.5 adds operating hours (requires additional Step 11?)

2. **Existing Steps Audit**: Should I verify Steps 4, 6, 8, 9 completeness first?

3. **Performance**: What's typical problem size? (employees × days)

4. **Backend**: Is Python validator accessible via API?

5. **Priorities**: Any features to cut if timeline is tight?
   - Phase 3 features (virtualization, time picker, save/load) are optional
   - Could focus on getting Phase 1 + 2 working first

6. **Browser Support**: Any specific version requirements?

---

# Getting Started

## Recommended Approach

**Week 1** (Phase 1):
- Day 1: Generation utilities (Task 1.1)
- Day 2: Step 10 UI + validation (Tasks 1.2, 1.3)
- Days 3-4: Schedule matrix (Task 1.4)
- **Deliverable**: Working end-to-end flow

**Week 2** (Phase 2 + 3):
- Days 5-7: Complete Steps 4, 6, 8, 9
- Days 8-10: Add polish features
- **Deliverable**: All features complete

**Week 3** (Phase 4):
- Days 11-12: Testing
- Day 13: Documentation
- **Deliverable**: Release candidate

---

# Conclusion

This plan provides:
- ✅ **Clear phases** with dependencies
- ✅ **Detailed tasks** with acceptance criteria
- ✅ **Time estimates** per task
- ✅ **Risk mitigation** strategies
- ✅ **Testing strategy**
- ✅ **Success metrics**

**Total Estimate**: 9-13 days (72-104 hours)

**Critical Path**: Generation utilities → Step 10 → Schedule matrix → Complete remaining steps

**Ready to implement!** Let me know when you want to start, and which phase to prioritize.

---

**Document Version**: 1.0
**Created**: 2026-04-21
**Last Updated**: 2026-04-21
**Status**: Ready for Implementation
