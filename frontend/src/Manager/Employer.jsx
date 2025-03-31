import React, { useState, useEffect } from "react";
import axios from "axios";
import Sidebar_Manager from "../components/Sidebar_Manager";
import {
  Table, TableBody, TableCell, TableContainer, TableHead, TableRow,
  Typography, CircularProgress, Box, Button, Dialog, DialogTitle,
  DialogContent, DialogActions, TextField, FormControl, InputLabel,
  Select, MenuItem, OutlinedInput, Checkbox, ListItemText, IconButton
} from "@mui/material";
import DeleteIcon from '@mui/icons-material/Delete';

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
  const [removalMode, setRemovalMode] = useState(false); // Adicionando o estado de modo de remoção

  useEffect(() => { fetchEmployees(); }, []);

  const fetchEmployees = () => {
    setLoading(true);
    axios.get("http://localhost:8081/api/v1/employees/")
      .then((response) => { setEmployees(response.data); setLoading(false); })
      .catch(() => { setError("Erro ao buscar employees."); setLoading(false); });
  };

  const handleRemoveEmployee = (id) => {
    axios.delete(`http://localhost:8081/api/v1/employees/${id}`).then(fetchEmployees)
      .catch((error) => console.error("Erro ao remover employee:", error));
  };

  const handleOpenEditDialog = (employee) => {
    setSelectedEmployee(employee);
    setOpenEditDialog(true);
  };

  const handleEditEmployee = () => {
    axios.put(`http://localhost:8081/api/v1/employees/${selectedEmployee.id}`, selectedEmployee)
      .then(() => { setOpenEditDialog(false); setSelectedEmployee(null); fetchEmployees(); })
      .catch((error) => console.error("Erro ao editar employee:", error));
  };

  const handleAddEmployee = () => {
    axios.post("http://localhost:8081/api/v1/employees/", newEmployee)
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
    setRemovalMode(!removalMode); // Alterna entre o modo de remoção
  };

  return (
    <div className="admin-container" style={{ display: "flex", minHeight: "100vh" }}>
      <Sidebar_Manager />
      <div className="main-content" style={{ flex: 1, padding: "20px" }}>
        <Box mb={4} display="flex" justifyContent="space-between" alignItems="center">
          <Typography variant="h4">Lista de Employees</Typography>
          <Box>
            <Button variant="contained" color="success" onClick={() => setOpenAddDialog(true)}>
              Adicionar Employee
            </Button>
            <Button
              variant="contained"
              color="error"
              onClick={toggleRemovalMode} // Alterna para o modo de remoção
              style={{ marginLeft: "10px" }}
            >
              {removalMode ? "Cancelar Remoção" : "Remover Employees"}
            </Button>
          </Box>
        </Box>

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
        ) : employees.length > 0 ? (
          <>
            <TableContainer style={{ borderRadius: 8 }}>
              <Table>
                <TableHead style={{ backgroundColor: "#1976d2", color: "#fff" }}>
                  <TableRow>
                    <TableCell style={{ color: "#fff", fontWeight: "bold" }}>ID</TableCell>
                    <TableCell style={{ color: "#fff", fontWeight: "bold" }}>Nome</TableCell>
                    <TableCell style={{ color: "#fff", fontWeight: "bold" }}>Equipa</TableCell>
                    <TableCell style={{ color: "#fff", fontWeight: "bold" }}></TableCell>
                    <TableCell style={{ color: "#fff", fontWeight: "bold" }}></TableCell>
                  </TableRow>
                </TableHead>
                <TableBody>
                  {employees.map((emp, index) => {
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
                          {removalMode && ( // Exibe o ícone de lixeira se estiver no modo de remoção
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
                            Editar
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
                Adicionar Employee
              </Button>
            </Box>
          </Box>
        )}

        {/* Diálogo para Adicionar Employee */}
        <Dialog open={openAddDialog} onClose={() => setOpenAddDialog(false)}>
          <DialogTitle>Adicionar Employee</DialogTitle>
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
            <Button onClick={() => setOpenAddDialog(false)} color="secondary">
              Cancelar
            </Button>
            <Button onClick={handleAddEmployee} color="primary">
              Adicionar
            </Button>
          </DialogActions>
        </Dialog>

        {/* Diálogo para Confirmar Remoção */}
        <Dialog open={openConfirmDialog} onClose={handleCancelDelete}>
          <DialogTitle>Confirmar Remoção</DialogTitle>
          <DialogContent>
            <Typography>Você tem certeza que deseja remover este funcionário?</Typography>
          </DialogContent>
          <DialogActions>
            <Button onClick={handleCancelDelete} color="secondary">
              Cancelar
            </Button>
            <Button onClick={handleConfirmDelete} color="primary">
              Confirmar
            </Button>
          </DialogActions>
        </Dialog>

        {/* Diálogo para Editar Employee */}
        <Dialog open={openEditDialog} onClose={() => setOpenEditDialog(false)}>
          <DialogTitle>Editar Employee</DialogTitle>
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
            <Button onClick={() => setOpenEditDialog(false)} color="secondary">
              Cancelar
            </Button>
            <Button onClick={handleEditEmployee} color="primary">
              Salvar
            </Button>
          </DialogActions>
        </Dialog>
      </div>
    </div>
  );
};

export default Employer;
