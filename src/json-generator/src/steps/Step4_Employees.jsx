import React, { useState } from 'react';
import { Typography, Box, Tabs, Tab, Alert, Chip, Button } from '@mui/material';
import { Download as DownloadIcon } from '@mui/icons-material';
import StepCard from '../components/wizard/StepCard';
import NavigationButtons from '../components/wizard/NavigationButtons';
import EmployeeTable from '../components/employees/EmployeeTable';
import CSVImporter from '../components/import/CSVImporter';
import CSVPreview from '../components/import/CSVPreview';
import ColumnMapper from '../components/import/ColumnMapper';
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

    // Validate mappings
    const requiredFields = ['employee_id', 'contract_type', 'teams'];  // Always require teams

    const missingMappings = requiredFields.filter(field => !columnMappings[field]);
    if (missingMappings.length > 0) {
      setCsvError(`Please map required fields: ${missingMappings.join(', ')}`);
      return;
    }

    try {
      const newEmployees = csvData.rows.map((row, index) => {
        const empId = row[columnMappings.employee_id]?.trim();
        if (!empId) {
          throw new Error(`Row ${index + 1}: Employee ID is empty`);
        }

        const contractType = row[columnMappings.contract_type]?.trim();
        if (!contractType) {
          throw new Error(`Row ${index + 1}: Contract type is empty`);
        }

        const employee = {
          id: empId,
          name: row[columnMappings.name]?.trim() || empId,
          contractType: contractType
        };

        // Parse teams (format depends on employee model)
        const teamsStr = row[columnMappings.teams];
        if (!teamsStr) {
          throw new Error(`Row ${index + 1}: Teams field is empty`);
        }

        if (employeeModel === 'team') {
          // Team model: Parse teams as simple codes "A,B,C"
          employee.teams = teamsStr.split(',').map(t => t.trim()).filter(t => t);
          if (employee.teams.length === 0) {
            throw new Error(`Row ${index + 1}: No valid teams found`);
          }
          // Validate team codes exist
          const validTeamCodes = teams.map(t => t.code);
          const invalidTeams = employee.teams.filter(t => !validTeamCodes.includes(t));
          if (invalidTeams.length > 0) {
            throw new Error(`Row ${index + 1}: Invalid team codes: ${invalidTeams.join(', ')}. Valid teams: ${validTeamCodes.join(', ')}`);
          }
        } else {
          // Competency model: Parse teams with levels "EG:1,CAJ:2"
          employee.teams = teamsStr.split(',').map(t => {
            const parts = t.trim().split(':');
            if (parts.length !== 2) {
              throw new Error(`Row ${index + 1}: Invalid team format "${t.trim()}". Expected format: CODE:LEVEL`);
            }
            const code = parts[0].trim();
            const level = parseInt(parts[1].trim());
            if (isNaN(level) || level < 1) {
              throw new Error(`Row ${index + 1}: Invalid competency level for team "${code}"`);
            }
            const teamInfo = teams.find(team => team.code === code);
            if (!teamInfo) {
              throw new Error(`Row ${index + 1}: Unknown team code "${code}". Valid teams: ${teams.map(t => t.code).join(', ')}`);
            }
            return {
              code: code,
              name: teamInfo.name,
              level: level
            };
          });
          if (employee.teams.length === 0) {
            throw new Error(`Row ${index + 1}: No valid teams found`);
          }
        }

        return employee;
      });

      // Success - add to employees
      handleEmployeesChange([...employees, ...newEmployees]);
      setCsvData(null);
      setColumnMappings({});
      setCurrentTab(0);  // Switch to Manual Entry tab to see imported employees
      setCsvError('');
    } catch (err) {
      setCsvError(err.message);
    }
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
              {/* Download Template Button */}
              <Box sx={{ mb: 2, textAlign: 'right' }}>
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
    </Box>
  );
};

export default Step4_Employees;
