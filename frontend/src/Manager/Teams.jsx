import React, { useEffect, useState } from "react";
import Sidebar_Manager from "../components/Sidebar_Manager";
import BaseUrl from "../components/BaseUrl";
import {
  Box,
  Button,
  CircularProgress,
  Dialog,
  DialogActions,
  DialogContent,
  DialogTitle,
  Paper,
  Typography,
  TextField,
  Grid,
  Divider,
  IconButton,
} from "@mui/material";
import { Close as CloseIcon } from "@mui/icons-material";

const Teams = () => {
  const [teams, setTeams] = useState([]);
  const [loading, setLoading] = useState(true);
  const [openDialog, setOpenDialog] = useState(false);
  const [newTeamName, setNewTeamName] = useState("");
  const [employeeIdsInput, setEmployeeIdsInput] = useState("");
  const [searchTerm, setSearchTerm] = useState("");
  const [editTeamId, setEditTeamId] = useState(null);

  const [openDetailsDialog, setOpenDetailsDialog] = useState(false);
  const [teamDetails, setTeamDetails] = useState(null);
  const [newEmployeeIds, setNewEmployeeIds] = useState("");

  useEffect(() => {
    fetchTeams();
  }, []);

  const fetchTeams = async () => {
    setLoading(true);
    try {
      const response = await fetch(`${BaseUrl}/api/v1/teams/`, {
        method: "GET",
        headers: {
          "Content-Type": "application/json",
          Accept: "application/json",
        },
      });
      const data = await response.json();
      if (response.ok) {
        setTeams(data);
      } else {
        console.error("Erro ao buscar equipes:", data);
      }
    } catch (error) {
      console.error("Erro ao buscar equipes:", error);
    } finally {
      setLoading(false);
    }
  };

  const handleAddOrUpdateTeam = async () => {
    const employeeIds = employeeIdsInput
      .split(",")
      .map((id) => id.trim())
      .filter((id) => id);

    const payload = {
      name: newTeamName,
      employeeIds: employeeIds,
    };

    try {
      let response;
      if (editTeamId) {
        response = await fetch(`${BaseUrl}/api/v1/teams/${editTeamId}`, {
          method: "PUT",
          headers: {
            "Content-Type": "application/json",
            Accept: "application/json",
          },
          body: JSON.stringify(payload),
        });
      } else {
        response = await fetch(`${BaseUrl}/api/v1/teams/`, {
          method: "POST",
          headers: {
            "Content-Type": "application/json",
            Accept: "application/json",
          },
          body: JSON.stringify(payload),
        });
      }

      if (response.ok) {
        handleCloseDialog();
        fetchTeams();
      } else {
        const errorData = await response.json();
        console.error("Erro ao adicionar ou atualizar equipe:", errorData);
      }
    } catch (error) {
      console.error("Erro ao adicionar ou atualizar equipe:", error);
    }
  };

  const handleEditTeam = (team) => {
    setNewTeamName(team.name);
    setEmployeeIdsInput(team.employeeIds.join(","));
    setEditTeamId(team.id);
    setOpenDialog(true);
  };

  const handleCloseDialog = () => {
    setOpenDialog(false);
    setNewTeamName("");
    setEmployeeIdsInput("");
    setEditTeamId(null);
  };

  const filteredTeams = teams.filter((team) =>
    team.id.toLowerCase().includes(searchTerm.toLowerCase())
  );

  const handleViewTeamDetails = async (teamId) => {
    try {
      const response = await fetch(`${BaseUrl}/api/v1/teams/${teamId}`, {
        method: "GET",
        headers: {
          "Content-Type": "application/json",
          Accept: "application/json",
        },
      });

      const teamData = await response.json();
      if (!response.ok) {
        console.error("Erro ao buscar detalhes da equipe:", teamData);
        return;
      }

      const employeeDetails = await Promise.all(
        teamData.employeeIds.map(async (id) => {
          try {
            const res = await fetch(`${BaseUrl}/api/v1/employees/${id}`, {
              method: "GET",
              headers: {
                "Content-Type": "application/json",
                Accept: "application/json",
              },
            });
            const data = await res.json();
            if (res.ok) {
              return { id: data.id, name: data.name, restrictions: data.restrictions };
            } else {
              return { id, name: "Erro ao carregar", restrictions: {} };
            }
          } catch (err) {
            return { id, name: "Erro na requisição", restrictions: {} };
          }
        })
      );

      setTeamDetails({
        ...teamData,
        employees: employeeDetails,
      });

      setOpenDetailsDialog(true);
    } catch (error) {
      console.error("Erro ao buscar detalhes da equipe:", error);
    }
  };

  const handleCloseDetailsDialog = () => {
    setOpenDetailsDialog(false);
    setTeamDetails(null);
    setNewEmployeeIds("");
  };

  const handleAddEmployeesToTeam = async () => {
    if (!newEmployeeIds) {
      console.error("Nenhum ID de empregado fornecido.");
      return;
    }

    const employeeIds = newEmployeeIds
      .split(",")
      .map((id) => id.trim())
      .filter((id) => id);

    try {
      const response = await fetch(
        `${BaseUrl}/api/v1/teams/${teamDetails.id}/add-employees`,
        {
          method: "POST",
          headers: {
            "Content-Type": "application/json",
            Accept: "application/json",
          },
          body: JSON.stringify({ employeeIds }),
        }
      );

      const data = await response.json();
      if (response.ok) {
        setTeamDetails((prevDetails) => ({
          ...prevDetails,
          employees: [
            ...prevDetails.employees,
            ...employeeIds.map((id) => ({
              id,
              name: "Carregando...",
              restrictions: {},
            })),
          ],
        }));
        setNewEmployeeIds("");
      } else {
        console.error("Erro ao adicionar empregados:", data);
      }
    } catch (error) {
      console.error("Erro ao adicionar empregados:", error);
    }
  };

  return (
    <div className="admin-container">
      <Sidebar_Manager />
      <div className="main-content" style={{ flex: 1, padding: "20px" }}>
        <Box sx={{ padding: 4, flexGrow: 1 }}>
          <Box display="flex" justifyContent="space-between" alignItems="center" mb={3}>
            <Typography variant="h4" gutterBottom>
              Lista de Equipes
            </Typography>
            <Box display="flex" gap={2} alignItems="center" sx={{ width: "35%" }}>
              <TextField
                label="Buscar por ID da Equipe"
                variant="outlined"
                value={searchTerm}
                onChange={(e) => setSearchTerm(e.target.value)}
                margin="normal"
                sx={{ flex: 1, borderRadius: "8px", backgroundColor: "#fff" }}
              />
              <Button
                variant="contained"
                color="primary"
                onClick={() => setOpenDialog(true)}
                sx={{ height: "100%", padding: "10px 20px", fontWeight: "bold", borderRadius: "8px" }}
              >
                + Nova Equipe
              </Button>
            </Box>
          </Box>

          {loading ? (
            <Box display="flex" justifyContent="center" mt={4}>
              <CircularProgress />
            </Box>
          ) : (
            <Grid container spacing={4}>
              {filteredTeams.length === 0 ? (
                <Typography variant="body1" color="textSecondary">
                  Nenhuma equipe encontrada.
                </Typography>
              ) : (
                filteredTeams.map((team) => (
                  <Grid item key={team.id} xs={12} sm={6} md={4} lg={3}>
                    <Paper sx={{ padding: 3, textAlign: "center", boxShadow: 3, borderRadius: 2 }}>
                      <Typography variant="h6" sx={{ fontWeight: "bold", mb: 2 }}>
                        {team.name}
                      </Typography>
                      <Typography variant="body2" color="textSecondary" sx={{ mb: 2 }}>
                        {team.description || "Sem descrição"}
                      </Typography>
                      <Button
                        variant="outlined"
                        color="primary"
                        onClick={() => handleViewTeamDetails(team.id)}
                        sx={{ marginTop: 1, width: "100%" }}
                      >
                        Ver Detalhes
                      </Button>
                      <Button
                        variant="contained"
                        color="secondary"
                        onClick={() => handleEditTeam(team)}
                        sx={{ marginTop: 1, width: "100%" }}
                      >
                        Editar
                      </Button>
                    </Paper>
                  </Grid>
                ))
              )}
            </Grid>
          )}
        </Box>
      </div>

      {/* Modal Nova/Editar Equipe */}
      <Dialog open={openDialog} onClose={handleCloseDialog}>
        <DialogTitle>{editTeamId ? "Editar Equipe" : "Nova Equipe"}</DialogTitle>
        <DialogContent>
          <TextField
            label="Nome da Equipe"
            fullWidth
            margin="normal"
            value={newTeamName}
            onChange={(e) => setNewTeamName(e.target.value)}
          />
          <TextField
            label="IDs dos Empregados (separados por vírgula)"
            fullWidth
            margin="normal"
            value={employeeIdsInput}
            onChange={(e) => setEmployeeIdsInput(e.target.value)}
          />
        </DialogContent>
        <DialogActions>
          <Button onClick={handleCloseDialog}>Cancelar</Button>
          <Button variant="contained" color="primary" onClick={handleAddOrUpdateTeam}>
            {editTeamId ? "Atualizar" : "Adicionar"}
          </Button>
        </DialogActions>
      </Dialog>

      {/* Modal Detalhes Equipe */}
      <Dialog open={openDetailsDialog} onClose={handleCloseDetailsDialog}>
        <DialogTitle>
          Detalhes da Equipe
          <IconButton
            edge="end"
            color="inherit"
            onClick={handleCloseDetailsDialog}
            sx={{ position: "absolute", right: 8, top: 8 }}
          >
            <CloseIcon />
          </IconButton>
        </DialogTitle>
        <DialogContent sx={{ width: 420 }}>
          {teamDetails ? (
            <Box>
              <Typography variant="h6" sx={{ fontWeight: "bold" }}>
                Nome: {teamDetails.name}
              </Typography>
              <Typography variant="body2" color="textSecondary" sx={{ marginTop: 1 }}>
                Descrição: {teamDetails.description || "Sem descrição"}
              </Typography>
              <Divider sx={{ marginTop: 2 }} />
              <Typography variant="subtitle1" sx={{ marginTop: 2, fontWeight: 'bold' }}>
                Empregados:
              </Typography>
              {teamDetails.employees.map((emp) => (
                <Box key={emp.id} sx={{ ml: 2, mt: 1 }}>
                  <Typography variant="body2">
                    • {emp.name} ({emp.id})
                  </Typography>
                  {Object.keys(emp.restrictions).length > 0 ? (
                    <Typography variant="caption" color="error">
                      Restrições: {JSON.stringify(emp.restrictions)}
                    </Typography>
                  ) : (
                    <Typography variant="caption" color="textSecondary">
                      Sem restrições
                    </Typography>
                  )}
                </Box>
              ))}
              <TextField
                label="Adicionar IDs dos Empregados"
                fullWidth
                margin="normal"
                value={newEmployeeIds}
                onChange={(e) => setNewEmployeeIds(e.target.value)}
                helperText="Digite os IDs separados por vírgula"
              />
              <Button
                variant="contained"
                color="primary"
                onClick={handleAddEmployeesToTeam}
                sx={{ marginTop: 2 }}
              >
                Adicionar Empregados
              </Button>
            </Box>
          ) : (
            <CircularProgress sx={{ display: "block", margin: "0 auto" }} />
          )}
        </DialogContent>
        <DialogActions>
          <Button onClick={handleCloseDetailsDialog} color="primary">
            Fechar
          </Button>
        </DialogActions>
      </Dialog>
    </div>
  );
};

export default Teams;
