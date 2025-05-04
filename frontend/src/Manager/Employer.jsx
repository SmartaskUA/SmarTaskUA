import React, { useState, useEffect } from "react";
import axios from "axios";
import Sidebar_Manager from "../components/Sidebar_Manager";
import SearchBar from "../components/manager/SearchBar";
import {
  Table, TableBody, TableCell, TableContainer, TableHead, TableRow,
  Typography, CircularProgress, Box, Button, Dialog, DialogTitle,
  DialogContent, DialogActions, TextField, FormControl, InputLabel,
  Select, MenuItem, OutlinedInput, Checkbox, ListItemText, IconButton
} from "@mui/material";
import DeleteIcon from '@mui/icons-material/Delete';
import BaseUrl from "../components/BaseUrl";

const teamOptions = ["A", "B"];

const Employer = () => {
  const [employees, setEmployees] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [openAddDialog, setOpenAddDialog] = useState(false);
  const [newEmployee, setNewEmployee] = useState({ id: "", name: "", team: [] });
  const [openEditDialog, setOpenEditDialog] = useState(false);
  const [selectedEmployee, setSelectedEmployee] = useState(null);
  const [openConfirmDialog, setOpenConfirmDialog] = useState(false);
  const [employeeToDelete, setEmployeeToDelete] = useState(null);
  const [removalMode, setRemovalMode] = useState(false);
  const [filteredEmployees, setFilteredEmployees] = useState([]);

  useEffect(() => {
    fetchEmployees();
  }, []);

  const fetchEmployees = () => {
    setLoading(true);
    axios.get(`${BaseUrl}/api/v1/employees/`)
      .then((response) => {
        setEmployees(response.data);
        setFilteredEmployees(response.data);
        setLoading(false);
        console.log(response.data);
      })
      .catch(() => {
        setError("Erro ao buscar employees.");
        setLoading(false);
      });
  };

  const handleSearch = (query) => {
    if (query) {
      const filtered = employees.filter(employee =>
        employee.id.toString().includes(query)
      );
      setFilteredEmployees(filtered);
    } else {
      setFilteredEmployees(employees);
    }
  };

  const handleRemoveEmployee = (id) => {
    axios.delete(`${BaseUrl}/api/v1/employees/${id}`).then(fetchEmployees)
      .catch((error) => console.error("Erro ao remover employee:", error));
  };

  const handleOpenEditDialog = (employee) => {
    setSelectedEmployee(employee);
    setOpenEditDialog(true);
  };

  const handleEditEmployee = () => {
    axios.put(`${BaseUrl}/api/v1/employees/${selectedEmployee.id}`, selectedEmployee)
      .then(() => { setOpenEditDialog(false); setSelectedEmployee(null); fetchEmployees(); })
      .catch((error) => console.error("Erro ao editar employee:", error));
  };

  const handleAddEmployee = () => {
    axios.post(`${BaseUrl}/api/v1/employees/`, newEmployee)
      .then(() => { setOpenAddDialog(false); setNewEmployee({ id: "", name: "", team: [] }); fetchEmployees(); })
      .catch((error) => console.error("Erro ao adicionar employee:", error));
  };

  const handleOpenConfirmDialog = (employee) => {
    setEmployeeToDelete(employee);
    setOpenConfirmDialog(true);
  };

  const handleConfirmDelete = () => {
    if (employeeToDelete) {
      handleRemoveEmployee(employeeToDelete.id);
    }
    setOpenConfirmDialog(false);
    setEmployeeToDelete(null);
  };

  const handleCancelDelete = () => {
    setOpenConfirmDialog(false);
    setEmployeeToDelete(null);
  };

  const toggleRemovalMode = () => {
    setRemovalMode(!removalMode);
  };

  const disableBackgroundInteraction = (disable) => {
    const rootElement = document.getElementById('root');
    if (disable) {
      rootElement.setAttribute('inert', ''); 
    } else {
      rootElement.removeAttribute('inert'); 
    }
  };

  return (
    <div className="admin-container" style={{ display: "flex", minHeight: "100vh" }}>
      <Sidebar_Manager />
      <div className="main-content" style={{ flex: 1, padding: "20px" }}>
        <Box mb={4} display="flex" justifyContent="space-between" alignItems="center">
          <Typography variant="h4">List of Employees</Typography>
          <Box>
            <Button variant="contained" color="success" onClick={() => { setOpenAddDialog(true); disableBackgroundInteraction(true); }}>
              Add Employee
            </Button>
            <Button
              variant="contained"
              color="error"
              onClick={toggleRemovalMode}
              style={{ marginLeft: "10px" }}
            >
              {removalMode ? "Cancelar Remoção" : "Remover Employees"}
            </Button>
          </Box>
        </Box>

        <SearchBar onSearch={handleSearch} />

        {loading ? (
          <Box display="flex" justifyContent="center" alignItems="center" minHeight="60vh">
            <CircularProgress size={60} />
          </Box>
        ) : error ? (
          <Box display="flex" justifyContent="center" alignItems="center" minHeight="60vh">
            <Typography variant="h6" color="error" align="center">
              {error}
            </Typography>
          </Box>
        ) : filteredEmployees.length > 0 ? (
          <>
            <TableContainer style={{ borderRadius: 8 }}>
              <Table>
                <TableHead style={{ backgroundColor: "#1976d2", color: "#fff" }}>
                  <TableRow>
                    <TableCell style={{ color: "#fff", fontWeight: "bold" }}>ID</TableCell>
                    <TableCell style={{ color: "#fff", fontWeight: "bold" }}>Nome</TableCell>
                    <TableCell style={{ color: "#fff", fontWeight: "bold" }}>Equipa</TableCell>
                    <TableCell style={{ color: "#fff", fontWeight: "bold" }}>Restrições</TableCell>

                    <TableCell style={{ color: "#fff", fontWeight: "bold" }}></TableCell>
                    <TableCell style={{ color: "#fff", fontWeight: "bold" }}></TableCell>
                  </TableRow>
                </TableHead>
                <TableBody>
                  {filteredEmployees.map((emp, index) => {
                    const rowStyle = index % 2 === 0
                      ? { backgroundColor: "#f2f2f2" }
                      : { backgroundColor: "#ffffff" };

                    const teamDisplay = Array.isArray(emp.team)
                      ? emp.team.join(" e ")
                      : emp.team
                        ? emp.team.name
                        : "N/A";

                    return (
                      <TableRow key={emp.id} style={rowStyle}>
                        <TableCell>{emp.id}</TableCell>
                        <TableCell>{emp.name}</TableCell>
                        <TableCell>{teamDisplay}</TableCell>
                        <TableCell>
                          {emp.restrictions && Object.keys(emp.restrictions).length > 0 ? (
                            Object.entries(emp.restrictions).map(([key, value]) => (
                              <div key={key}>
                                {key}: {value.toString()}
                              </div>
                            ))
                          ) : (
                            <em>Sem restrições</em>
                          )}
                        </TableCell>

                        <TableCell>
                          {removalMode && (
                            <IconButton
                              color="error"
                              onClick={() => handleOpenConfirmDialog(emp)}
                            >
                              <DeleteIcon />
                            </IconButton>
                          )}
                        </TableCell>
                        <TableCell>
                          <Button
                            variant="contained"
                            color="primary"
                            onClick={() => handleOpenEditDialog(emp)}
                          >
                            Edit
                          </Button>
                        </TableCell>
                      </TableRow>
                    );
                  })}
                </TableBody>
              </Table>
            </TableContainer>
          </>
        ) : (
          <Box display="flex" flexDirection="column" justifyContent="center" alignItems="center" minHeight="60vh">
            <Typography variant="h6">Nenhum employee encontrado.</Typography>
            <Box mt={2}>
              <Button variant="contained" color="success" onClick={() => { setOpenAddDialog(true); disableBackgroundInteraction(true); }}>
                Add Employee
              </Button>
            </Box>
          </Box>
        )}
        <Dialog open={openAddDialog} onClose={() => { setOpenAddDialog(false); disableBackgroundInteraction(false); }}>
          <DialogTitle>Add Employee</DialogTitle>
          <DialogContent>
            <TextField
              margin="dense"
              label="ID"
              fullWidth
              value={newEmployee.id}
              onChange={(e) => setNewEmployee({ ...newEmployee, id: e.target.value })}
            />
            <TextField
              margin="dense"
              label="Nome"
              fullWidth
              value={newEmployee.name}
              onChange={(e) => setNewEmployee({ ...newEmployee, name: e.target.value })}
            />
            <FormControl fullWidth margin="dense">
              <InputLabel id="team-label">Equipa</InputLabel>
              <Select
                labelId="team-label"
                multiple
                value={newEmployee.team}
                onChange={(e) => setNewEmployee({ ...newEmployee, team: e.target.value })}
                input={<OutlinedInput label="Equipa" />}
                renderValue={(selected) => selected.join(" e ")}
              >
                {teamOptions.map((team) => (
                  <MenuItem key={team} value={team}>
                    <Checkbox checked={newEmployee.team.indexOf(team) > -1} />
                    <ListItemText primary={team} />
                  </MenuItem>
                ))}
              </Select>
            </FormControl>
          </DialogContent>
          <DialogActions>
            <Button onClick={() => { setOpenAddDialog(false); disableBackgroundInteraction(false); }} color="secondary">
              Cancel
            </Button>
            <Button onClick={handleAddEmployee} color="primary">
              To add
            </Button>
          </DialogActions>
        </Dialog>
        <Dialog open={openConfirmDialog} onClose={handleCancelDelete}>
          <DialogTitle>Confirmar Remoção</DialogTitle>
          <DialogContent>
            <Typography>Você tem certeza que deseja remover este funcionário?</Typography>
          </DialogContent>
          <DialogActions>
            <Button onClick={handleCancelDelete} color="secondary">
              Cancel
            </Button>
            <Button onClick={handleConfirmDelete} color="primary">
              Confirm
            </Button>
          </DialogActions>
        </Dialog>
        <Dialog open={openEditDialog} onClose={() => { setOpenEditDialog(false); disableBackgroundInteraction(false); }}>
          <DialogTitle>Edit Employee</DialogTitle>
          <DialogContent>
            {selectedEmployee && (
              <>
                <TextField
                  margin="dense"
                  label="ID"
                  fullWidth
                  value={selectedEmployee.id}
                  disabled
                />
                <TextField
                  margin="dense"
                  label="Nome"
                  fullWidth
                  value={selectedEmployee.name}
                  onChange={(e) =>
                    setSelectedEmployee({ ...selectedEmployee, name: e.target.value })
                  }
                />
                <FormControl fullWidth margin="dense">
                  <InputLabel id="edit-team-label">Equipa</InputLabel>
                  <Select
                    labelId="edit-team-label"
                    multiple
                    value={
                      Array.isArray(selectedEmployee.team)
                        ? selectedEmployee.team
                        : selectedEmployee.team
                          ? [selectedEmployee.team.name]
                          : []
                    }
                    onChange={(e) =>
                      setSelectedEmployee({ ...selectedEmployee, team: e.target.value })
                    }
                    input={<OutlinedInput label="Equipa" />}
                    renderValue={(selected) => selected.join(" e ")}
                  >
                    {teamOptions.map((team) => (
                      <MenuItem key={team} value={team}>
                        <Checkbox
                          checked={
                            Array.isArray(selectedEmployee.team)
                              ? selectedEmployee.team.indexOf(team) > -1
                              : selectedEmployee.team && selectedEmployee.team.name === team
                          }
                        />
                        <ListItemText primary={team} />
                      </MenuItem>
                    ))}
                  </Select>
                </FormControl>
              </>
            )}
          </DialogContent>
          <DialogActions>
            <Button onClick={() => { setOpenEditDialog(false); disableBackgroundInteraction(false); }} color="secondary">
              Cancel
            </Button>
            <Button onClick={handleEditEmployee} color="primary">
              Save
            </Button>
          </DialogActions>
        </Dialog>
      </div>
    </div>
  );
};

export default Employer;
