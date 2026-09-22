import React, { useState } from 'react';
import { Typography, Box, Tabs, Tab, Alert, Chip, Button, Tooltip } from '@mui/material';
import { Download as DownloadIcon } from '@mui/icons-material';
import StepCard from '../components/wizard/StepCard';
import NavigationButtons from '../components/wizard/NavigationButtons';
import EmployeeTable from '../components/employees/EmployeeTable';
import CSVImporter from '../components/import/CSVImporter';
import CSVPreview from '../components/import/CSVPreview';
import ColumnMapper from '../components/import/ColumnMapper';
import ImportPreviewModal from '../components/shared/ImportPreviewModal';
import { useWizard } from '../context/WizardContext';
import Papa from 'papaparse';

/**
 * Step 4: Employees
 *
 * Define employee roster with manual entry or CSV import.
 * Adapts fields based on employee model from Step 1.
 */
const Step4_Employees = () => {
  const { state, updateState } = useWizard();
  const [currentTab, setCurrentTab] = useState(0);
  const [error, setError] = useState('');
  const [csvError, setCsvError] = useState('');

  // CSV import state
  const [csvData, setCsvData] = useState(null);
  const [columnMappings, setColumnMappings] = useState({});

  // Import preview modal state
  const [pendingEmployees, setPendingEmployees] = useState(null);
  const [importModalOpen, setImportModalOpen] = useState(false);

  // Get state values
  const employeeModel = state.employees.model;
  const employees = employeeModel === 'team' ? state.employees.simple : state.employees.competency;
  const teams = state.organizationalUnits.teams || [];  // Always use teams for both models
  const contracts = state.contracts.definitions.map(c => c.id);

  // Handlers
  const handleEmployeesChange = (newEmployees) => {
    const stateKey = employeeModel === 'team' ? 'employees.simple' : 'employees.competency';
    updateState(stateKey, newEmployees);
    if (error) setError('');
  };

  // CSV Import Handlers
  const handleCsvDataParsed = (data) => {
    setCsvData(data);
    setCsvError('');

    // Initialize column mappings (always use "teams" for both models)
    setColumnMappings({
      employee_id: '',
      name: '',
      teams: '',
      contract_type: ''
    });
  };

  const handleImportCsv = () => {
    if (!csvData) {
      setCsvError('No CSV data loaded');
      return;
    }

    const requiredFields = ['employee_id', 'contract_type', 'teams'];
    const missingMappings = requiredFields.filter(field => !columnMappings[field]);
    if (missingMappings.length > 0) {
      setCsvError(`Please map required fields: ${missingMappings.join(', ')}`);
      return;
    }

    const existingIds = new Set(employees.map(e => e.id));
    const validContractIds = new Set(contracts);
    const validRows = [];
    const warnings = [];
    const previewRows = [];

    for (let index = 0; index < csvData.rows.length; index++) {
      const row = csvData.rows[index];
      try {
        const empId = row[columnMappings.employee_id]?.trim();
        if (!empId) { warnings.push(`Row ${index + 1}: Employee ID is empty — skipped`); continue; }

        const contractType = row[columnMappings.contract_type]?.trim();
        if (!contractType) { warnings.push(`Row ${index + 1}: Contract type is empty — skipped`); continue; }

        if (existingIds.has(empId)) {
          warnings.push(`Row ${index + 1}: Employee "${empId}" already exists — skipped`);
          continue;
        }

        if (!validContractIds.has(contractType)) {
          warnings.push(`Row ${index + 1}: Unknown contract type "${contractType}" (valid: ${[...validContractIds].join(', ')}) — skipped`);
          continue;
        }

        const employee = {
          id: empId,
          name: row[columnMappings.name]?.trim() || empId,
          contractType
        };

        const teamsStr = row[columnMappings.teams];
        if (!teamsStr) { warnings.push(`Row ${index + 1}: Teams field is empty — skipped`); continue; }

        if (employeeModel === 'team') {
          employee.teams = teamsStr.split(',').map(t => t.trim()).filter(t => t);
          if (employee.teams.length === 0) { warnings.push(`Row ${index + 1}: No valid teams — skipped`); continue; }
          const validTeamCodes = teams.map(t => t.code);
          const invalidTeams = employee.teams.filter(t => !validTeamCodes.includes(t));
          if (invalidTeams.length > 0) { warnings.push(`Row ${index + 1}: Invalid team codes: ${invalidTeams.join(', ')} — skipped`); continue; }
        } else {
          const parsed = [];
          let rowError = null;
          for (const t of teamsStr.split(',')) {
            const parts = t.trim().split(':');
            if (parts.length !== 2) { rowError = `Invalid team format "${t.trim()}" — expected CODE:LEVEL`; break; }
            const code = parts[0].trim();
            const level = parseInt(parts[1].trim());
            if (isNaN(level) || level < 1) { rowError = `Invalid competency level for team "${code}"`; break; }
            const teamInfo = teams.find(tm => tm.code === code);
            if (!teamInfo) { rowError = `Unknown team code "${code}"`; break; }
            parsed.push({ code, name: teamInfo.name, level });
          }
          if (rowError) { warnings.push(`Row ${index + 1}: ${rowError} — skipped`); continue; }
          employee.teams = parsed;
        }

        validRows.push(employee);
        if (previewRows.length < 10) {
          const teamsDisplay = employeeModel === 'team'
            ? employee.teams.join(', ')
            : employee.teams.map(t => `${t.code}:${t.level}`).join(', ');
          previewRows.push({ id: employee.id, name: employee.name, teams: teamsDisplay, contractType: employee.contractType });
        }
      } catch (err) {
        warnings.push(`Row ${index + 1}: ${err.message} — skipped`);
      }
    }

    if (validRows.length === 0 && warnings.length === 0) {
      setCsvError('No valid rows found in CSV');
      return;
    }

    setPendingEmployees({ validRows, previewRows });
    setImportModalOpen(true);
    setCsvError('');
  };

  const handleImportConfirm = () => {
    if (!pendingEmployees) return;
    handleEmployeesChange([...employees, ...pendingEmployees.validRows]);
    setPendingEmployees(null);
    setImportModalOpen(false);
    setCsvData(null);
    setColumnMappings({});
    setCurrentTab(0);
  };

  const handleDownloadTemplate = () => {
    // Always use "teams" column for both models
    const headers = ['employee_id', 'name', 'teams', 'contract_type'];

    let sampleTeams;
    if (employeeModel === 'team') {
      // Team model: Use team codes from defined teams (e.g., "A,B")
      sampleTeams = teams.length > 0
        ? teams.slice(0, 2).map(t => t.code).join(',')
        : 'A,B';
    } else {
      // Competency model: Use team codes with levels (e.g., "EG:1,CAJ:2")
      sampleTeams = teams.length > 0
        ? teams.slice(0, 2).map(t => `${t.code}:1`).join(',')
        : 'EG:1,CAJ:2';
    }

    const sampleRow = ['EMP001', 'John Doe', sampleTeams, contracts[0] || 'fullTime_8h'];

    const csv = Papa.unparse({
      fields: headers,
      data: [sampleRow]
    });

    const blob = new Blob([csv], { type: 'text/csv;charset=utf-8;' });
    const link = document.createElement('a');
    link.href = URL.createObjectURL(blob);
    link.download = `employees_template_${employeeModel}.csv`;
    link.click();
  };

  const handleDownloadCurrentEmployees = () => {
    const headers = ['employee_id', 'name', 'teams', 'contract_type'];
    const rows = employees.map(emp => {
      const teamsStr = employeeModel === 'team'
        ? (emp.teams || []).join(',')
        : (emp.teams || []).map(t => `${t.code}:${t.level}`).join(',');
      return [emp.id, emp.name, teamsStr, emp.contractType];
    });
    const csv = Papa.unparse({ fields: headers, data: rows });
    const blob = new Blob([csv], { type: 'text/csv;charset=utf-8;' });
    const link = document.createElement('a');
    link.href = URL.createObjectURL(blob);
    link.download = `employees_export_${employeeModel}.csv`;
    link.click();
  };

  // Validation
  const validate = () => {
    if (employees.length === 0) {
      setError('At least one employee is required');
      return false;
    }
    return true;
  };

  const handleNext = () => {
    return validate();
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
          Employees
        </Typography>
        <Typography variant="body1" color="text.secondary">
          Define your employee roster with manual entry or CSV import.
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
          {/* Tabs */}
          <Tabs value={currentTab} onChange={(e, newValue) => setCurrentTab(newValue)} sx={{ mb: 2 }}>
            <Tab label="Manual Entry" />
            <Tab label="Import CSV" />
          </Tabs>

          {/* Tab 1: Manual Entry */}
          {currentTab === 0 && (
            <Box>
              <EmployeeTable
                employees={employees}
                onChange={handleEmployeesChange}
                employeeModel={employeeModel}
                availableTeams={teams}
                availableContracts={contracts}
                error={error}
              />
            </Box>
          )}

          {/* Tab 2: CSV Import */}
          {currentTab === 1 && (
            <Box>
              {/* Download Buttons */}
              <Box sx={{ mb: 2, display: 'flex', justifyContent: 'flex-end', gap: 1 }}>
                <Tooltip title={employees.length === 0 ? 'No employees to export' : ''}>
                  <span>
                    <Button
                      size="small"
                      startIcon={<DownloadIcon />}
                      onClick={handleDownloadCurrentEmployees}
                      disabled={employees.length === 0}
                    >
                      Download Current Employees
                    </Button>
                  </span>
                </Tooltip>
                <Button
                  size="small"
                  startIcon={<DownloadIcon />}
                  onClick={handleDownloadTemplate}
                >
                  Download CSV Template
                </Button>
              </Box>

              {/* CSV Importer */}
              {!csvData ? (
                <CSVImporter
                  onDataParsed={handleCsvDataParsed}
                  onError={setCsvError}
                />
              ) : (
                <>
                  {/* CSV Preview */}
                  <CSVPreview data={csvData} maxRows={5} />

                  {/* Column Mapper */}
                  <Box sx={{ mt: 3 }}>
                    <ColumnMapper
                      csvColumns={csvData.columns}
                      fieldMappings={columnMappings}
                      onMappingChange={setColumnMappings}
                      requiredFields={['employee_id', 'contract_type', 'teams']}
                    />
                  </Box>

                  {/* Format Instructions */}
                  <Alert severity="info" sx={{ mt: 2 }}>
                    <Typography variant="subtitle2" gutterBottom>
                      Format Instructions:
                    </Typography>
                    {employeeModel === 'team' ? (
                      <>
                        <Typography variant="body2">
                          • <strong>Teams</strong>: Comma-separated team codes (e.g., "A,B,C")
                        </Typography>
                        <Typography variant="body2" sx={{ mt: 0.5 }}>
                          Valid team codes: {teams.map(t => t.code).join(', ') || 'None defined yet'}
                        </Typography>
                      </>
                    ) : (
                      <>
                        <Typography variant="body2">
                          • <strong>Teams</strong>: CODE:LEVEL pairs separated by commas (e.g., "EG:1,CAJ:2")
                        </Typography>
                        <Typography variant="body2" sx={{ mt: 0.5 }}>
                          Valid team codes: {teams.map(t => t.code).join(', ') || 'None defined yet'}
                        </Typography>
                        <Typography variant="body2" sx={{ mt: 0.5 }}>
                          Levels indicate competency proficiency for each team
                        </Typography>
                      </>
                    )}
                    <Typography variant="body2">
                      • <strong>Contract Type</strong>: Must match contract ID from Step 2
                    </Typography>
                  </Alert>

                  {/* Import Buttons */}
                  <Box sx={{ mt: 2, display: 'flex', gap: 1 }}>
                    <Button
                      variant="contained"
                      onClick={handleImportCsv}
                    >
                      Import Employees
                    </Button>
                    <Button
                      variant="outlined"
                      onClick={() => {
                        setCsvData(null);
                        setColumnMappings({});
                        setCsvError('');
                      }}
                    >
                      Cancel
                    </Button>
                  </Box>
                </>
              )}

              {/* CSV Error */}
              {csvError && (
                <Alert severity="error" sx={{ mt: 2 }}>
                  {csvError}
                </Alert>
              )}
            </Box>
          )}
        </StepCard>
      </Box>

      {/* NAVIGATION - Fixed at bottom */}
      <Box sx={{ flexShrink: 0, mt: 2 }}>
        <NavigationButtons
          onNext={handleNext}
          nextDisabled={employees.length === 0}
        />
      </Box>

      {/* Import Preview Confirmation Modal */}
      <ImportPreviewModal
        open={importModalOpen}
        title={`Import Preview — ${pendingEmployees?.validRows?.length ?? 0} employee(s)`}
        summary={`${pendingEmployees?.validRows?.length ?? 0} employees will be added to the roster.`}
        warnings={[]}
        rows={pendingEmployees?.previewRows || []}
        columns={[
          { field: 'id', label: 'Employee ID' },
          { field: 'name', label: 'Name' },
          { field: 'teams', label: 'Teams' },
          { field: 'contractType', label: 'Contract Type' }
        ]}
        onConfirm={handleImportConfirm}
        onCancel={() => { setImportModalOpen(false); setPendingEmployees(null); }}
      />
    </Box>
  );
};

export default Step4_Employees;
