import React, { useEffect, useState } from "react";
import axios from "axios";
import baseurl from "../components/BaseUrl";
import Sidebar_Manager from "../components/Sidebar_Manager";
import {
  Typography,
  Grid,
  TextField,
  Button,
  Box,
  ToggleButton,
  ToggleButtonGroup,
  Paper,
  Snackbar,
  Alert,
  MenuItem,
  Select,
  FormControl,
  InputLabel,
} from "@mui/material";

const CreateCalendar = () => {
  const [title, setTitle] = useState("");
  const [year, setYear] = useState("");
  const [maxDuration, setMaxDuration] = useState("");
  const [selectedAlgorithm, setSelectedAlgorithm] = useState("Algorithm1");
  const [vacationTemplate, setVacationTemplate] = useState("");
  const [minimumTemplate, setMinimumTemplate] = useState("");
  const [templateOptions, setTemplateOptions] = useState([]);
  const [minimumOptions, setMinimumOptions] = useState([]);

  const [successOpen, setSuccessOpen] = useState(false);
  const [errorOpen, setErrorOpen] = useState(false);

  useEffect(() => {
    fetchVacationTemplates();
    fetchMinimumTemplates();
  }, []);

  const fetchVacationTemplates = async () => {
    try {
      const response = await axios.get(`${baseurl}/vacation/`);
      setTemplateOptions(response.data);
    } catch (error) {
      console.error("Erro ao buscar templates de férias:", error);
    }
  };

  const fetchMinimumTemplates = async () => {
    try {
      const response = await axios.get(`${baseurl}/reference/`);
      setMinimumOptions(response.data);
    } catch (error) {
      console.error("Erro ao buscar templates de mínimos:", error);
    }
  };

  const handleAlgorithmChange = (event, newAlgorithm) => {
    if (newAlgorithm !== null) {
      setSelectedAlgorithm(newAlgorithm);
    }
  };

  const handleSave = async () => {
    try {
      const data = {
        year: year,
        algorithm: selectedAlgorithm,
        title: title,
        maxTime: maxDuration,
        requestedAt: new Date().toISOString(),
        vacationTemplate: vacationTemplate,
        minimuns: minimumTemplate,
      };

      const response = await axios.post(`${baseurl}/schedules/generate`, data);
      console.log("API Response:", response.data);
      setSuccessOpen(true);
    } catch (error) {
      console.error("Error sending data:", error);
      setErrorOpen(true);
    }
  };

  const handleClear = () => {
    setTitle("");
    setYear("");
    setMaxDuration("");
    setSelectedAlgorithm("Algorithm1");
    setVacationTemplate("");
    setMinimumTemplate("");
  };

  return (
    <div className="admin-container">
      <Sidebar_Manager />
      <div className="main-content" style={{ flex: 1, overflowY: "auto", padding: "20px", boxSizing: "border-box", marginRight: "20px" }}>
        <div style={{ display: "flex", justifyContent: "center", marginBottom: "2%" }}>
          <h1>Generate Schedule</h1>
        </div>

        <Grid container spacing={10}>
          <Grid item xs={12} md={6}>
            <Paper style={{ padding: "20px" }}>
              <Typography variant="h6" gutterBottom>Schedule Information</Typography>
              <TextField fullWidth label="Title" value={title} onChange={(e) => setTitle(e.target.value)} margin="normal" />
              <TextField fullWidth type="number" label="Year" value={year} onChange={(e) => setYear(e.target.value)} margin="normal" />
              <TextField fullWidth type="number" label="Max Duration (minutes)" value={maxDuration} onChange={(e) => setMaxDuration(e.target.value)} margin="normal" />

              <FormControl fullWidth margin="normal">
                <InputLabel id="vacation-template-label">Vacation Template</InputLabel>
                <Select
                  labelId="vacation-template-label"
                  value={vacationTemplate}
                  label="Vacation Template"
                  onChange={(e) => setVacationTemplate(e.target.value)}
                >
                  {templateOptions.map((option) => (
                    <MenuItem key={option.id} value={option.name}>{option.name}</MenuItem>
                  ))}
                </Select>
              </FormControl>

              <FormControl fullWidth margin="normal">
                <InputLabel id="minimum-template-label">Minimum Template</InputLabel>
                <Select
                  labelId="minimum-template-label"
                  value={minimumTemplate}
                  label="Minimum Template"
                  onChange={(e) => setMinimumTemplate(e.target.value)}
                >
                  {minimumOptions.map((option) => (
                    <MenuItem key={option.id} value={option.name}>{option.name}</MenuItem>
                  ))}
                </Select>
              </FormControl>
            </Paper>
          </Grid>

          <Grid item xs={12} md={6}>
            <Paper style={{ padding: "20px" }}>
              <Typography variant="h6" gutterBottom>Choose the Algorithm</Typography>
              <Box display="flex" justifyContent="center">
                <ToggleButtonGroup color="primary" value={selectedAlgorithm} exclusive onChange={handleAlgorithmChange}>
                  <ToggleButton value="CSP Scheduling">CSP</ToggleButton>
                  <ToggleButton value="hill climbing">Hill Climbing</ToggleButton>
                  <ToggleButton value="genetic_algorithm">Genetic</ToggleButton>
                  <ToggleButton value="linear programming">Linear Programming</ToggleButton>
                </ToggleButtonGroup>
              </Box>
            </Paper>
          </Grid>
        </Grid>

        <Box sx={{ display: "flex", justifyContent: "center", marginTop: 3, gap: 2 }}>
          <Button variant="contained" color="primary" onClick={handleSave}>Generate</Button>
          <Button variant="contained" color="secondary" onClick={handleClear}>Clear All</Button>
        </Box>

        <Snackbar open={successOpen} autoHideDuration={3000} onClose={() => setSuccessOpen(false)} anchorOrigin={{ vertical: "top", horizontal: "center" }}>
          <Alert onClose={() => setSuccessOpen(false)} severity="success" sx={{ width: "100%" }}>Task Requested Successfully!</Alert>
        </Snackbar>

        <Snackbar open={errorOpen} autoHideDuration={3000} onClose={() => setErrorOpen(false)} anchorOrigin={{ vertical: "top", horizontal: "center" }}>
          <Alert onClose={() => setErrorOpen(false)} severity="error" sx={{ width: "100%" }}>Failed to create calendar. Try again.</Alert>
        </Snackbar>
      </div>
    </div>
  );
};

export default CreateCalendar;
