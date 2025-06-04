import React, { useEffect, useState } from "react";
import axios from "axios";
import baseurl from "../components/BaseUrl";
import Sidebar_Manager from "../components/Sidebar_Manager";
import NotificationSnackbar from "../components/manager/NotificationSnackbar";
import { useNavigate } from "react-router-dom";
import {
  Typography,
  Grid,
  TextField,
  Button,
  Box,
  Paper,
  FormControl,
  InputLabel,
  Select,
  MenuItem,
} from "@mui/material";

const CreateCalendar = () => {
  const [title, setTitle] = useState("");
  const [year, setYear] = useState("");
  const [maxDuration, setMaxDuration] = useState("");
  const [selectedAlgorithm, setSelectedAlgorithm] = useState("");
  const [vacationTemplate, setVacationTemplate] = useState("");
  const [minimumTemplate, setMinimumTemplate] = useState("");
  const [templateOptions, setTemplateOptions] = useState([]);
  const [minimumOptions, setMinimumOptions] = useState([]);

  const [successOpen, setSuccessOpen] = useState(false);
  const [errorOpen, setErrorOpen] = useState(false);
  const [errorMessage, setErrorMessage] = useState("");

  const navigate = useNavigate();

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
      setTimeout(() => {
        navigate("/manager");
      }, 0);
    } catch (error) {
      console.error("Error sending data:", error);
      const rawMsg = error.response?.data?.message || error.response?.data;
      let displayMsg = rawMsg || "Failed to create calendar. Try again.";

      if (typeof displayMsg === "string" && displayMsg.includes("Caused by:")) {
        const [, cause] = displayMsg.split("Caused by:");
        displayMsg = cause?.trim() || displayMsg;
      }

      setErrorMessage(displayMsg);
      setErrorOpen(true);
    }
  };

  const handleClear = () => {
    setTitle("");
    setYear("");
    setMaxDuration("");
    setSelectedAlgorithm("");
    setVacationTemplate("");
    setMinimumTemplate("");
  };

  const [titleError, setTitleError] = useState(false);
  const [yearError, setYearError] = useState(false);
  const [maxDurationError, setMaxDurationError] = useState(false);

  const handleTitleChange = (e) => {
    const value = e.target.value;
    setTitle(value);
    setTitleError(value.trim() === "");
  };

  const handleYearChange = (e) => {
    const value = e.target.value;
    const intValue = parseInt(value, 10);
    setYear(value);
    setYearError(!intValue || intValue <= 0 || !/^\d+$/.test(value));
  };

  const handleMaxDurationChange = (e) => {
    const value = e.target.value;
    const intValue = parseInt(value, 10);
    setMaxDuration(value);
    setMaxDurationError(!intValue || intValue <= 0 || !/^\d+$/.test(value));
  };

  return (
    <div className="admin-container">
      <Sidebar_Manager />
      <div
        className="main-content"
        style={{
          flex: 1,
          overflowY: "auto",
          padding: "20px",
          boxSizing: "border-box",
          marginRight: "20px",
        }}
      >
        <div style={{ display: "flex", justifyContent: "left", marginBottom: "2%" }}>
          <h1>Generate Schedule</h1>
        </div>

        <Grid container spacing={10}>
          <Grid item xs={12} md={6}>
            <Paper style={{ padding: "20px" }}>
              <Typography variant="h6" gutterBottom>Schedule Information</Typography>
              <TextField
                fullWidth
                label="Title"
                value={title}
                onChange={handleTitleChange}
                margin="normal"
                error={titleError}
                helperText={titleError ? "Title is required" : ""}
              />
              <TextField
                fullWidth
                type="number"
                label="Year"
                value={year}
                onChange={handleYearChange}
                margin="normal"
                error={yearError}
                helperText={yearError ? "Year must be a positive integer" : ""}
              />
              <TextField
                fullWidth
                type="number"
                label="Max Duration (minutes)"
                value={maxDuration}
                onChange={handleMaxDurationChange}
                margin="normal"
                error={maxDurationError}
                helperText={maxDurationError ? "Duration must be a positive integer" : ""}
              />

              <FormControl fullWidth margin="normal">
                <InputLabel id="algorithm-select-label">Algorithm</InputLabel>
                <Select
                  labelId="algorithm-select-label"
                  value={selectedAlgorithm}
                  label="Algorithm"
                  onChange={(e) => setSelectedAlgorithm(e.target.value)}
                >
                  <MenuItem value="hill climbing">Hill Climbing</MenuItem>
                  <MenuItem value="linear programming">Integer Linear Programming</MenuItem>
                  <MenuItem value="Greedy Randomized">Greedy Randomized</MenuItem>
                  <MenuItem value="Greedy Randomized + Hill Climbing">Greedy Randomized + Hill Climbing</MenuItem>
                </Select>
              </FormControl>

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
        </Grid>

        <Box sx={{ display: "flex", justifyContent: "left", marginTop: 3, marginLeft: "17%", gap: 2 }}>
          <Button variant="contained" color="success" onClick={handleSave}>Generate</Button>
          <Button variant="contained" color="error" onClick={handleClear}>Clear All</Button>
        </Box>

        <NotificationSnackbar
          open={successOpen}
          severity="success"
          message="Task Requested Successfully!"
          onClose={() => setSuccessOpen(false)}
        />

        <NotificationSnackbar
          open={errorOpen}
          severity="error"
          message={errorMessage}
          onClose={() => setErrorOpen(false)}
        />
      </div>
    </div>
  );
};

export default CreateCalendar;
