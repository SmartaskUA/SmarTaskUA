     ╭────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────╮
     │ JSON Generation Frontend Wizard - Implementation Plan (v2.2)                                                                                                           │
     │                                                                                                                                                                        │
     │ Overview                                                                                                                                                               │
     │                                                                                                                                                                        │
     │ Create a standalone, step-by-step wizard application in src/json-generator/ to generate schema v2.2 JSON + CSV pairs with a user-friendly interface using Material-UI. │
     │                                                                                                                                                                        │
     │ Technology Stack                                                                                                                                                       │
     │                                                                                                                                                                        │
     │ - Framework: React 18 + Vite                                                                                                                                           │
     │ - UI Components: Material UI (MUI) v7 + Tailwind CSS                                                                                                                   │
     │ - Navigation: React Router v6                                                                                                                                          │
     │ - State Management: React Context API                                                                                                                                  │
     │ - CSV Handling: PapaParse                                                                                                                                              │
     │ - Date Handling: date-fns                                                                                                                                              │
     │ - Validation: Integration with Python validator.py                                                                                                                     │
     │ - File Operations: file-saver for downloads                                                                                                                            │
     │                                                                                                                                                                        │
     │ Project Structure                                                                                                                                                      │
     │                                                                                                                                                                        │
     │ src/json-generator/                                                                                                                                                    │
     │ ├── package.json (separate Vite app)                                                                                                                                   │
     │ ├── vite.config.js                                                                                                                                                     │
     │ ├── index.html                                                                                                                                                         │
     │ ├── src/                                                                                                                                                               │
     │ │   ├── main.jsx                                                                                                                                                       │
     │ │   ├── App.jsx (main wizard with MUI Stepper)                                                                                                                         │
     │ │   ├── context/                                                                                                                                                       │
     │ │   │   └── WizardContext.jsx (shared state across all steps)                                                                                                          │
     │ │   ├── steps/                                                                                                                                                         │
     │ │   │   ├── Step1_QuickSetup.jsx                                                                                                                                       │
     │ │   │   ├── Step2_Contracts.jsx                                                                                                                                        │
     │ │   │   ├── Step3_OrganizationalUnits.jsx                                                                                                                              │
     │ │   │   ├── Step4_Employees.jsx                                                                                                                                        │
     │ │   │   ├── Step5_ScheduleInput.jsx                                                                                                                                    │
     │ │   │   ├── Step6_Shifts.jsx                                                                                                                                           │
     │ │   │   ├── Step7_Demand.jsx                                                                                                                                           │
     │ │   │   ├── Step8_Constraints.jsx                                                                                                                                      │
     │ │   │   ├── Step9_Optimization.jsx                                                                                                                                     │
     │ │   │   └── Step10_ReviewGenerate.jsx                                                                                                                                  │
     │ │   ├── components/                                                                                                                                                    │
     │ │   │   ├── wizard/                                                                                                                                                    │
     │ │   │   │   ├── WizardStepper.jsx (MUI Stepper navigation)                                                                                                             │
     │ │   │   │   ├── StepCard.jsx (consistent card wrapper)                                                                                                                 │
     │ │   │   │   └── NavigationButtons.jsx (Next/Previous/Save)                                                                                                             │
     │ │   │   ├── tables/                                                                                                                                                    │
     │ │   │   │   ├── EditableTable.jsx (generic editable table)                                                                                                             │
     │ │   │   │   ├── EmployeeTable.jsx (employees with teams/competencies)                                                                                                  │
     │ │   │   │   └── ContractTable.jsx (contract definitions)                                                                                                               │
     │ │   │   ├── calendar/                                                                                                                                                  │
     │ │   │   │   ├── DemandCalendar.jsx (calendar grid for demand)                                                                                                          │
     │ │   │   │   ├── ScheduleMatrix.jsx (schedule_input.csv editor)                                                                                                         │
     │ │   │   │   └── DateRangePicker.jsx (temporal scope picker)                                                                                                            │
     │ │   │   ├── import/                                                                                                                                                    │
     │ │   │   │   ├── CSVImporter.jsx (reusable CSV import)                                                                                                                  │
     │ │   │   │   └── CSVPreview.jsx (preview before import)                                                                                                                 │
     │ │   │   ├── validation/                                                                                                                                                │
     │ │   │   │   ├── ValidationPanel.jsx (show errors/warnings)                                                                                                             │
     │ │   │   │   └── StepValidationIndicator.jsx (check/error icons)                                                                                                        │
     │ │   │   ├── preview/                                                                                                                                                   │
     │ │   │   │   ├── JsonPreview.jsx (syntax-highlighted JSON)                                                                                                              │
     │ │   │   │   ├── CSVPreview.jsx (table view of CSV)                                                                                                                     │
     │ │   │   │   └── DownloadPanel.jsx (download buttons)                                                                                                                   │
     │ │   │   └── forms/                                                                                                                                                     │
     │ │   │       ├── ContractForm.jsx (add/edit contract dialog)                                                                                                            │
     │ │   │       ├── EmployeeForm.jsx (add/edit employee dialog)                                                                                                            │
     │ │   │       ├── ShiftForm.jsx (add/edit shift dialog)                                                                                                                  │
     │ │   │       └── ConstraintForm.jsx (constraint configuration)                                                                                                          │
     │ │   ├── utils/                                                                                                                                                         │
     │ │   │   ├── generators/                                                                                                                                                │
     │ │   │   │   ├── jsonGenerator.js (builds problem.json)                                                                                                                 │
     │ │   │   │   ├── demandCsvGenerator.js (generates demand.csv)                                                                                                           │
     │ │   │   │   └── scheduleInputCsvGenerator.js (generates schedule_input.csv)                                                                                            │
     │ │   │   ├── validators/                                                                                                                                                │
     │ │   │   │   ├── stepValidators.js (per-step validation)                                                                                                                │
     │ │   │   │   ├── crossValidation.js (cross-field validation)                                                                                                            │
     │ │   │   │   └── pythonValidator.js (call backend validator)                                                                                                            │
     │ │   │   ├── parsers/                                                                                                                                                   │
     │ │   │   │   ├── csvParser.js (parse imported CSVs)                                                                                                                     │
     │ │   │   │   └── jsonParser.js (load existing problem.json)                                                                                                             │
     │ │   │   ├── storage/                                                                                                                                                   │
     │ │   │   │   └── localStorage.js (auto-save/restore)                                                                                                                    │
     │ │   │   └── helpers/                                                                                                                                                   │
     │ │   │       ├── dateHelpers.js (date operations)                                                                                                                       │
     │ │   │       ├── fileDownload.js (ZIP download)                                                                                                                         │
     │ │   │       └── constants.js (default values, enums)                                                                                                                   │
     │ │   └── hooks/                                                                                                                                                         │
     │ │       ├── useWizardState.js (wizard state management)                                                                                                                │
     │ │       ├── useStepValidation.js (validate current step)                                                                                                               │
     │ │       └── useAutoSave.js (localStorage auto-save)                                                                                                                    │
     │                                                                                                                                                                        │
     │ Wizard Flow (10 Steps)                                                                                                                                                 │
     │                                                                                                                                                                        │
     │ Step 1: Quick Setup                                                                                                                                                    │
     │                                                                                                                                                                        │
     │ Purpose: Core metadata and model selection                                                                                                                             │
     │                                                                                                                                                                        │
     │ UI Components:                                                                                                                                                         │
     │ - TextField: Problem ID, Description                                                                                                                                   │
     │ - DateTimePicker: Creation timestamp (auto-filled)                                                                                                                     │
     │ - Select: Year (2020-2100)                                                                                                                                             │
     │ - TextField: Number of days (1-366)                                                                                                                                    │
     │ - DateRangePicker: Target period (start/end dates)                                                                                                                     │
     │ - Radio Group: Employee Model (Team vs Competency) - CRITICAL CHOICE                                                                                                   │
     │ - Checkbox Group: Feature flags (shift-based, advanced constraints, priority hierarchy)                                                                                │
     │                                                                                                                                                                        │
     │ MUI Components: Box, Paper, TextField, Select, RadioGroup, FormControlLabel, Checkbox, DatePicker                                                                      │
     │                                                                                                                                                                        │
     │ Validation:                                                                                                                                                            │
     │ - Problem ID required and unique                                                                                                                                       │
     │ - Year in valid range                                                                                                                                                  │
     │ - NumDays matches date range                                                                                                                                           │
     │ - Model selection required                                                                                                                                             │
     │                                                                                                                                                                        │
     │ ---                                                                                                                                                                    │
     │ Step 2: Contracts                                                                                                                                                      │
     │                                                                                                                                                                        │
     │ Purpose: Define reusable contract types                                                                                                                                │
     │                                                                                                                                                                        │
     │ UI Components:                                                                                                                                                         │
     │ - Table (MUI DataGrid or custom): Contract list with columns:                                                                                                          │
     │   - ID, Name, Work Hours/Day, Actions (Edit/Delete)                                                                                                                    │
     │ - Button: Add Contract → Opens Dialog                                                                                                                                  │
     │ - Dialog: Add/Edit Contract Form                                                                                                                                       │
     │   - TextField: Contract ID, Name                                                                                                                                       │
     │   - TextField (number): Work Hours Per Day (0-24)                                                                                                                      │
     │   - Accordion: Optional Constraints                                                                                                                                    │
     │       - Checkbox: Weekends Only / Weekdays Only                                                                                                                        │
     │     - MultiSelect: Available Days                                                                                                                                      │
     │     - TextField: Max Hours Per Week, Max Consecutive Days, Min Rest Days/Week                                                                                          │
     │                                                                                                                                                                        │
     │ MUI Components: DataGrid, Button, Dialog, TextField, Accordion, Checkbox, Chip                                                                                         │
     │                                                                                                                                                                        │
     │ Validation:                                                                                                                                                            │
     │ - At least 1 contract required                                                                                                                                         │
     │ - Unique contract IDs                                                                                                                                                  │
     │ - Work hours 0-24                                                                                                                                                      │
     │ - Weekends/Weekdays mutually exclusive                                                                                                                                 │
     │                                                                                                                                                                        │
     │ ---                                                                                                                                                                    │
     │ Step 3: Organizational Units                                                                                                                                           │
     │                                                                                                                                                                        │
     │ Purpose: Define teams or competencies (depends on model from Step 1)                                                                                                   │
     │                                                                                                                                                                        │
     │ Conditional Rendering:                                                                                                                                                 │
     │                                                                                                                                                                        │
     │ If Team Model:                                                                                                                                                         │
     │ - ChipInput: Add/remove team codes                                                                                                                                     │
     │ - List: Display all teams with delete buttons                                                                                                                          │
     │ - TextField: Add new team code                                                                                                                                         │
     │                                                                                                                                                                        │
     │ If Competency Model:                                                                                                                                                   │
     │ - Table: Competency list (code, name)                                                                                                                                  │
     │ - Button: Add Competency → Dialog                                                                                                                                      │
     │ - Dialog: Code + Name fields                                                                                                                                           │
     │                                                                                                                                                                        │
     │ MUI Components: Paper, TextField, Chip, List, ListItem, IconButton, Table, Button, Dialog                                                                              │
     │                                                                                                                                                                        │
     │ Validation:                                                                                                                                                            │
     │ - At least 1 team/competency required                                                                                                                                  │
     │ - Unique codes                                                                                                                                                         │
     │ - Non-empty names                                                                                                                                                      │
     │                                                                                                                                                                        │
     │ ---                                                                                                                                                                    │
     │ Step 4: Employees                                                                                                                                                      │
     │                                                                                                                                                                        │
     │ Purpose: Define employee roster                                                                                                                                        │
     │                                                                                                                                                                        │
     │ UI Components:                                                                                                                                                         │
     │ - Tabs: "Manual Entry" | "Import CSV"                                                                                                                                  │
     │ - Manual Entry Tab:                                                                                                                                                    │
     │   - DataGrid/Table: Employee list with inline editing                                                                                                                  │
     │   - Columns: ID, Name, Teams/Competencies, Contract Type                                                                                                               │
     │   - Button: Add Employee → Dialog                                                                                                                                      │
     │   - Dialog: Employee Form                                                                                                                                              │
     │       - TextField: ID, Name                                                                                                                                            │
     │     - Team Model: MultiSelect chips for teams (from Step 3)                                                                                                            │
     │     - Competency Model: Competency builder:                                                                                                                            │
     │           - Select: Competency Code (from Step 3)                                                                                                                      │
     │       - TextField: Level (integer)                                                                                                                                     │
     │       - Button: Add Competency                                                                                                                                         │
     │       - List: Current competencies with delete                                                                                                                         │
     │     - Select: Contract Type (from Step 2)                                                                                                                              │
     │     - Accordion: Contract Periods (advanced)                                                                                                                           │
     │ - Import CSV Tab:                                                                                                                                                      │
     │   - File upload (drag-drop or button)                                                                                                                                  │
     │   - CSV preview table                                                                                                                                                  │
     │   - Column mapping UI                                                                                                                                                  │
     │   - Import button                                                                                                                                                      │
     │                                                                                                                                                                        │
     │ MUI Components: Tabs, DataGrid, Button, Dialog, TextField, Autocomplete, Select, Chip, Accordion                                                                       │
     │                                                                                                                                                                        │
     │ Validation:                                                                                                                                                            │
     │ - Unique employee IDs                                                                                                                                                  │
     │ - At least 1 employee                                                                                                                                                  │
     │ - Valid contract references                                                                                                                                            │
     │ - Valid team/competency references                                                                                                                                     │
     │ - At least 1 team/competency per employee                                                                                                                              │
     │                                                                                                                                                                        │
     │ ---                                                                                                                                                                    │
     │ Step 5: Schedule Input Matrix                                                                                                                                          │
     │                                                                                                                                                                        │
     │ Purpose: Define employee availability and work requirements                                                                                                            │
     │                                                                                                                                                                        │
     │ UI Components:                                                                                                                                                         │
     │ - Date header row (auto-generated from Step 1 date range)                                                                                                              │
     │ - Employee rows (from Step 4)                                                                                                                                          │
     │ - Editable cells with:                                                                                                                                                 │
     │   - Text input: A, 1-16, VAC, DL, etc.                                                                                                                                 │
     │   - Color coding: Green (A/numbers), Red (DL/VAC), etc.                                                                                                                │
     │   - Keyboard navigation (arrow keys, tab)                                                                                                                              │
     │   - Cell validation on blur                                                                                                                                            │
     │ - Toolbar:                                                                                                                                                             │
     │   - Button: Define Marking Types → Dialog to add custom markings                                                                                                       │
     │   - Select: Fill mode (drag to apply value)                                                                                                                            │
     │   - Button: Import CSV                                                                                                                                                 │
     │   - Button: Export CSV                                                                                                                                                 │
     │ - Legend: Show color meanings                                                                                                                                          │
     │                                                                                                                                                                        │
     │ MUI Components: Box, Paper, Table, TableCell (custom styled), TextField, IconButton, Tooltip, Dialog                                                                   │
     │                                                                                                                                                                        │
     │ Validation:                                                                                                                                                            │
     │ - Valid cell values: A, 1-16, or defined marking types                                                                                                                 │
     │ - Employees using 'A' must have valid contract with workHoursPerDay                                                                                                    │
     │ - Date columns match temporal scope                                                                                                                                    │
     │                                                                                                                                                                        │
     │ ---                                                                                                                                                                    │
     │ Step 6: Shifts Definition                                                                                                                                              │
     │                                                                                                                                                                        │
     │ Purpose: Define shift types and schedules                                                                                                                              │
     │                                                                                                                                                                        │
     │ UI Components:                                                                                                                                                         │
     │ - Radio: Shift Model (Fixed vs Flexible)                                                                                                                               │
     │ - Table: Shift list                                                                                                                                                    │
     │   - Columns: Code, Name, Order, Time Range/Duration, Actions                                                                                                           │
     │ - Button: Add Shift → Dialog                                                                                                                                           │
     │ - Dialog: Shift Form                                                                                                                                                   │
     │   - TextField: Code, Name                                                                                                                                              │
     │   - TextField (number): Order                                                                                                                                          │
     │   - If Fixed Model:                                                                                                                                                    │
     │       - TimePicker: Start Time, End Time                                                                                                                               │
     │   - If Flexible Model:                                                                                                                                                 │
     │       - TextField: Duration (hours)                                                                                                                                    │
     │     - MultiSelect: Allowed Start Times                                                                                                                                 │
     │   - Accordion: Breaks                                                                                                                                                  │
     │       - Add break: Type (meal/rest), Duration (minutes), Timing mode, Paid/Required                                                                                    │
     │                                                                                                                                                                        │
     │ MUI Components: RadioGroup, Table, Button, Dialog, TextField, TimePicker, Select, Accordion, Checkbox                                                                  │
     │                                                                                                                                                                        │
     │ Validation:                                                                                                                                                            │
     │ - At least 1 shift required                                                                                                                                            │
     │ - Unique shift codes                                                                                                                                                   │
     │ - Unique order values                                                                                                                                                  │
     │ - Start time < End time (fixed)                                                                                                                                        │
     │ - Valid time formats                                                                                                                                                   │
     │                                                                                                                                                                        │
     │ ---                                                                                                                                                                    │
     │ Step 7: Demand Calendar                                                                                                                                                │
     │                                                                                                                                                                        │
     │ Purpose: Define coverage requirements                                                                                                                                  │
     │                                                                                                                                                                        │
     │ UI Components:                                                                                                                                                         │
     │ - Calendar Grid:                                                                                                                                                       │
     │   - Rows: Date + Shift combinations                                                                                                                                    │
     │   - Columns: Team/Competency, Minimum, Ideal, Estimated                                                                                                                │
     │ - Date filter: Show specific week/month                                                                                                                                │
     │ - Bulk actions:                                                                                                                                                        │
     │   - Copy week pattern                                                                                                                                                  │
     │   - Apply to date range                                                                                                                                                │
     │   - Fill from template                                                                                                                                                 │
     │ - Button: Import CSV                                                                                                                                                   │
     │ - Button: Export CSV                                                                                                                                                   │
     │                                                                                                                                                                        │
     │ MUI Components: Box, Paper, Table (virtualized), TextField, DatePicker, Button, Menu, Dialog                                                                           │
     │                                                                                                                                                                        │
     │ Validation:                                                                                                                                                            │
     │ - Minimum ≤ Estimated ≤ Ideal                                                                                                                                          │
     │ - Non-negative values                                                                                                                                                  │
     │ - Valid shift references (from Step 6)                                                                                                                                 │
     │ - Valid team/competency references (from Step 3)                                                                                                                       │
     │ - Dates within temporal scope                                                                                                                                          │
     │                                                                                                                                                                        │
     │ ---                                                                                                                                                                    │
     │ Step 8: Constraints & Rules                                                                                                                                            │
     │                                                                                                                                                                        │
     │ Purpose: Configure scheduling constraints                                                                                                                              │
     │                                                                                                                                                                        │
     │ UI Components:                                                                                                                                                         │
     │ - Tabs: "Hard Constraints" | "Soft Constraints" | "Advanced"                                                                                                           │
     │ - Hard Constraints Tab:                                                                                                                                                │
     │   - List of constraint types with:                                                                                                                                     │
     │       - Checkbox: Enable/Disable                                                                                                                                       │
     │     - Expandable panel: Parameters (JSON editor or form)                                                                                                               │
     │ - Soft Constraints Tab:                                                                                                                                                │
     │   - Similar to hard but with:                                                                                                                                          │
     │       - Slider: Weight (0-100)                                                                                                                                         │
     │ - Advanced Tab (if feature enabled in Step 1):                                                                                                                         │
     │   - Day-off swapping rules                                                                                                                                             │
     │   - Break rules                                                                                                                                                        │
     │   - Priority hierarchy builder                                                                                                                                         │
     │                                                                                                                                                                        │
     │ MUI Components: Tabs, List, Checkbox, Slider, Accordion, TextField, Select, Button                                                                                     │
     │                                                                                                                                                                        │
     │ Validation:                                                                                                                                                            │
     │ - Valid parameter types                                                                                                                                                │
     │ - Non-negative weights                                                                                                                                                 │
     │                                                                                                                                                                        │
     │ ---                                                                                                                                                                    │
     │ Step 9: Optimization Settings                                                                                                                                          │
     │                                                                                                                                                                        │
     │ Purpose: Configure solver settings                                                                                                                                     │
     │                                                                                                                                                                        │
     │ UI Components:                                                                                                                                                         │
     │ - Select: Algorithm (with descriptions in tooltips)                                                                                                                    │
     │ - Slider: Max Time (1-60 minutes)                                                                                                                                      │
     │ - Section: Objectives                                                                                                                                                  │
     │   - Table: Goal, Weight, Priority                                                                                                                                      │
     │   - Button: Add Objective → Dialog                                                                                                                                     │
     │   - Dialog: Select goal, set weight/priority                                                                                                                           │
     │                                                                                                                                                                        │
     │ MUI Components: Select, Slider, Table, Button, Dialog, TextField, Tooltip                                                                                              │
     │                                                                                                                                                                        │
     │ Validation:                                                                                                                                                            │
     │ - Algorithm selected                                                                                                                                                   │
     │ - Max time > 0                                                                                                                                                         │
     │ - At least 1 objective                                                                                                                                                 │
     │                                                                                                                                                                        │
     │ ---                                                                                                                                                                    │
     │ Step 10: Review & Generate                                                                                                                                             │
     │                                                                                                                                                                        │
     │ Purpose: Final validation and file generation                                                                                                                          │
     │                                                                                                                                                                        │
     │ UI Components:                                                                                                                                                         │
     │ - Stepper Summary: Visual review of all steps (Accordion)                                                                                                              │
     │   - Each step shows summary with edit button                                                                                                                           │
     │ - Validation Section:                                                                                                                                                  │
     │   - Button: Validate → Calls Python validator                                                                                                                          │
     │   - Alert: Show validation results                                                                                                                                     │
     │   - List: Errors with "Jump to Step" buttons                                                                                                                           │
     │   - List: Warnings with descriptions                                                                                                                                   │
     │ - Preview Section:                                                                                                                                                     │
     │   - Tabs: "problem.json" | "demand.csv" | "schedule_input.csv"                                                                                                         │
     │   - Syntax-highlighted JSON viewer                                                                                                                                     │
     │   - CSV table preview                                                                                                                                                  │
     │ - Actions:                                                                                                                                                             │
     │   - Button: Download as ZIP                                                                                                                                            │
     │   - Button: Download Individual Files                                                                                                                                  │
     │   - Button: Copy JSON to Clipboard                                                                                                                                     │
     │   - Button: Save Project (localStorage)                                                                                                                                │
     │                                                                                                                                                                        │
     │ MUI Components: Accordion, Alert, Tabs, Button, Box, CircularProgress, Snackbar                                                                                        │
     │                                                                                                                                                                        │
     │ Generation Process:                                                                                                                                                    │
     │ 1. Collect all wizard state                                                                                                                                            │
     │ 2. Build problem.json using jsonGenerator.js                                                                                                                           │
     │ 3. Build demand.csv using demandCsvGenerator.js                                                                                                                        │
     │ 4. Build schedule_input.csv using scheduleInputCsvGenerator.js                                                                                                         │
     │ 5. Run Python validator (via backend API or WASM)                                                                                                                      │
     │ 6. Show results                                                                                                                                                        │
     │ 7. Allow download as ZIP or individual files                                                                                                                           │
     │                                                                                                                                                                        │
     │ ---                                                                                                                                                                    │
     │ Key Features                                                                                                                                                           │
     │                                                                                                                                                                        │
     │ Validation System                                                                                                                                                      │
     │                                                                                                                                                                        │
     │ - Per-Step Validation: Green checkmark on stepper when step is valid                                                                                                   │
     │ - Cross-Reference Validation: Validate references between steps                                                                                                        │
     │ - Real-Time Feedback: Inline error messages on form fields                                                                                                             │
     │ - Final Validation: Python validator.py integration                                                                                                                    │
     │ - Jump to Error: Click error → navigate to relevant step                                                                                                               │
     │                                                                                                                                                                        │
     │ User Experience                                                                                                                                                        │
     │                                                                                                                                                                        │
     │ - Auto-Save: Save to localStorage every 30 seconds                                                                                                                     │
     │ - Progress Persistence: Restore on page refresh                                                                                                                        │
     │ - Tooltips Everywhere: Explain each field using schema descriptions                                                                                                    │
     │ - Example Values: Show placeholder examples                                                                                                                            │
     │ - Keyboard Shortcuts: Ctrl+S (save), Ctrl+Enter (next step)                                                                                                            │
     │ - Responsive: Works on tablets                                                                                                                                         │
     │                                                                                                                                                                        │
     │ Data Import/Export                                                                                                                                                     │
     │                                                                                                                                                                        │
     │ - CSV Import: Employees, Schedule Input, Demand                                                                                                                        │
     │ - CSV Export: Schedule Input, Demand                                                                                                                                   │
     │ - JSON Import: Load existing problem.json to edit                                                                                                                      │
     │ - ZIP Download: All files bundled                                                                                                                                      │
     │ - Individual Downloads: problem.json, demand.csv, schedule_input.csv                                                                                                   │
     │                                                                                                                                                                        │
     │ Implementation Phases                                                                                                                                                  │
     │                                                                                                                                                                        │
     │ Phase 1: Foundation (Week 1)                                                                                                                                           │
     │                                                                                                                                                                        │
     │ - Create project structure                                                                                                                                             │
     │ - Set up Vite + React + MUI                                                                                                                                            │
     │ - Implement WizardContext                                                                                                                                              │
     │ - Build WizardStepper component                                                                                                                                        │
     │ - Implement Steps 1-2 (Quick Setup, Contracts)                                                                                                                         │
     │                                                                                                                                                                        │
     │ Phase 2: Core Data (Week 2)                                                                                                                                            │
     │                                                                                                                                                                        │
     │ - Implement Steps 3-4 (Org Units, Employees)                                                                                                                           │
     │ - Build reusable table components                                                                                                                                      │
     │ - CSV import functionality                                                                                                                                             │
     │                                                                                                                                                                        │
     │ Phase 3: Scheduling (Week 3)                                                                                                                                           │
     │                                                                                                                                                                        │
     │ - Implement Step 5 (Schedule Input Matrix)                                                                                                                             │
     │ - Implement Step 6 (Shifts)                                                                                                                                            │
     │ - Implement Step 7 (Demand Calendar)                                                                                                                                   │
     │                                                                                                                                                                        │
     │ Phase 4: Configuration (Week 4)                                                                                                                                        │
     │                                                                                                                                                                        │
     │ - Implement Steps 8-9 (Constraints, Optimization)                                                                                                                      │
     │ - Build constraint forms                                                                                                                                               │
     │                                                                                                                                                                        │
     │ Phase 5: Generation & Polish (Week 5)                                                                                                                                  │
     │                                                                                                                                                                        │
     │ - Implement Step 10 (Review & Generate)                                                                                                                                │
     │ - JSON/CSV generation logic                                                                                                                                            │
     │ - Python validator integration                                                                                                                                         │
     │ - File download functionality                                                                                                                                          │
     │ - Testing and bug fixes                                                                                                                                                │
     │                                                                                                                                                                        │
     │ Technical Implementation Notes                                                                                                                                         │
     │                                                                                                                                                                        │
     │ State Management                                                                                                                                                       │
     │                                                                                                                                                                        │
     │ // WizardContext structure                                                                                                                                             │
     │ {                                                                                                                                                                      │
     │   metadata: { problemId, createdAt, description, source },                                                                                                             │
     │   features: { useShiftBasedScheduling, ... },                                                                                                                          │
     │   temporalScope: { year, numDays, targetPeriod },                                                                                                                      │
     │   contracts: { definitions: [...] },                                                                                                                                   │
     │   employees: { model, simple/competency: [...] },                                                                                                                      │
     │   organizationalUnits: { teams/competencies: [...] },                                                                                                                  │
     │   scheduleInput: { dataMatrix, markingTypes },                                                                                                                         │
     │   demand: { shiftModel, shifts: [...], demandData: [...] },                                                                                                            │
     │   constraints: { hard: [...], soft: [...], advanced: {...} },                                                                                                          │
     │   optimization: { algorithm, maxTimeMinutes, objectives: [...] }                                                                                                       │
     │ }                                                                                                                                                                      │
     │                                                                                                                                                                        │
     │ MUI Theme Customization                                                                                                                                                │
     │                                                                                                                                                                        │
     │ - Primary color: Align with existing frontend                                                                                                                          │
     │ - Typography: Match existing app                                                                                                                                       │
     │ - Custom table styles for schedule matrix                                                                                                                              │
     │ - Responsive breakpoints                                                                                                                                               │
     │                                                                                                                                                                        │
     │ File Generation                                                                                                                                                        │
     │                                                                                                                                                                        │
     │ - Use JSZip to create ZIP archive                                                                                                                                      │
     │ - Use file-saver for browser downloads                                                                                                                                 │
     │ - CSV generation with proper escaping (PapaParse.unparse)                                                                                                              │
     │                                                                                                                                                                        │
     │ Validation                                                                                                                                                             │
     │                                                                                                                                                                        │
     │ - Client-side: Zod or Yup schemas per step                                                                                                                             │
     │ - Backend: POST to /api/validate endpoint calling validator.py                                                                                                         │
     │ - Display errors with file:line references                                                                                                                             │
     │                                                                                                                                                                        │
     │ Ready to implement! Starting with Phase 1.                                                                                                                             │
     ╰────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────╯
