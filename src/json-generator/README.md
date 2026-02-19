# JSON Generator - Schema v2.2

User-friendly frontend wizard for generating schema v2.2 JSON + CSV pairs for employee scheduling problems.

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
│   ├── wizard/          # Wizard components (Stepper, Navigation, StepCard)
│   ├── tables/          # Table components (coming soon)
│   ├── calendar/        # Calendar components (coming soon)
│   ├── import/          # CSV import components (coming soon)
│   ├── validation/      # Validation components (coming soon)
│   ├── preview/         # Preview components (coming soon)
│   └── forms/           # Form dialogs (coming soon)
├── context/
│   └── WizardContext.jsx    # Central state management
├── steps/
│   ├── Step1_QuickSetup.jsx         # ✅ Implemented
│   ├── Step2_Contracts.jsx          # ✅ Implemented
│   ├── Step3_OrganizationalUnits.jsx # 🔄 Placeholder
│   ├── Step4_Employees.jsx          # 🔄 Placeholder
│   ├── Step5_ScheduleInput.jsx      # 🔄 Placeholder
│   ├── Step6_Work Periods.jsx             # 🔄 Placeholder
│   ├── Step7_Demand.jsx             # 🔄 Placeholder
│   ├── Step8_Constraints.jsx        # 🔄 Placeholder
│   ├── Step9_Optimization.jsx       # 🔄 Placeholder
│   └── Step10_ReviewGenerate.jsx    # 🔄 Placeholder
├── utils/
│   ├── generators/      # JSON/CSV generation logic (coming soon)
│   ├── validators/      # Validation logic (coming soon)
│   ├── parsers/         # CSV/JSON parsing (coming soon)
│   ├── storage/         # LocalStorage helpers (coming soon)
│   └── helpers/         # Helper functions (coming soon)
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

### 🔄 Step 3: Organizational Units (Coming Soon)
- Define teams (team model) or competencies (competency model)

### 🔄 Step 4: Employees (Coming Soon)
- Manual entry or CSV import
- Assign teams/competencies and contracts

### 🔄 Step 5: Schedule Input Matrix (Coming Soon)
- Visual matrix for employee availability and work requirements
- **Work Requirements**: A (auto-allocate), 1-16 (specific hours)
- **Time Window Constraints (v2.2)**: EQUALS:HH:MM-HH:MM, INCLUDE:HH:MM-HH:MM, EXCEPT:HH:MM-HH:MM
- **Standard Constraints**: VAC (vacation), NOT (unavailable)
- **Custom Constraints**: Define project-specific codes (DL, DLF, etc.)

### 🔄 Step 6: Work Periods (Coming Soon)
- Define work period codes, names, time ranges
- Fixed or flexible work periods
- Break rules (meal, rest, other)
- Timing modes: fixed, window, afterWork

### 🔄 Step 7: Demand Calendar (Coming Soon)
- Coverage requirements per date/shift/team
- Minimum, Ideal, Estimated values

### 🔄 Step 8: Constraints (Coming Soon)
- **Hard Constraints**: Must be satisfied (max_consecutive_days, min_rest_hours, vacation_block, etc.)
- **Soft Constraints**: With penalty weights (min_coverage, balance_workload, etc.)
- **Advanced**: Day-off swapping, break rules, priority hierarchy (requires useAdvancedConstraints feature flag)

### 🔄 Step 9: Optimization (Coming Soon)
- Algorithm selection
- Objectives and weights

### 🔄 Step 10: Review & Generate (Coming Soon)
- Validation
- Preview JSON/CSV
- Download files

## Development Roadmap

### Phase 1: Foundation ✅ COMPLETE
- [x] Project structure
- [x] Theme configuration (editable)
- [x] WizardContext state management
- [x] Stepper navigation
- [x] Step 1: Quick Setup
- [x] Step 2: Contracts

### Phase 2: Core Data (Next)
- [ ] Step 3: Organizational Units
- [ ] Step 4: Employees (with CSV import)
- [ ] Reusable table components

### Phase 3: Scheduling
- [ ] Step 5: Schedule Input Matrix
- [ ] Step 6: Work Periods
- [ ] Step 7: Demand Calendar

### Phase 4: Configuration
- [ ] Step 8: Constraints
- [ ] Step 9: Optimization

### Phase 5: Generation & Polish
- [ ] Step 10: Review & Generate
- [ ] JSON/CSV generation logic
- [ ] Python validator integration
- [ ] File downloads (ZIP)
- [ ] Testing and polish

## State Management

The wizard uses React Context API for state management. All state is automatically saved to localStorage and restored on page reload.

State structure matches schema v2.2:
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
- **PapaParse**: CSV parsing (when implemented)
- **JSZip**: File bundling (when implemented)
- **file-saver**: File downloads (when implemented)

## Contributing

1. Each step should be self-contained in `src/steps/`
2. Use the `useWizard()` hook to access/update state
3. Use `StepCard` for consistent styling
4. Use `NavigationButtons` for step navigation
5. Validate before allowing "Next"
6. Mark step as completed on successful validation

## License

Part of SmarTask UA project.
