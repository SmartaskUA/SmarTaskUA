import React, { useState } from 'react';
import {
  Box,
  Button,
  Table,
  TableBody,
  TableCell,
  TableContainer,
  TableHead,
  TableRow,
  Paper,
  IconButton,
  Chip,
  Typography,
  Alert
} from '@mui/material';
import {
  Add as AddIcon,
  Edit as EditIcon,
  Delete as DeleteIcon
} from '@mui/icons-material';
import EmployeeForm from './EmployeeForm';

/**
 * EmployeeTable Component
 *
 * Table displaying all employees with CRUD operations.
 * Adapts columns based on employee model (team vs competency).
 */
const EmployeeTable = ({
  employees = [],
  onChange,
  employeeModel,
  availableTeams = [],
  availableCompetencies = [],
  availableContracts = [],
  error
}) => {
  const [openDialog, setOpenDialog] = useState(false);
  const [editingEmployee, setEditingEmployee] = useState(null);

  const handleAdd = () => {
    setEditingEmployee(null);
    setOpenDialog(true);
  };

  const handleEdit = (employee) => {
    setEditingEmployee(employee);
    setOpenDialog(true);
  };

  const handleDelete = (idToDelete) => {
    onChange(employees.filter(e => e.id !== idToDelete));
  };

  const handleSave = (employeeData) => {
    if (editingEmployee) {
      // Update existing
      onChange(
        employees.map(e =>
          e.id === editingEmployee.id ? employeeData : e
        )
      );
    } else {
      // Add new
      onChange([...employees, employeeData]);
    }
  };

  const existingIds = employees.map(e => e.id);

  return (
    <Box>
      {/* Header */}
      <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', mb: 2 }}>
        <Typography variant="h6">
          Employees ({employees.length})
        </Typography>
        <Button
          variant="contained"
          startIcon={<AddIcon />}
          onClick={handleAdd}
        >
          Add Employee
        </Button>
      </Box>

      {/* Error from parent */}
      {error && (
        <Alert severity="error" sx={{ mb: 2 }}>
          {error}
        </Alert>
      )}

      {/* Table */}
      {employees.length === 0 ? (
        <Alert severity="info">
          No employees added yet. Click "Add Employee" to add your first employee.
        </Alert>
      ) : (
        <TableContainer component={Paper} variant="outlined" sx={{ maxHeight: 500 }}>
          <Table stickyHeader>
            <TableHead>
              <TableRow>
                <TableCell>ID</TableCell>
                <TableCell>Name</TableCell>
                {employeeModel === 'team' && <TableCell>Teams</TableCell>}
                {employeeModel === 'competency' && <TableCell>Competencies</TableCell>}
                <TableCell>Contract</TableCell>
                <TableCell align="right">Actions</TableCell>
              </TableRow>
            </TableHead>
            <TableBody>
              {employees.map((employee) => (
                <TableRow key={employee.id} hover>
                  <TableCell>
                    <Chip label={employee.id} size="small" color="primary" variant="outlined" />
                  </TableCell>
                  <TableCell>
                    <Typography>{employee.name || employee.id}</Typography>
                  </TableCell>

                  {/* Team Model: Show teams with names */}
                  {employeeModel === 'team' && (
                    <TableCell>
                      <Box sx={{ display: 'flex', gap: 0.5, flexWrap: 'wrap' }}>
                        {employee.teams?.map((teamCode) => {
                          const team = availableTeams.find(t => t.code === teamCode);
                          const label = team ? `${team.code} - ${team.name}` : teamCode;
                          return (
                            <Chip key={teamCode} label={label} size="small" color="info" />
                          );
                        })}
                      </Box>
                    </TableCell>
                  )}

                  {/* Competency Model: Show competencies with levels */}
                  {employeeModel === 'competency' && (
                    <TableCell>
                      <Box sx={{ display: 'flex', gap: 0.5, flexWrap: 'wrap' }}>
                        {employee.competencies?.map((comp) => (
                          <Chip
                            key={comp.code}
                            label={`${comp.code} (L${comp.level})`}
                            size="small"
                            color="success"
                          />
                        ))}
                      </Box>
                    </TableCell>
                  )}

                  <TableCell>
                    <Typography variant="body2">{employee.contractType}</Typography>
                  </TableCell>
                  <TableCell align="right">
                    <IconButton
                      size="small"
                      onClick={() => handleEdit(employee)}
                      sx={{ mr: 1 }}
                    >
                      <EditIcon />
                    </IconButton>
                    <IconButton
                      size="small"
                      color="error"
                      onClick={() => handleDelete(employee.id)}
                    >
                      <DeleteIcon />
                    </IconButton>
                  </TableCell>
                </TableRow>
              ))}
            </TableBody>
          </Table>
        </TableContainer>
      )}

      {/* Dialog */}
      <EmployeeForm
        open={openDialog}
        onClose={() => setOpenDialog(false)}
        onSave={handleSave}
        editingEmployee={editingEmployee}
        employeeModel={employeeModel}
        existingIds={existingIds}
        availableTeams={availableTeams}
        availableCompetencies={availableCompetencies}
        availableContracts={availableContracts}
      />
    </Box>
  );
};

export default EmployeeTable;
