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
  FormControl,
  InputLabel,
  MenuItem,
  Select,
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

  const [openConfirmDialog, setOpenConfirmDialog] = useState(false);
  const [teamToDelete, setTeamToDelete] = useState(null);


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
        console.error("Error fetching teams:", data);
      }
    } catch (error) {
      console.error("Error fetching teams:", error);
    } finally {
      setLoading(false);
    }
  };

  const handleQuickAddTeam = async () => {
    if (!newTeamName || typeof newTeamName !== "string" || newTeamName.trim() === "") {
      console.error("Team name is required for quick add.");
      return;
    }

    try {
      const response = await fetch(`${BaseUrl}/api/v1/teams/${newTeamName.trim()}`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          Accept: "application/json",
        },
      });

      if (response.ok) {
        handleCloseDialog();
        fetchTeams();
      } else {
        const errorData = await response.json();
        console.error("Error in quick add:", errorData);
      }
    } catch (error) {
      console.error("Error in quick add:", error);
    }
  };

  const handleDeleteTeam = async () => {
    try {
      const team = teams.find((t) => t.id === teamToDelete);
      if (!team) {
        console.error("Team not found");
        return;
      }
  
      const response = await fetch(`${BaseUrl}/api/v1/teams/${encodeURIComponent(team.name)}`, {
        method: "DELETE",
        headers: {
          "Content-Type": "application/json",
          Accept: "application/json",
        },
      });
  
      if (response.ok) {
        fetchTeams();
        setOpenConfirmDialog(false);
        setEditTeamId(null);
      } else {
        const errorData = await response.json();
        console.error("Error deleting team:", errorData);
      }
    } catch (error) {
      console.error("Error deleting team:", error);
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
        console.error("Error fetching team details:", teamData);
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
              return { id, name: "Error loading", restrictions: {} };
            }
          } catch (err) {
            return { id, name: "Request error", restrictions: {} };
          }
        })
      );

      setTeamDetails({
        ...teamData,
        employees: employeeDetails,
      });

      setOpenDetailsDialog(true);
    } catch (error) {
      console.error("Error fetching team details:", error);
    }
  };

  const handleCloseDetailsDialog = () => {
    setOpenDetailsDialog(false);
    setTeamDetails(null);
    setNewEmployeeIds("");
  };

  const handleAddEmployeesToTeam = async () => {
    if (!newEmployeeIds) {
      console.error("No employee IDs provided.");
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
              name: "Loading...",
              restrictions: {},
            })),
          ],
        }));
        setNewEmployeeIds("");
      } else {
        console.error("Error adding employees:", data);
      }
    } catch (error) {
      console.error("Error adding employees:", error);
    }
  };

  const handleUpdateTeam = async () => {
    if (!newTeamName || newTeamName.trim() === "") {
      console.error("Team name is required to update.");
      return;
    }

    const employeeIds = employeeIdsInput
      .split(",")
      .map((id) => id.trim())
      .filter((id) => id);

    try {
      const response = await fetch(`${BaseUrl}/api/v1/teams/${editTeamId}`, {
        method: "PUT", 
        headers: {
          "Content-Type": "application/json",
          Accept: "application/json",
        },
        body: JSON.stringify({
          name: newTeamName.trim(),
          employeeIds,
        }),
      });

      if (response.ok) {
        handleCloseDialog();
        fetchTeams();
      } else {
        const errorData = await response.json();
        console.error("Error updating team:", errorData);
      }
    } catch (error) {
      console.error("Error updating team:", error);
    }
  };


  return (
    <div className="admin-container">
      <Sidebar_Manager />
      <div className="main-content" style={{ flex: 1, padding: "20px", marginRight: 52 }}>
        <Box sx={{ padding: 4, flexGrow: 1 }}>
          <Box display="flex" justifyContent="space-between" alignItems="center" mb={3}>
            <Typography variant="h4" gutterBottom>
              Team List
            </Typography>
            <Button sx={{ marginLeft: "30%" }} variant="contained" color="success" onClick={() => setOpenDialog(true)}>
              + New Team
            </Button>
            <Box display="flex" gap={2} alignItems="center" sx={{ width: "50%" }}>
              <TextField
                label="Search by Team ID"
                variant="outlined"
                value={searchTerm}
                onChange={(e) => setSearchTerm(e.target.value)}
                margin="normal"
                sx={{ flex: 1 }}
              />
              <FormControl sx={{ minWidth: 150 }}>
                <InputLabel id="select-team-label">Select Team pra eliminar</InputLabel>
                <Select
                  labelId="select-team-label"
                  value={editTeamId || ""}
                  label="Select Team"
                  onChange={(e) => setEditTeamId(e.target.value)}
                >
                  {teams.map((team) => (
                    <MenuItem key={team.id} value={team.id}>
                      {team.name}
                    </MenuItem>
                  ))}
                </Select>
              </FormControl>

              {editTeamId && (
                <Button
                  variant="outlined"
                  color="error"
                  onClick={() => {
                    setTeamToDelete(editTeamId);
                    setOpenConfirmDialog(true);
                  }}
                >
                  Delete
                </Button>
              )}
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
                  No teams found.
                </Typography>
              ) : (
                filteredTeams.map((team) => (
                  <Grid item key={team.id} xs={12} sm={6} md={4} lg={3}>
                    <Paper sx={{ padding: 3, textAlign: "center", boxShadow: 3, borderRadius: 2 }}>
                      <Typography variant="h6" sx={{ fontWeight: "bold", mb: 2 }}>
                        {team.name}
                      </Typography>

                      <Typography variant="body2" sx={{ fontWeight: "bold" }}>
                        {team.employeeIds?.length || 0} employee(s)
                      </Typography>
                      <Button
                        variant="outlined"
                        color="primary"
                        onClick={() => handleViewTeamDetails(team.id)}
                        sx={{ marginTop: 1, width: "100%" }}
                      >
                        View Details
                      </Button>
                      <Button
                        variant="contained"
                        color="primary"
                        onClick={() => handleEditTeam(team)}
                        sx={{ marginTop: 1, width: "100%" }}
                      >
                        Edit
                      </Button>
                    </Paper>
                  </Grid>
                ))
              )}
            </Grid>
          )}
        </Box>
      </div>

      <Dialog open={openDialog} onClose={handleCloseDialog}>
        <DialogTitle>{editTeamId ? "Edit Team" : "New Team"}</DialogTitle>
        <DialogContent>
          <TextField
            label="Team Name"
            fullWidth
            margin="normal"
            value={newTeamName}
            onChange={(e) => setNewTeamName(e.target.value)}
          />
          <TextField
            label="Employee IDs (comma separated)"
            fullWidth
            margin="normal"
            value={employeeIdsInput}
            onChange={(e) => setEmployeeIdsInput(e.target.value)}
          />
        </DialogContent>
        <DialogActions>
          <Button onClick={handleCloseDialog}>Cancel</Button>
          {editTeamId ? (
            <Button variant="contained" color="primary" onClick={handleUpdateTeam}>
              Update
            </Button>
          ) : (
            <Button variant="contained" color="success" onClick={handleQuickAddTeam}>
              Add
            </Button>
          )}
        </DialogActions>
      </Dialog>

      <Dialog open={openDetailsDialog} onClose={handleCloseDetailsDialog}>
        <DialogTitle>
          Team Details
          <IconButton
            edge="end"
            color="inherit"
            onClick={handleCloseDetailsDialog}
            sx={{ position: "absolute", right: 8, top: 8 }}
          >
            <CloseIcon />
          </IconButton>
        </DialogTitle>
        <DialogContent dividers sx={{ padding: 4, bgcolor: "#fafafa" }}>
          {teamDetails ? (
            <>
              <Typography variant="h5" gutterBottom sx={{ fontWeight: "700", color: "#1976d2", mb: 3 }}>
                {teamDetails.name}
              </Typography>
              <Divider sx={{ mb: 3 }} />
              <Typography variant="subtitle1" sx={{ fontWeight: "600", mb: 2 }}>
                Employees ({teamDetails.employees.length})
              </Typography>

              {teamDetails.employees.map((emp) => (
                <Paper
                  key={emp.id}
                  elevation={3}
                  sx={{
                    p: 2,
                    mb: 2,
                    borderRadius: 3,
                    transition: "transform 0.15s ease-in-out",
                    "&:hover": {
                      boxShadow: "0 4px 20px rgba(25, 118, 210, 0.3)",
                      transform: "translateY(-3px)",
                    },
                  }}
                >
                  <Typography variant="body1" sx={{ fontWeight: "600" }}>
                    {emp.name}{" "}
                    <Typography component="span" color="text.secondary" sx={{ fontWeight: "400" }}>
                      ({emp.id})
                    </Typography>
                  </Typography>

                  {emp?.restrictions &&
                    typeof emp.restrictions === "object" &&
                    Object.entries(emp.restrictions).length > 0 && (
                      <Box sx={{ mt: 1, display: "flex", flexWrap: "wrap", gap: 1 }}>
                        {Object.entries(emp.restrictions).map(([key, value]) => (
                          <Box
                            key={key}
                            sx={{
                              backgroundColor: "#e3f2fd",
                              borderRadius: "16px",
                              px: 2,
                              py: 0.5,
                              fontSize: "0.85rem",
                              color: "#0d47a1",
                              fontWeight: "500",
                              boxShadow: "0 1px 3px rgba(13, 71, 161, 0.2)",
                              userSelect: "none",
                              "&:hover": {
                                backgroundColor: "#bbdefb",
                              },
                            }}
                          >
                            {key}: {value}
                          </Box>
                        ))}
                      </Box>
                    )}
                </Paper>
              ))}

              <TextField
                label="Add Employee IDs"
                fullWidth
                margin="normal"
                value={newEmployeeIds}
                onChange={(e) => setNewEmployeeIds(e.target.value)}
                helperText="Enter IDs separated by commas"
                sx={{ mt: 2 }}
              />
              <Button
                variant="contained"
                color="success"
                onClick={handleAddEmployeesToTeam}
                sx={{ mt: 2 }}
                fullWidth
              >
                Add Employees
              </Button>
            </>
          ) : (
            <Box sx={{ display: "flex", justifyContent: "center", py: 8 }}>
              <CircularProgress size={48} />
            </Box>
          )}
        </DialogContent>
        <DialogActions sx={{ px: 3, pb: 2 }}>
          <Button onClick={handleCloseDetailsDialog} color="error" sx={{ fontWeight: "700" }} autoFocus>
            Close
          </Button>
        </DialogActions>
      </Dialog>

      <Dialog open={openConfirmDialog} onClose={() => setOpenConfirmDialog(false)}>
        <DialogTitle>Confirm Deletion</DialogTitle>
        <DialogContent>
          <Typography>Are you sure you want to delete this team?</Typography>
        </DialogContent>
        <DialogActions>
          <Button onClick={() => setOpenConfirmDialog(false)}>Cancel</Button>
          <Button variant="contained" color="error" onClick={handleDeleteTeam}>
            Confirm
          </Button>
        </DialogActions>
      </Dialog>
    </div>
  );

}
export default Teams;
