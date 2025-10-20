import React, { useEffect, useState, useMemo } from "react";
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
  const [shifts, setShifts] = useState("");
  const [vacationTemplate, setVacationTemplate] = useState("");
  const [minimumTemplate, setMinimumTemplate] = useState("");

  // NEW: ruleset selection
  const [ruleSets, setRuleSets] = useState([]); // [{name, description, ...}]
  const [ruleSetName, setRuleSetName] = useState("");
  const selectedRuleSet = useMemo(
    () => ruleSets.find((r) => r.name === ruleSetName),
    [ruleSets, ruleSetName]
  );

  const [templateOptions, setTemplateOptions] = useState([]);
  const [minimumOptions, setMinimumOptions] = useState([]);

  const [successOpen, setSuccessOpen] = useState(false);
  const [errorOpen, setErrorOpen] = useState(false);
  const [errorMessage, setErrorMessage] = useState("");

  const navigate = useNavigate();

  useEffect(() => {
    fetchVacationTemplates();
    fetchMinimumTemplates();
    fetchRuleSets();
  }, []);

  const fetchVacationTemplates = async () => {
    try {
      const response = await axios.get(`${baseurl}/vacation/`);
      setTemplateOptions(response.data || []);
    } catch (error) {
      console.error("Erro ao buscar templates de férias:", error);
    }
  };

  const fetchMinimumTemplates = async () => {
    try {
      const response = await axios.get(`${baseurl}/reference/`);
      setMinimumOptions(response.data || []);
    } catch (error) {
      console.error("Erro ao buscar templates de mínimos:", error);
    }
  };

  const fetchRuleSets = async () => {
    try {
      const response = await axios.get(`${baseurl}/rulesets`);
      const list = Array.isArray(response.data) ? response.data : [];
      setRuleSets(list);
    } catch (error) {
      console.error("Erro ao buscar rulesets:", error);
      setRuleSets([]);
    }
  };

  const handleSave = async () => {

    try {
      console.log("Minimum Template:", minimumTemplate);
      const data = {
        year: year,
        algorithm: selectedAlgorithm,
        title: title.trim(),
        maxTime: maxDuration,
        requestedAt: new Date().toISOString(),
        vacationTemplate: vacationTemplate,
        minimuns: minimumTemplate,
        shifts: shifts,
        ruleSetName: ruleSetName, 
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
    setRuleSetName("");
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

  // disable Generate if core required fields invalid
  const canGenerate = useMemo(() => {
    const y = parseInt(year, 10);
    const d = parseInt(maxDuration, 10);
    return (
      title.trim() &&
      y > 0 &&
      /^\d+$/.test(String(year)) &&
      d > 0 &&
      /^\d+$/.test(String(maxDuration)) &&
      !!ruleSetName
    );
  }, [title, year, maxDuration, ruleSetName]);

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
                  <MenuItem value="linear programming 2">Integer Linear Programming 2</MenuItem>
                  <MenuItem value="ILP Engine">ILP Engine</MenuItem>
                  <MenuItem value="Greedy Randomized">Greedy Randomized</MenuItem>
                  <MenuItem value="Greedy Randomized Engine">Greedy Randomized Engine</MenuItem>
                  <MenuItem value="Greedy Randomized + Hill Climbing">Greedy Randomized + Hill Climbing</MenuItem>
                  <MenuItem value="CSP">CSP</MenuItem>
                  <MenuItem value="CSP_ENGINE">CSP Engine</MenuItem>
                  <MenuItem value="GRHC_ENGINE">Greedy Randomized + Hill Climbing Engine</MenuItem>
                </Select>
              </FormControl>

              {/* NEW: Rule Set Select */}
              <FormControl fullWidth margin="normal">
                <InputLabel id="ruleset-select-label">Rule Set</InputLabel>
                <Select
                  labelId="ruleset-select-label"
                  value={ruleSetName}
                  label="Rule Set"
                  onChange={(e) => {
                    setRuleSetName(e.target.value);
                  }}
                >
                  {ruleSets.map((rs) => (
                    <MenuItem key={rs.name} value={rs.name}>
                      {rs.name}
                    </MenuItem>
                  ))}
                </Select>
              </FormControl>

              <FormControl fullWidth margin="normal">
                <InputLabel id="shifts-select-label">Shifts</InputLabel>
                <Select
                  labelId="shifts-select-label"
                  value={shifts}
                  label="Shifts"
                  onChange={(e) => setShifts(e.target.value)}
                >
                  <MenuItem value={2}>2 shifts</MenuItem>
                  <MenuItem value={3}>3 shifts</MenuItem>
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
                    <MenuItem key={option.id ?? option.name} value={option.name}>
                      {option.name}
                    </MenuItem>
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
                    <MenuItem key={option.id ?? option.name} value={option.name}>
                      {option.name}
                    </MenuItem>
                  ))}
                </Select>
              </FormControl>
            </Paper>
          </Grid>
        </Grid>

        <Box sx={{ display: "flex", justifyContent: "left", marginTop: 3, marginLeft: "17%", gap: 2 }}>
          <Button variant="contained" color="success" onClick={handleSave} disabled={!canGenerate}>
            Generate
          </Button>
          <Button variant="contained" color="error" onClick={handleClear}>
            Clear All
          </Button>
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
