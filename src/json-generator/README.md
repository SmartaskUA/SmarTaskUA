# JSON Generator - Schema v2.6

User-friendly frontend wizard for generating schema v2.6 JSON + CSV pairs for employee scheduling problems.

## Features

- ✅ **10-Step Wizard**: Guides users through the entire JSON/CSV generation process
- ✅ **Editable Theme**: All colors can be customized in `src/theme.config.js`
- ✅ **MUI Components**: Built with Material-UI for consistency with main app
- ✅ **Auto-Save**: Progress is automatically saved to localStorage
- ✅ **Validation**: Real-time validation with error feedback
- ✅ **Responsive**: Works on tablets and desktops

The application will be available at: http://localhost:5174

## Project Structure

```
src/
├── components/
│   ├── wizard/          # Stepper, NavigationButtons, StepCard
│   ├── calendar/        # ScheduleMatrix, TimeConstraintDialog, MatrixCell
│   ├── constraints/     # ConstraintCard, ConstraintsList, ParamEditor
│   ├── demand/          # DemandCalendarGrid, WeeklyTemplateBuilder, DayDemandDetail
│   ├── employees/       # EmployeeTable, EmployeeForm, CompetencyBuilder
│   ├── import/          # CSVImporter, CSVPreview, ColumnMapper
│   ├── organizational/  # OrganizationalUnitTable, OrganizationalUnitForm
│   ├── optimization/    # AlgorithmSelector, ObjectiveDialog
│   ├── preview/         # JsonPreview, CsvPreview
│   ├── review/          # ValidationPanel, PreviewTabs, SummaryAccordions, DownloadPanel
│   ├── shared/          # ImportPreviewModal
│   ├── shifts/          # WorkPeriodForm, WorkPeriodTable, BreakBuilder
│   └── project/         # ProjectManagerDialog (save/load/export projects)
├── context/
│   └── WizardContext.jsx    # Central state management
├── steps/
│   ├── Step1_QuickSetup.jsx         # ✅ Implemented
│   ├── Step2_Contracts.jsx          # ✅ Implemented
│   ├── Step3_OrganizationalUnits.jsx # ✅ Implemented
│   ├── Step4_Employees.jsx          # ✅ Implemented
│   ├── Step5_ScheduleInput.jsx      # ✅ Implemented
│   ├── Step6_WorkPeriods.jsx        # ✅ Implemented
│   ├── Step7_Demand.jsx             # ✅ Implemented
│   ├── Step8_Constraints.jsx        # ✅ Implemented (hidden from stepper)
│   ├── Step9_Optimization.jsx       # ✅ Implemented (hidden from stepper)
│   └── Step10_ReviewGenerate.jsx    # ✅ Implemented
├── utils/
│   ├── generators/      # JSON/CSV generation logic
│   ├── validators/      # Validation logic (master + per-step + cross-step)
│   ├── parsers/         # CSV/JSON parsing
│   └── helpers/         # Date, time, template, color helpers
├── App.jsx              # Main application
├── main.jsx             # Entry point
├── theme.config.js      # 🎨 EDITABLE THEME CONFIGURATION
├── theme.js             # MUI theme
└── index.css            # Global styles
```

## Customizing Colors

Edit `src/theme.config.js` to customize the entire application's color palette:

```javascript
export const themeConfig = {
  primary: {
    main: '#007bff',      // Change this to your primary color
    light: '#4da3ff',
    dark: '#0056b3'
  },
  success: {
    main: '#28a745',      // Success/completed states
  },
  // ... more colors
};
```

## Wizard Steps

### ✅ Step 1: Quick Setup (Implemented)
- Problem metadata (ID, description)
- Temporal scope (year, dates, number of days)
- Employee model selection (Team vs Competency)
- Feature flags

### ✅ Step 2: Contracts (Implemented)
- Define reusable contract types
- Set work hours per day
- Optional constraints (weekends only, max hours, etc.)
- Add/Edit/Delete contracts

### ✅ Step 3: Organizational Units (Implemented)
- Define teams (team model) or competencies (competency model)

### ✅ Step 4: Employees (Implemented)
- Manual entry or CSV import (with preview & column mapping)
- Assign teams/competencies and contracts

### ✅ Step 5: Schedule Input Matrix (Implemented)
- Visual matrix for employee availability and work requirements
- **Work Requirements**: A (auto-allocate), 1-16 (specific hours)
- **Time Window Constraints (v2.6)**: EQUALS:HH:MM-HH:MM, INCLUDE:HH:MM-HH:MM, EXCEPT:HH:MM-HH:MM
- **Standard Constraints**: VAC (vacation), NOT (unavailable)
- **Custom Constraints**: Define project-specific codes (DL, DLF, etc.)

### ✅ Step 6: Work Periods (Implemented)
- Define work period codes, names, time ranges
- Fixed or flexible work periods
- Break rules (meal, rest, other)
- Timing modes: fixed, window, afterWork

### ✅ Step 7: Demand Calendar (Implemented)
- Coverage requirements per date/shift/team
- Minimum, Ideal, Estimated values

### ✅ Step 8: Constraints (Implemented — hidden from stepper UI)
- **Hard Constraints**: Must be satisfied (max_consecutive_days, min_rest_hours, vacation_block, etc.)
- **Soft Constraints**: With penalty weights (min_coverage, balance_workload, etc.)
- **Advanced**: Day-off swapping, break rules, priority hierarchy (requires useAdvancedConstraints feature flag)

### ✅ Step 9: Optimization (Implemented — hidden from stepper UI)
- Algorithm selection
- Objectives and weights

### ✅ Step 10: Review & Generate (Implemented)
- Master validation (per-step + cross-step) with errors/warnings
- Preview JSON/CSV
- Download `problem.json` + `demand.csv` + `schedule_input.csv` as a ZIP

> **Note on hidden steps:** Steps 8 (Constraints) and 9 (Optimization) are intentionally hidden from the visible stepper to keep the main flow simple, but they are fully functional and editable. Sensible defaults are applied; advanced users can reach them programmatically or via the review step.

## Development Roadmap

### Phase 1: Foundation ✅ COMPLETE
- [x] Project structure
- [x] Theme configuration (editable)
- [x] WizardContext state management
- [x] Stepper navigation
- [x] Step 1: Quick Setup
- [x] Step 2: Contracts

### Phase 2: Core Data ✅ COMPLETE
- [x] Step 3: Organizational Units
- [x] Step 4: Employees (with CSV import)
- [x] Reusable table components

### Phase 3: Scheduling ✅ COMPLETE
- [x] Step 5: Schedule Input Matrix
- [x] Step 6: Work Periods
- [x] Step 7: Demand Calendar

### Phase 4: Configuration ✅ COMPLETE
- [x] Step 8: Constraints
- [x] Step 9: Optimization

### Phase 5: Generation & Polish ✅ COMPLETE
- [x] Step 10: Review & Generate
- [x] JSON/CSV generation logic
- [x] File downloads (ZIP)
- [ ] Python validator integration (deferred)
- [ ] User-testing pass (in progress)

## State Management

The wizard uses React Context API for state management. All state is automatically saved to localStorage and restored on page reload.

State structure matches schema v2.6:
```javascript
{
  currentStep: 0,
  stepCompleted: { 0: false, 1: false, ... },
  metadata: { ... },
  features: { ... },
  temporalScope: { ... },
  contracts: { definitions: [...] },
  employees: { model, simple/competency: [...] },
  organizationalUnits: { teams/competencies: [...] },
  scheduleInput: { ... },
  demand: { ... },
  constraints: { ... },
  optimization: { ... }
}
```

## Technologies

- **React 18**: UI framework
- **Vite**: Build tool
- **Material-UI v7**: Component library
- **React Router v6**: Navigation
- **date-fns**: Date operations
- **PapaParse**: CSV parsing
- **JSZip**: File bundling
- **file-saver**: File downloads

## Contributing

1. Each step should be self-contained in `src/steps/`
2. Use the `useWizard()` hook to access/update state
3. Use `StepCard` for consistent styling
4. Use `NavigationButtons` for step navigation
5. Validate before allowing "Next"
6. Mark step as completed on successful validation

## License

Part of SmarTask UA project.
