# JSON Generator - Comprehensive Implementation Plan

**Project**: User-Friendly Frontend Wizard for Schema v2.2 JSON + CSV Generation
**Status**: Phase 1 Complete ✅ | Phase 2 In Progress 🔄
**Total Steps**: 11 (reorganized on Feb 4, 2026)
**Last Updated**: February 4, 2026

---

## 📋 Table of Contents

1. [Project Overview](#project-overview)
2. [Architecture](#architecture)
3. [Phase 1: Foundation](#phase-1-foundation-completed-)
4. [Current UI Improvements](#current-ui-improvements-completed-)
5. [Phase 2: Core Data Entry](#phase-2-core-data-entry-next-)
6. [Phase 3: Scheduling Components](#phase-3-scheduling-components)
7. [Phase 4: Configuration](#phase-4-configuration)
8. [Phase 5: Generation & Polish](#phase-5-generation--polish)
9. [Technical Decisions](#technical-decisions)
10. [Future Enhancements](#future-enhancements)

---

## Project Overview

### Goal
Create an intuitive, step-by-step wizard that guides users through generating schema v2.2 JSON + CSV pairs for employee scheduling problems, eliminating the need for manual JSON/CSV editing.

### Key Features
- ✅ **11-Step Wizard**: Progressive disclosure of complexity (reorganized Feb 4, 2026)
- ✅ **Visual Model Selection**: Dedicated step with card-based selection for employee models
- ✅ **Validation**: Real-time validation with clear error messages
- ✅ **Auto-Save**: Persistent state in localStorage
- ✅ **Responsive**: Works on tablets and desktops
- ✅ **Customizable**: Editable theme configuration
- 🔄 **CSV Import**: Import employees and other data
- 🔄 **Preview & Download**: Preview generated files before download
- 🔄 **Python Validator**: Integration with existing validator.py

### Non-Goals
- Backend integration (generates files client-side only)
- Schedule solving (that's handled by existing scheduler)
- Multi-user collaboration (single-user tool)

---

## Architecture

### Tech Stack
- **Frontend**: React 18 + Vite
- **UI Library**: Material-UI v7 (consistent with main app)
- **Styling**: MUI + Tailwind CSS
- **State**: React Context API + localStorage
- **Routing**: React Router v6
- **Dates**: date-fns v2.30.0 (compatible with MUI DatePickers)
- **CSV**: PapaParse (for import/export)
- **Downloads**: file-saver + JSZip

### Project Structure
```
src/json-generator/
├── src/
│   ├── components/
│   │   ├── wizard/          # Reusable wizard components
│   │   ├── tables/          # Data table components
│   │   ├── calendar/        # Calendar/matrix components
│   │   ├── import/          # CSV import components
│   │   ├── validation/      # Validation display components
│   │   ├── preview/         # Preview components
│   │   └── forms/           # Dialog forms
│   ├── context/
│   │   └── WizardContext.jsx    # Central state management
│   ├── steps/               # 10 wizard steps
│   ├── utils/
│   │   ├── generators/      # JSON/CSV generation logic
│   │   ├── validators/      # Client-side validation
│   │   ├── parsers/         # CSV/JSON parsing
│   │   ├── featureDetector.js # Auto-detect feature flags
│   │   └── helpers/         # Utility functions
│   ├── hooks/               # Custom React hooks
│   ├── theme.config.js      # 🎨 Editable theme colors
│   ├── theme.js             # MUI theme setup
│   └── App.jsx              # Main app
├── package.json
├── vite.config.js
├── README.md
└── PLAN.md (this file)
```

### State Management
**WizardContext** manages all wizard state:
```javascript
{
  currentStep: 0-10,  // 11 steps total (updated Feb 4, 2026)
  stepCompleted: { 0: false, 1: false, ..., 10: false },
  metadata: { problemId, createdAt, description },
  features: { useWorkPeriodBasedScheduling, ... },
  temporalScope: { year, numDays, targetPeriod },
  contracts: { definitions: [...] },
  employees: { model, simple/competency: [...] },  // model now selected in Step 2
  organizationalUnits: { teams/competencies: [...] },
  scheduleInput: { dataMatrix, markingTypes },
  demand: { workPeriodModel, shifts, demandData },
  constraints: { hard, soft, advanced },
  optimization: { algorithm, maxTimeMinutes, objectives }
}
```

**Current Step Structure (11 steps)**:
1. Quick Setup - Metadata & temporal scope (merged card)
2. Employee Model - Visual card-based selection (NEW)
3. Contracts - Contract types
4. Organizational Units - Teams/Competencies
5. Employees - Employee roster
6. Schedule Input - Availability matrix
7. Shifts - Shift definitions
8. Demand - Coverage requirements
9. Constraints - Rules & constraints
10. Optimization - Solver settings
11. Review & Generate - Preview and download

Auto-saves to `localStorage` every 1 second (debounced).

---

## Phase 1: Foundation (COMPLETED ✅)

### Deliverables
- [x] Project setup (Vite + React + MUI + Tailwind)
- [x] Editable theme configuration (`theme.config.js`)
- [x] WizardContext with full state structure
- [x] WizardStepper navigation component
- [x] Reusable components (StepCard, NavigationButtons)
- [x] Step 1: Quick Setup (fully functional)
- [x] Step 2: Contracts (fully functional)
- [x] Placeholder steps 3-10
- [x] Auto-save functionality
- [x] Docker integration
- [x] Nginx routing (`/json-gen/`)

### Step 1: Quick Setup ✅
**Completed Features**:
- Problem metadata (ID, description, creation date)
- Temporal scope (year, numDays, date range with auto-calculation)
- Employee model selection (Team vs Competency) - **critical decision point**
- Full validation with inline error messages

**Recent Changes (Feb 4, 2026)**:
- ✅ **Removed feature flags** from Step 1 UI (UX improvement)
- ✅ Feature flags now **auto-detected** based on configuration in later steps
- ✅ Created `src/utils/featureDetector.js` for automatic feature detection

### Step 2: Contracts ✅
**Completed Features**:
- Add/Edit/Delete contract types
- Contract fields: ID, Name, Work Hours Per Day
- Optional constraints:
  - Weekends/Weekdays only
  - Available days
  - Max hours per week
  - Max consecutive days
  - Min rest days per week
  - Flexible hours flag
- Table view with chips showing active constraints
- Form validation (unique IDs, valid hour ranges, mutually exclusive constraints)

---

## Current UI Improvements (COMPLETED ✅)

### Recent Fixes (Feb 4, 2026)
1. **Header Full Width** ✅
   - Removed container restriction
   - Added 2px solid bottom border
   - Full viewport width

2. **Step 1 Layout Consistency** ✅
   - Fixed inconsistent grid sizing
   - Year: 4 cols, NumDays: 4 cols, Empty: 4 cols
   - Start/End dates: 6 cols each
   - Removed "Buffer Weeks" checkbox (moved to future Step 5)
   - Added responsive breakpoints (xs, sm, md)

3. **Buffer Weeks Removal** ✅
   - Removed from Step 1 temporal scope
   - Removed from WizardContext initialState
   - Will be added to Step 5 (Schedule Input) in future

4. **Date-fns Compatibility** ✅
   - Downgraded from v3 to v2.30.0 for MUI compatibility

5. **Vite Base Path** ✅
   - Configured `base: '/json-gen/'` for nginx routing

6. **Feature Flags Auto-Detection** ✅ (NEW)
   - Removed feature flags section from Step 1 UI
   - Implemented automatic feature detection based on later steps
   - Created `src/utils/featureDetector.js` utility
   - Updated WizardContext to auto-detect features on export
   - Cleaner, simpler Step 1 UX

---

## Phase 2: Core Data Entry (NEXT 🔄)

### Step 3: Organizational Units
**Status**: Placeholder  
**Priority**: HIGH  
**Dependencies**: Step 1 (model selection)

**Implementation Plan**:

**If Team Model**:
- Simple text input + "Add" button
- Chip list showing all teams with delete buttons
- Drag-to-reorder chips (optional)
- Validation: unique team codes, at least 1 team

**If Competency Model**:
- Table with columns: Code, Name, Actions
- "Add Competency" button → Dialog
- Dialog: Code (text), Name (text)
- Validation: unique codes, non-empty names, at least 1 competency

**UI Components Needed**:
- `TeamInput.jsx` - chip input component
- `CompetencyTable.jsx` - table with add/edit/delete
- Conditional rendering based on `state.employees.model`

**Validation**:
- At least 1 team/competency required
- Unique codes
- Non-empty names
- No special characters in codes (alphanumeric + underscore)

**State Updates**:
```javascript
// Team model
updateState('organizationalUnits.teams', ['A', 'B', 'C']);

// Competency model
updateState('organizationalUnits.competencies', [
  {code: 'EG', name: 'Engineer'},
  {code: 'CAJ', name: 'Cashier'}
]);
```

---

### Step 4: Employees
**Status**: Placeholder  
**Priority**: HIGH  
**Dependencies**: Step 2 (contracts), Step 3 (org units)

**Implementation Plan**:

**Tabs**: "Manual Entry" | "Import CSV"

**Manual Entry Tab**:
- Table/DataGrid showing employees
- Columns (Team Model): ID, Name, Teams, Contract Type, Actions
- Columns (Competency Model): ID, Name, Competencies, Contract Type, Actions
- "Add Employee" button → Dialog

**Add/Edit Employee Dialog**:
- TextField: Employee ID (required, unique)
- TextField: Employee Name (optional but recommended)
- **Team Model**:
  - Autocomplete (multi-select): Teams (from Step 3)
  - Validation: at least 1 team
- **Competency Model**:
  - Competency builder:
    - Select: Competency Code (from Step 3)
    - TextField: Level (integer, 1+)
    - Button: Add Competency
    - List: Current competencies with delete
  - Validation: at least 1 competency
- Select: Contract Type (from Step 2)
- Accordion: Contract Periods (advanced, optional)

**Import CSV Tab**:
- File upload (drag-drop or button)
- CSV preview table
- Column mapping UI:
  - Map CSV columns to: employee_id, name, teams/competencies, contract_type
- Validation before import
- Import button

**UI Components Needed**:
- `EmployeeTable.jsx` - main table
- `EmployeeForm.jsx` - add/edit dialog
- `CompetencyBuilder.jsx` - competency selector with levels
- `CSVImporter.jsx` - reusable CSV import component
- `CSVPreview.jsx` - preview table
- `ColumnMapper.jsx` - map CSV columns to fields

**Validation**:
- Unique employee IDs
- At least 1 employee required
- Valid contract references (must exist in Step 2)
- Valid team/competency references (must exist in Step 3)
- At least 1 team/competency per employee
- Level values must be positive integers

**CSV Format Examples**:

*Team Model CSV*:
```csv
employee_id,name,teams,contract_type
EMP001,John Doe,"A,B",fullTime_8h
EMP002,Jane Smith,A,partTime_4h
```

*Competency Model CSV*:
```csv
employee_id,name,competencies,contract_type
EMP001,John Doe,"EG:1,CAJ:2",fullTime_8h
EMP002,Jane Smith,EG:1,partTime_4h
```

**State Updates**:
```javascript
// Team model
updateState('employees.simple', [
  {id: 'EMP001', name: 'John', teams: ['A', 'B'], contractType: 'fullTime_8h'}
]);

// Competency model
updateState('employees.competency', [
  {
    id: 'EMP001',
    name: 'John',
    competencies: [{code: 'EG', level: 1}, {code: 'CAJ', level: 2}],
    contractType: 'fullTime_8h'
  }
]);
```

---

## Phase 3: Scheduling Components

### Step 5: Schedule Input Matrix
**Status**: Placeholder  
**Priority**: MEDIUM  
**Dependencies**: Step 1 (dates), Step 4 (employees)

**Implementation Plan**:

**Matrix Layout**:
- Rows: Employees (from Step 4)
- Columns: Dates (from Step 1 temporal scope)
- Sticky header row (dates)
- Sticky first column (employee IDs)
- Virtualized scrolling for large datasets

**Cell Editing**:
- Click to edit
- Keyboard navigation (Tab, Arrow keys, Enter)
- Cell values:
  - "A" = auto-allocate from contract
  - 1-16 = specific hours
  - Marking types: VAC, DL, DLF, etc.
- Auto-complete dropdown for marking types
- Color coding by value type:
  - Green: A / numbers (available)
  - Yellow: VAC (vacation)
  - Red: DL/OFF (not available)
  - Blue: Custom markings

**Toolbar**:
- Button: "Define Custom Marking Types" → Dialog
- Select: Fill Mode (drag to apply same value to multiple cells)
- Button: "Import CSV"
- Button: "Export CSV"
- Button: "Clear All"
- Button: "Fill Week Pattern" (copy Mon-Fri pattern)

**Legend**:
- Color-coded legend showing all marking types
- Compact chips with tooltips

**Define Marking Types Dialog**:
- Table: Code, Description, Color, Actions
- Add marking type
- Edit existing
- Delete (except built-in A, VAC, DL)

**CSV Import/Export**:
- Export current matrix to schedule_input.csv
- Import from CSV (overwrites or merges)

**UI Components Needed**:
- `ScheduleMatrix.jsx` - main matrix component
- `MatrixCell.jsx` - editable cell with validation
- `MatrixToolbar.jsx` - toolbar with actions
- `MarkingTypesDialog.jsx` - manage marking types
- `MatrixLegend.jsx` - color legend

**Validation**:
- Valid cell values only (A, 1-16, or defined markings)
- Employees using "A" must have contract with workHoursPerDay
- Date columns must match temporal scope
- Warn if employee has no availability

**State Updates**:
```javascript
updateState('scheduleInput.dataMatrix', {
  'EMP001': {
    '2026-01-01': 'A',
    '2026-01-02': '8',
    '2026-01-03': 'VAC'
  }
});

updateState('scheduleInput.markingTypes', {
  'A': 'Auto-allocate from contract',
  'VAC': 'Vacation',
  'DL': 'Day off',
  'CUSTOM': 'Custom marking'
});
```

---

### Step 6: Work Periods Definition
**Status**: Placeholder  
**Priority**: MEDIUM  
**Dependencies**: Step 1 (features)

**Implementation Plan**:

**Work Period Model Selection**:
- Radio: Fixed vs Flexible
- Shows in Step 1 feature flags, but configurable here

**Shifts Table**:
- Columns: Code, Name, Order, Time/Duration, Breaks, Actions
- "Add Shift" button → Dialog

**Add/Edit Shift Dialog**:
- TextField: Code (required, unique, e.g., "M", "T", "N")
- TextField: Name (required, e.g., "Morning")
- TextField (number): Order (required, unique, 1=earliest)
- **If Fixed Model**:
  - TimePicker: Start Time (HH:MM)
  - TimePicker: End Time (HH:MM)
  - Validation: Start < End
- **If Flexible Model**:
  - TextField (number): Duration (hours)
  - Multi-TimePicker: Allowed Start Times
- Accordion: Breaks (optional)
  - Add Break:
    - Select: Type (meal/rest/other)
    - TextField: Duration (minutes)
    - Radio: Timing Mode (fixed/window/afterWork)
    - Fields based on timing mode
    - Checkbox: Paid
    - Checkbox: Required
    - Checkbox: Can Stagger

**UI Components Needed**:
- `ShiftsTable.jsx` - main table
- `ShiftForm.jsx` - add/edit dialog
- `BreakBuilder.jsx` - break configuration

**Validation**:
- At least 1 shift required
- Unique work period codes
- Unique order values
- Start < End (fixed model)
- Valid time formats (HH:MM)
- Positive duration (flexible model)

**State Updates**:
```javascript
updateState('demand.workPeriodModel', 'fixed');
updateState('demand.shifts', [
  {
    code: 'M',
    name: 'Morning',
    order: 1,
    timeRange: {start: '08:00', end: '16:00'},
    breaks: [{type: 'meal', duration: 30, ...}]
  }
]);
```

---

### Step 7: Demand Calendar
**Status**: Placeholder  
**Priority**: MEDIUM  
**Dependencies**: Step 3 (org units), Step 6 (shifts)

**Implementation Plan**:

**Calendar Grid View**:
- Rows: Date + Shift combinations
- Columns: Team/Competency, Minimum, Ideal, Estimated
- Group by date, then by shift
- Expandable/collapsible dates

**Filters**:
- Date range selector (show 1 week, 1 month, or all)
- Shift filter (show specific shifts)
- Team/Competency filter

**Inline Editing**:
- Click cell to edit
- TextField for numbers
- Validation: Min ≤ Est ≤ Ideal
- Visual indicators: red (understaffed), green (good), yellow (warning)

**Bulk Actions**:
- "Copy Week Pattern" - copy Mon-Sun to next weeks
- "Apply to Date Range" - apply same values to range
- "Fill from Template" - load from saved template
- "Clear Range" - clear values for range

**Toolbar**:
- Button: "Add Date/Shift Row" → Dialog
- Button: "Import CSV"
- Button: "Export CSV"
- Button: "Save as Template"
- Button: "Load Template"

**Add Demand Entry Dialog**:
- DatePicker: Date
- Select: Shift (from Step 6)
- Select: Team/Competency (from Step 3)
- TextField (number): Minimum
- TextField (number): Ideal
- TextField (number): Estimated
- Validation: Min ≤ Est ≤ Ideal, non-negative

**UI Components Needed**:
- `DemandCalendar.jsx` - main calendar grid
- `DemandRow.jsx` - editable row
- `DemandToolbar.jsx` - toolbar with actions
- `BulkActionsDialog.jsx` - bulk operations
- `TemplateManager.jsx` - save/load templates

**Validation**:
- Minimum ≤ Estimated ≤ Ideal
- Non-negative values
- Valid shift references
- Valid team/competency references
- Dates within temporal scope
- No duplicate (date, workPeriod, team) combinations

**CSV Format**:
```csv
date,shift,team,minimum,ideal,estimated
2026-01-01,M,A,3,5,4
2026-01-01,T,A,2,4,3
```

**State Updates**:
```javascript
updateState('demand.demandData', [
  {
    date: '2026-01-01',
    shift: 'M',
    team: 'A',
    minimum: 3,
    ideal: 5,
    estimated: 4
  }
]);
```

---

## Phase 4: Configuration

### Step 8: Constraints & Rules
**Status**: Placeholder  
**Priority**: LOW  
**Dependencies**: Step 1 (features)

**Implementation Plan**:

**Tabs**: "Hard Constraints" | "Soft Constraints" | "Advanced"

**Hard Constraints Tab**:
- List of constraint types (predefined set)
- Each constraint:
  - Checkbox: Enable/Disable
  - Expandable panel: Parameters
  - Helper text explaining the constraint

**Common Hard Constraints**:
- No overlapping shifts
- Respect contract max hours
- Minimum rest between shifts
- Maximum consecutive days
- Required skills for shift
- Employee availability (from Step 5)

**Soft Constraints Tab**:
- Similar to hard constraints
- Additional field: Weight (slider 0-100)
- Explains how weight affects optimization

**Common Soft Constraints**:
- Prefer certain shift patterns
- Balance workload across employees
- Minimize overtime
- Prefer experienced employees
- Minimize split shifts

**Advanced Tab** (if feature enabled in Step 1):
- Day-off swapping configuration
- Break rules
- Priority hierarchy builder (drag-drop ranking)

**UI Components Needed**:
- `ConstraintsList.jsx` - list of constraints
- `ConstraintCard.jsx` - individual constraint config
- `WeightSlider.jsx` - weight slider with labels
- `PriorityBuilder.jsx` - drag-drop priority list

**Validation**:
- Valid parameter types
- Non-negative weights
- Sum of weights doesn't exceed limits

**State Updates**:
```javascript
updateState('constraints.hard', [
  {id: 'no-overlap', type: 'no_overlapping_shifts', params: {}, enabled: true}
]);

updateState('constraints.soft', [
  {id: 'balance', type: 'balance_workload', params: {}, weight: 50, enabled: true}
]);

updateState('constraints.advanced.dayOffSwapping', {
  enabled: true,
  rules: ['can_swap_with_same_contract'],
  weekDefinition: 'monday-sunday'
});
```

---

### Step 9: Optimization Settings
**Status**: Placeholder  
**Priority**: LOW  
**Dependencies**: None

**Implementation Plan**:

**Algorithm Selection**:
- Select dropdown with all algorithms:
  - ILP, ILPv2, CSP, CSPv2
  - ILP Engine, CSP_ENGINE
  - Greedy Randomized, Greedy Randomized Engine
  - Greedy Randomized + Hill Climbing, GRHC_ENGINE
- Each option has tooltip with description

**Max Time**:
- Slider: 1-60 minutes
- Shows estimated time for problem size

**Objectives Table**:
- Columns: Goal, Weight, Priority, Actions
- "Add Objective" button → Dialog
- Predefined objective list to choose from

**Add Objective Dialog**:
- Select: Goal (from predefined list)
- TextField (number): Weight (0-100)
- TextField (number): Priority (1=highest)
- Helper text explaining the objective

**Common Objectives**:
- Minimize total hours worked
- Maximize coverage
- Minimize cost
- Balance workload
- Maximize employee satisfaction

**UI Components Needed**:
- `AlgorithmSelector.jsx` - algorithm dropdown with descriptions
- `TimeSlider.jsx` - max time slider
- `ObjectivesTable.jsx` - objectives table
- `ObjectiveForm.jsx` - add/edit dialog

**Validation**:
- Algorithm selected
- Max time > 0
- At least 1 objective
- Non-negative weights

**State Updates**:
```javascript
updateState('optimization.algorithm', 'ILP');
updateState('optimization.maxTimeMinutes', 10);
updateState('optimization.objectives', [
  {goal: 'minimize_hours', weight: 50, priority: 1}
]);
```

---

## Phase 5: Generation & Polish

### Step 10: Review & Generate
**Status**: Placeholder  
**Priority**: CRITICAL  
**Dependencies**: All previous steps

**Implementation Plan**:

**Summary Accordions**:
- Accordion for each step showing summary
- "Edit" button jumps back to that step
- Visual indicators: ✅ Complete, ⚠️ Warnings, ❌ Errors

**Validation Section**:
- Button: "Run Validation"
- Shows validation status:
  - ✅ All valid
  - ⚠️ Warnings (can proceed)
  - ❌ Errors (cannot proceed)
- List of errors with:
  - Error message
  - Location (which step)
  - "Jump to Step" button
- List of warnings with descriptions

**Preview Tabs**:
- Tab: "problem.json"
  - Syntax-highlighted JSON viewer
  - Collapsible sections
  - Copy button
- Tab: "demand.csv"
  - Table preview
  - Sortable columns
  - Export button
- Tab: "schedule_input.csv"
  - Table preview
  - Sortable columns
  - Export button

**Action Buttons**:
- Button: "Download as ZIP" (primary)
- Button: "Download problem.json"
- Button: "Download demand.csv"
- Button: "Download schedule_input.csv"
- Button: "Copy JSON to Clipboard"
- Button: "Save Project" (localStorage)
- Button: "Load Project"

**Generation Process**:
1. Collect all wizard state via `exportData()`
2. Call `jsonGenerator.js` to build problem.json
3. Call `demandCsvGenerator.js` to build demand.csv
4. Call `scheduleInputCsvGenerator.js` to build schedule_input.csv
5. (Optional) Call Python validator via API
6. Display results
7. Allow download

**UI Components Needed**:
- `ReviewAccordion.jsx` - summary accordion
- `ValidationPanel.jsx` - validation results
- `JsonPreview.jsx` - syntax-highlighted JSON
- `CSVPreview.jsx` - table view
- `DownloadPanel.jsx` - download buttons
- `ProjectManager.jsx` - save/load projects

**Utilities Needed**:
- `jsonGenerator.js` - builds problem.json from state
- `demandCsvGenerator.js` - builds demand.csv
- `scheduleInputCsvGenerator.js` - builds schedule_input.csv
- `pythonValidator.js` - calls backend validator (optional)
- `fileDownload.js` - handles ZIP creation and download

**jsonGenerator.js Logic**:
```javascript
export function generateProblemJson(state) {
  return {
    schemaVersion: '2.2',
    problemType: 'employee_scheduling',
    metadata: state.metadata,
    features: state.features,
    temporalScope: state.temporalScope,
    contracts: state.contracts,
    employees: state.employees,
    scheduleInput: {
      dataFile: 'schedule_input.csv',
      markingTypes: state.scheduleInput.markingTypes
    },
    demand: {
      workPeriodModel: state.demand.workPeriodModel,
      work periods: state.demand.shifts,
      organizationalUnits: state.employees.model === 'team'
        ? {teams: state.organizationalUnits.teams}
        : {competencies: state.organizationalUnits.competencies},
      dataFile: 'demand.csv',
      priorityHierarchy: state.demand.priorityHierarchy
    },
    constraints: state.constraints,
    optimization: state.optimization
  };
}
```

**demandCsvGenerator.js Logic**:
```javascript
import Papa from 'papaparse';

export function generateDemandCsv(demandData) {
  const rows = demandData.map(row => ({
    date: row.date,
    shift: row.shift,
    team: row.team,
    minimum: row.minimum,
    ideal: row.ideal,
    estimated: row.estimated
  }));
  
  return Papa.unparse(rows);
}
```

**scheduleInputCsvGenerator.js Logic**:
```javascript
import Papa from 'papaparse';

export function generateScheduleInputCsv(employees, dataMatrix, dateRange) {
  const headers = ['employee_id', ...dateRange];
  const rows = employees.map(emp => {
    const row = {employee_id: emp.id};
    dateRange.forEach(date => {
      row[date] = dataMatrix[emp.id]?.[date] || '';
    });
    return row;
  });
  
  return Papa.unparse(rows, {columns: headers});
}
```

**Download Logic**:
```javascript
import JSZip from 'jszip';
import { saveAs } from 'file-saver';

export async function downloadAsZip(problemJson, demandCsv, scheduleInputCsv) {
  const zip = new JSZip();
  
  zip.file('problem.json', JSON.stringify(problemJson, null, 2));
  zip.file('demand.csv', demandCsv);
  zip.file('schedule_input.csv', scheduleInputCsv);
  
  const blob = await zip.generateAsync({type: 'blob'});
  saveAs(blob, 'scheduling-problem.zip');
}
```

---

## Technical Decisions

### Why React Context instead of Redux?
- **Simpler**: No boilerplate for actions/reducers
- **Sufficient**: Single user, no concurrent updates
- **LocalStorage**: Easy persistence
- **Performance**: Only one consumer (WizardContent)

### Why MUI instead of DaisyUI?
- **Consistency**: Main frontend uses MUI
- **Components**: Rich set of form components
- **TypeScript**: Better type support
- **Customization**: Theme system matches requirements

### Why localStorage instead of backend?
- **Offline**: Works without network
- **Simple**: No auth, no database
- **Fast**: Instant saves
- **Stateless**: No server state to manage

### Why date-fns v2 instead of v3?
- **MUI Compatibility**: AdapterDateFns requires v2
- **Stable**: Well-tested, no breaking changes needed

### Why PapaParse for CSV?
- **Robust**: Handles edge cases (quotes, newlines)
- **Fast**: Streaming support for large files
- **Standard**: Industry standard for browser CSV

### Why JSZip + file-saver?
- **Convenience**: Bundle all files in one download
- **Standards**: Uses standard ZIP format
- **Browser**: Works client-side, no server needed

---

## Future Enhancements

### Short Term (After Phase 5)
- [ ] Dark mode theme option
- [ ] Keyboard shortcuts (Ctrl+S save, Ctrl+Enter next)
- [ ] Export to different JSON formats (v2.0, v2.1)
- [ ] Load existing problem.json for editing
- [ ] Validation tooltips with examples
- [ ] Quick start templates (retail, hospital, etc.)

### Medium Term
- [ ] Multi-language support (i18n)
- [ ] Help system with guided tour
- [ ] Undo/Redo functionality
- [ ] Drag-drop CSV files onto steps
- [ ] Excel import support (via SheetJS)
- [ ] Advanced validation with Python validator integration
- [ ] Schedule visualization before generation

### Long Term
- [ ] Backend integration (save to server)
- [ ] Multi-user collaboration
- [ ] Version history
- [ ] API for programmatic generation
- [ ] Mobile app (React Native)
- [ ] AI-assisted configuration suggestions

---

## Dependencies & Compatibility

### Browser Support
- Chrome 90+
- Firefox 88+
- Safari 14+
- Edge 90+

### Required NPM Packages
```json
{
  "@mui/material": "^7.0.1",
  "@mui/x-date-pickers": "^7.0.0",
  "date-fns": "^2.30.0",
  "papaparse": "^5.4.1",
  "jszip": "^3.10.1",
  "file-saver": "^2.0.5"
}
```

### Python Validator Integration (Optional)
- Backend endpoint: `POST /api/validate`
- Input: `multipart/form-data` with problem.json, demand.csv, schedule_input.csv
- Output: `{success: boolean, errors: [...], warnings: [...], stats: {...}}`

---

## Testing Strategy

### Unit Tests
- Utils: jsonGenerator, csvGenerators, validators
- Context: WizardContext state updates
- Components: Individual step validations

### Integration Tests
- Step navigation flow
- State persistence (localStorage)
- CSV import/export
- File generation

### E2E Tests (Cypress/Playwright)
- Complete wizard flow
- Error handling
- File downloads

### Manual Testing
- Browser compatibility
- Responsive design
- Accessibility (keyboard navigation, screen readers)

---

## Performance Considerations

### Large Datasets
- **1000+ employees**: Use virtualization (react-window)
- **365 days**: Lazy load schedule matrix columns
- **Large CSVs**: Stream parsing with PapaParse worker

### Optimization Strategies
- Debounced auto-save (1s)
- Memoized expensive computations (useMemo)
- Lazy loaded steps (React.lazy)
- Compressed localStorage (gzip)

---

## Deployment

### Development
```bash
cd src/json-generator
npm install
npm run dev
# Available at http://localhost:5174
```

### Production Build
```bash
npm run build
# Outputs to dist/
```

### Docker
```bash
docker-compose up json-generator
# Available at http://localhost/json-gen/
```

### Static Hosting (Future)
- Deploy dist/ to Netlify/Vercel/Cloudflare Pages
- Configure base path for subdomain
- Enable gzip compression

---

## Changelog

### 2026-02-04 (Step Reorganization Update)
- ✅ **Reorganized Steps** - Split Step 1 and created dedicated Employee Model step
- ✅ **Step 1 (Quick Setup)** - Merged metadata and temporal scope into single card
- ✅ Moved date chips below calendar for better visual flow
- ✅ Increased calendar size and added max-height to prevent scrolling
- ✅ Removed Employee Model selection from Step 1
- ✅ **Step 2 (NEW - Employee Model)** - Created visual card-based selection
- ✅ Two selectable cards with MUI icons (Groups for Team, Engineering for Competency)
- ✅ Info icons with tooltips explaining each model
- ✅ Visual feedback on selection (border highlight, checkmark)
- ✅ **Renumbered Steps** - All subsequent steps incremented (Step 2→3, 3→4, etc.)
- ✅ Updated WizardContext to support 11 steps (0-10)
- ✅ Updated App.jsx with new step imports and routing
- ✅ Updated WizardStepper to show 11 steps with correct labels
- 📝 Total steps now: 11 (was 10)

### 2026-02-04 (Evening Update)
- ✅ **Feature Flags Auto-Detection** - Major UX improvement
- ✅ Removed feature flags from Step 1 UI
- ✅ Created `src/utils/featureDetector.js` for automatic detection
- ✅ Updated WizardContext to auto-detect features on export
- ✅ Simplified Quick Setup step

### 2026-02-04 (Initial)
- ✅ Phase 1 complete (foundation)
- ✅ Step 1 and Step 2 fully implemented
- ✅ Header UI improvements
- ✅ Step 1 layout consistency fixes
- ✅ Removed buffer weeks from temporal scope
- ✅ Fixed date-fns compatibility
- ✅ Fixed nginx routing with vite base path
- 📝 Created comprehensive PLAN.md

### 2026-02-03
- ✅ Initial project setup
- ✅ Theme configuration
- ✅ WizardContext implementation
- ✅ Navigation components
- ✅ Step 1 and Step 2 implementation

---

## Contributors
- **AI Assistant (Claude)**: Architecture, implementation, documentation
- **User (roldao)**: Requirements, feedback, testing

---

## License
Part of SmarTask UA project.

---

**End of PLAN.md**
