import React, { useState } from 'react';
import { Box, Tabs, Tab, Alert, Button, Typography } from '@mui/material';
import { Add, Download } from '@mui/icons-material';
import StepLayout from '../components/wizard/StepLayout';
import StepCard from '../components/wizard/StepCard';
import EmployeeTable from '../components/employees/EmployeeTable';
import EmployeeForm, { newEmployee } from '../components/employees/EmployeeForm';
import CSVImporter from '../components/import/CSVImporter';
import CSVPreview from '../components/import/CSVPreview';
import ColumnMapper from '../components/import/ColumnMapper';
import ImportPreviewModal from '../components/shared/ImportPreviewModal';
import { ConfirmDialog } from '../components/shared/fields';
import { useWizard } from '../context/WizardContext';
import { removeEmployee, renameEmployee } from '../v4/operations';
import {
  EMPLOYEE_CSV_FIELDS, EMPLOYEE_CSV_REQUIRED, employeesFromRows, employeesTemplateCsv, employeesToCsv, formatCompetencies
} from '../v4/employeesCsv';
import { downloadText } from '../utils/download';

/**
 * Step 4: Employees — date-ranged contract membership and levelled competencies.
 */
const Step4_Employees = () => {
  const { state, transform } = useWizard();
  const employees = state.employees.list;
  const [tab, setTab] = useState(0);
  const [editing, setEditing] = useState(null); // null | employee (id '' = new)
  const [deleting, setDeleting] = useState(null);

  const [csvData, setCsvData] = useState(null);
  const [mapping, setMapping] = useState({});
  const [csvError, setCsvError] = useState('');
  const [pending, setPending] = useState(null);

  const saveEmployee = (employee) => {
    const original = editing.id;
    transform((s) => {
      const moved = original && original !== employee.id ? renameEmployee(s, original, employee.id) : s;
      const list = original
        ? moved.employees.list.map((e) => (e.id === original ? employee : e))
        : [...moved.employees.list, employee];
      return { ...moved, employees: { ...moved.employees, list } };
    });
    setEditing(null);
  };

  const handleParsed = (data) => {
    setCsvData(data);
    setCsvError('');
    setMapping(Object.fromEntries(EMPLOYEE_CSV_FIELDS.map((f) => [f, data.columns.includes(f) ? f : ''])));
  };

  const handleImport = () => {
    const missing = EMPLOYEE_CSV_REQUIRED.filter((f) => !mapping[f]);
    if (missing.length) return setCsvError(`Map the required columns: ${missing.join(', ')}`);
    const { employees: rows, warnings } = employeesFromRows(csvData.rows, mapping, state);
    if (!rows.length && !warnings.length) return setCsvError('No rows found');
    setPending({ rows, warnings });
    return null;
  };

  const confirmImport = () => {
    transform((s) => ({ ...s, employees: { ...s.employees, list: [...s.employees.list, ...pending.rows] } }));
    setPending(null);
    setCsvData(null);
    setTab(0);
  };

  return (
    <StepLayout
      stepId="employees"
      title="Employees"
      subtitle="Who can work, under which contract, and which coverage coordinates they hold at what level."
      actions={<Button variant="contained" startIcon={<Add />} onClick={() => setEditing(newEmployee(state))} disabled={!state.contracts.definitions.length}>Add employee</Button>}
      nextDisabled={!employees.length}
    >
      <StepCard>
        {!state.contracts.definitions.length && <Alert severity="warning" sx={{ mb: 2 }}>Define contracts first (step 2).</Alert>}
        {!state.demand.dimensions.length && <Alert severity="warning" sx={{ mb: 2 }}>Declare dimensions first (step 3) so employees can hold them.</Alert>}
        <Tabs value={tab} onChange={(_, v) => setTab(v)} sx={{ mb: 2 }}>
          <Tab label={`Roster (${employees.length})`} />
          <Tab label="Import / export CSV" />
        </Tabs>

        {tab === 0 && (employees.length
          ? <EmployeeTable employees={employees} scope={state.temporalScope} onEdit={setEditing} onDelete={setDeleting} />
          : <Alert severity="info">No employees yet. Add them one by one or import a CSV.</Alert>)}

        {tab === 1 && (
          <Box>
            <Box sx={{ mb: 2, display: 'flex', justifyContent: 'flex-end', gap: 1 }}>
              <Button size="small" startIcon={<Download />} disabled={!employees.length}
                onClick={() => downloadText('employees.csv', employeesToCsv(state))}
              >
                Export roster
              </Button>
              <Button size="small" startIcon={<Download />} onClick={() => downloadText('employees_template.csv', employeesTemplateCsv(state))}>
                Template
              </Button>
            </Box>
            <Alert severity="info" sx={{ mb: 2 }}>
              Columns <code>employee_id,name,contract_type,competencies</code>. Competencies are
              <code> tableName/tableValue:level</code> separated by commas, e.g.
              <code> Team/T1:1,Responsibility/A:2</code> — level 1 is the highest and the default.
              Imported assignments run open-ended from {state.temporalScope.start || 'the horizon start'}.
              Example: <code>{employees[0] ? formatCompetencies(employees[0].competencyAssignments) || '—' : 'Team/T1:1'}</code>
            </Alert>
            {!csvData ? (
              <CSVImporter onDataParsed={handleParsed} onError={setCsvError} />
            ) : (
              <>
                <CSVPreview data={csvData} maxRows={5} />
                <Box sx={{ mt: 2 }}>
                  <ColumnMapper csvColumns={csvData.columns} fieldMappings={mapping} onMappingChange={setMapping} requiredFields={EMPLOYEE_CSV_REQUIRED} />
                </Box>
                <Box sx={{ mt: 2, display: 'flex', gap: 1 }}>
                  <Button variant="contained" onClick={handleImport}>Import employees</Button>
                  <Button variant="outlined" onClick={() => { setCsvData(null); setCsvError(''); }}>Cancel</Button>
                </Box>
              </>
            )}
            {csvError && <Alert severity="error" sx={{ mt: 2 }}>{csvError}</Alert>}
          </Box>
        )}
      </StepCard>

      {editing && (
        <EmployeeForm
          open
          employee={editing}
          state={state}
          existingIds={employees.map((e) => e.id).filter((id) => id !== editing.id)}
          onClose={() => setEditing(null)}
          onSave={saveEmployee}
        />
      )}

      <ConfirmDialog
        open={!!deleting}
        title={`Delete ${deleting?.id}?`}
        confirmLabel="Delete"
        confirmColor="error"
        onCancel={() => setDeleting(null)}
        onConfirm={() => { transform((s) => removeEmployee(s, deleting.id)); setDeleting(null); }}
      >
        Their schedule-input row is removed too.
      </ConfirmDialog>

      <ImportPreviewModal
        open={!!pending}
        title={`Import ${pending?.rows.length ?? 0} employee(s)`}
        summary={pending ? `${pending.rows.length} will be added; ${pending.warnings.length} row(s) skipped.` : ''}
        warnings={pending?.warnings || []}
        rows={(pending?.rows || []).map((e) => ({
          id: e.id, name: e.name, contract: e.contractAssignments[0].contractType, competencies: formatCompetencies(e.competencyAssignments)
        }))}
        columns={[
          { field: 'id', label: 'ID' }, { field: 'name', label: 'Name' },
          { field: 'contract', label: 'Contract' }, { field: 'competencies', label: 'Competencies' }
        ]}
        onConfirm={confirmImport}
        onCancel={() => setPending(null)}
      />
      {!employees.length && tab === 0 && (
        <Typography variant="caption" color="text.secondary">Each employee needs a contract; competencies can be added later.</Typography>
      )}
    </StepLayout>
  );
};

export default Step4_Employees;
