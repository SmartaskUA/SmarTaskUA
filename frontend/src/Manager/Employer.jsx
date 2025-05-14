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
  const [teamsDict, setTeamsDict] = useState({});
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [openAddDialog, setOpenAddDialog] = useState(false);
  const [newEmployee, setNewEmployee] = useState({ id: "", name: "", teamIds: [] });
  const [openEditDialog, setOpenEditDialog] = useState(false);
  const [selectedEmployee, setSelectedEmployee] = useState(null);
  const [openConfirmDialog, setOpenConfirmDialog] = useState(false);
  const [employeeToDelete, setEmployeeToDelete] = useState(null);
  const [removalMode, setRemovalMode] = useState(false);
  const [filteredEmployees, setFilteredEmployees] = useState([]);

  useEffect(() => {
    fetchAll();
  }, []);

  const fetchAll = async () => {
    setLoading(true);
    try {
      const [empRes, teamsRes] = await Promise.all([
        axios.get(`${BaseUrl}/api/v1/employees/`),
        axios.get(`${BaseUrl}/api/v1/teams/`)
      ]);

      const teamMap = {};
      teamsRes.data.forEach(team => {
        teamMap[team.id] = team.name;
      });

      setTeamsDict(teamMap);
      setEmployees(empRes.data);
      setFilteredEmployees(empRes.data);
      setLoading(false);
    } catch (err) {
      console.error(err);
      setError("Erro ao buscar dados.");
      setLoading(false);
    }
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
    axios.delete(`${BaseUrl}/api/v1/employees/${id}`).then(fetchAll)
      .catch((error) => console.error("Erro ao remover employee:", error));
  };

  const handleOpenEditDialog = (employee) => {
    setSelectedEmployee(employee);
    setOpenEditDialog(true);
  };

  const handleEditEmployee = () => {
    axios.put(`${BaseUrl}/api/v1/employees/${selectedEmployee.id}`, {
      name: selectedEmployee.name,
      teamIds: selectedEmployee.teamIds,
    })
      .then(() => {
        setOpenEditDialog(false);
        setSelectedEmployee(null);
        fetchAll();
      })
      .catch((error) => console.error("Erro ao editar employee:", error));
  };

  const handleAddEmployee = () => {
    axios.post(`${BaseUrl}/api/v1/employees/`, newEmployee)
      .then(() => {
        setOpenAddDialog(false);
        setNewEmployee({ id: "", name: "", teamIds: [] });
        fetchAll();
      })
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

  const getTeamNames = (teamIds) => {
    if (!Array.isArray(teamIds) || teamIds.length === 0) return "N/A";
    return teamIds
      .map(id => (teamsDict[id] || id).replace(/^Equipa\s+/i, ''))
      .join(", ");
  };

  const handleResetEmployeesAndTeams = async () => {
    const confirmReset = window.confirm("Tem a certeza que deseja repor os employees e equipas para o estado inicial?");
    if (!confirmReset) return;

    try {
      await axios.post(`${BaseUrl}/cleanreset/reset-employees-teams`);
      await fetchAll();
    } catch (err) {
      console.error("Erro ao fazer reset dos employees e equipas:", err);
      alert("Erro ao fazer reset: " + (err.response?.data?.error || err.message));
    }
  };

  return (
    <div className="admin-container" style={{ display: "flex", minHeight: "100vh" }}>
      <Sidebar_Manager />
      <div className="main-content" style={{ flex: 1, padding: "20px" }}>
        <Box mb={4} display="flex" justifyContent="space-between" alignItems="center">
          <Typography variant="h4">List of Employees</Typography>
          <Box>
            <Button variant="contained" color="success" onClick={() => setOpenAddDialog(true)}>
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
            <Button
              variant="outlined"
              color="secondary"
              onClick={handleResetEmployeesAndTeams}
              style={{ marginLeft: "10px" }}
            >
              Reset Equipas e Employees
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
                    <TableCell style={{ color: "#fff", fontWeight: "bold" }}>Preferências</TableCell>
                    <TableCell style={{ color: "#fff", fontWeight: "bold" }}></TableCell>
                    <TableCell style={{ color: "#fff", fontWeight: "bold" }}></TableCell>
                  </TableRow>
                </TableHead>
                <TableBody>
                  {filteredEmployees.map((emp, index) => {
                    const rowStyle = index % 2 === 0
                      ? { backgroundColor: "#f2f2f2" }
                      : { backgroundColor: "#ffffff" };

                    return (
                      <TableRow key={emp.id} style={rowStyle}>
                        <TableCell>{emp.id}</TableCell>
                        <TableCell>{emp.name}</TableCell>
                        <TableCell>{getTeamNames(emp.teamIds)}</TableCell>
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
              <Button variant="contained" color="success" onClick={() => setOpenAddDialog(true)}>
                Add Employee
              </Button>
            </Box>
          </Box>
        )}

        <Dialog open={openAddDialog} onClose={() => setOpenAddDialog(false)}>
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
            {/* Aqui poderias usar um select de equipas futuras se necessário */}
          </DialogContent>
          <DialogActions>
            <Button onClick={() => setOpenAddDialog(false)} color="secondary">
              Cancel
            </Button>
            <Button onClick={handleAddEmployee} color="primary">
              Add
            </Button>
          </DialogActions>
        </Dialog>

        <Dialog open={openConfirmDialog} onClose={handleCancelDelete}>
          <DialogTitle>Confirmar Remoção</DialogTitle>
          <DialogContent>
            <Typography>Tem certeza que deseja remover este funcionário?</Typography>
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

        <Dialog open={openEditDialog} onClose={() => setOpenEditDialog(false)}>
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

                <FormControl fullWidth margin="normal">
                  <InputLabel id="team-select-label">Equipas</InputLabel>
                  <Select
                    labelId="team-select-label"
                    multiple
                    value={selectedEmployee.teamIds || []}
                    onChange={(e) => setSelectedEmployee({ ...selectedEmployee, teamIds: e.target.value })}
                    input={<OutlinedInput label="Equipas" />}
                    renderValue={(selected) =>
                      selected.map((id) => (teamsDict[id] || id).replace(/^Equipa\s+/i, "")).join(", ")
                    }
                  >
                    {Object.entries(teamsDict).map(([id, name]) => (
                      <MenuItem key={id} value={id}>
                        <Checkbox checked={selectedEmployee.teamIds?.includes(id)} />
                        <ListItemText primary={name.replace(/^Equipa\s+/i, "")} />
                      </MenuItem>
                    ))}
                  </Select>
                </FormControl>

                {selectedEmployee.teamIds?.length > 0 && (
                  <Box mt={2}>
                    <Typography variant="subtitle1" gutterBottom>
                      Ordem de Preferência
                    </Typography>
                    <Box display="flex" flexDirection="column" gap={1}>
                      {selectedEmployee.teamIds.map((id, index) => (
                        <Box key={id} display="flex" alignItems="center" gap={1}>
                          <Typography>{index + 1}.</Typography>
                          <Typography>{teamsDict[id].replace(/^Equipa\s+/i, "")}</Typography>
                          <Button
                            variant="outlined"
                            size="small"
                            disabled={index === 0}
                            onClick={() => {
                              const newOrder = [...selectedEmployee.teamIds];
                              [newOrder[index - 1], newOrder[index]] = [newOrder[index], newOrder[index - 1]];
                              setSelectedEmployee({ ...selectedEmployee, teamIds: newOrder });
                            }}
                          >
                            ↑
                          </Button>
                          <Button 
                            variant="outlined"
                            size="small"
                            disabled={index === selectedEmployee.teamIds.length - 1}
                            onClick={() => {
                              const newOrder = [...selectedEmployee.teamIds];
                              [newOrder[index], newOrder[index + 1]] = [newOrder[index + 1], newOrder[index]];
                              setSelectedEmployee({ ...selectedEmployee, teamIds: newOrder });
                            }}
                          >
                            ↓
                          </Button>
                        </Box>
                      ))}
                    </Box>
                  </Box>
                )}
              </>
            )}
          </DialogContent>
          <DialogActions>
            <Button onClick={() => setOpenEditDialog(false)} color="secondary">
              Cancel
            </Button>
            <Button
              onClick={async () => {
                try {
                  await axios.put(`${BaseUrl}/api/v1/employees/${selectedEmployee.id}`, {
                    name: selectedEmployee.name
                  });

                  const employeeId = selectedEmployee.id;
                  const newPrefs = selectedEmployee.teamIds;

                  for (const [teamId, name] of Object.entries(teamsDict)) {
                    await axios.delete(`${BaseUrl}/api/v1/teams/${name}/remove-employee/${employeeId}`);
                  }

                  for (let i = 0; i < newPrefs.length; i++) {
                    const reversedIndex = newPrefs.length - 1 - i;
                    const teamName = teamsDict[newPrefs[reversedIndex]];
                    await axios.post(`${BaseUrl}/api/v1/teams/${teamName}/add-employees`, {
                      employeeIds: [employeeId]
                    });
                    await axios.put(`${BaseUrl}/api/v1/teams/${employeeId}/set-team-preference-index/${teamName}/${i}`);
                  }

                  setOpenEditDialog(false);
                  setSelectedEmployee(null);
                  fetchAll();
                } catch (err) {
                  console.error("Erro ao guardar alterações:", err);
                }
              }}
              color="primary"
            >
              Save
            </Button>
          </DialogActions>
        </Dialog>
      </div>
    </div>
  );
};

export default Employer;
