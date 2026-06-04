import React, { useEffect, useState, useMemo } from "react";
import axios from "axios";
import baseurl from "../components/BaseUrl";
import Sidebar_Manager from "../components/Sidebar_Manager";
import NotificationSnackbar from "../components/manager/NotificationSnackbar";
import { useNavigate, useSearchParams } from "react-router-dom";
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
  const [searchParams] = useSearchParams();
  const initialProblemId = searchParams.get("problemId") || "";
  const initialMode = initialProblemId ? "problem" : "manual";
  const [mode, setMode] = useState(initialMode);
  const [title, setTitle] = useState("");
  const [groupNames, setGroupNames] = useState([]); 
  const [selectedGroup, setSelectedGroup] = useState("");
  const [problems, setProblems] = useState([]);
  const [selectedProblemId, setSelectedProblemId] = useState(initialProblemId);
  const selectedProblem = useMemo(
    () => problems.find((p) => p.problemId === selectedProblemId),
    [problems, selectedProblemId]
  );
  const problemSelected = mode === "problem" && Boolean(selectedProblem);
  const [problemJson, setProblemJson] = useState(null);
  const [problemJsonLoading, setProblemJsonLoading] = useState(false);
  const [year, setYear] = useState("2021");
  const [maxDuration, setMaxDuration] = useState("100");
  const [scheduleType, setScheduleType] = useState("Horas"); // "Turno" ou "Horas"
  const [selectedAlgorithm, setSelectedAlgorithm] = useState("Heuristica");
  const [shifts, setShifts] = useState("13");
  const [vacationTemplate, setVacationTemplate] = useState("VacationTemplate_Case1_21");
  const [minimumTemplate, setMinimumTemplate] = useState("Mins_R10-R62_30min.");
  const [selectedSolver, setSelectedSolver] = useState("CBC"); // "CBC" ou "GUROBI"

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
    fetchGroupNames();
    fetchProblems();
  }, []);

  useEffect(() => {
    if (mode === "problem" && !selectedProblemId && problems.length) {
      setSelectedProblemId(problems[0].problemId);
    }
  }, [mode, selectedProblemId, problems]);

  const fetchGroupNames = async () => {
  try {
    const response = await axios.get(`${baseurl}/api/v1/teams/groups`); 
    setGroupNames(response.data || []);
  } catch (error) {
    console.error("Erro ao buscar grupos de equipes:", error);
    setGroupNames([]);
  }
};


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

  const fetchProblems = async () => {
    try {
      const response = await axios.get(`${baseurl}/problems`);
      const list = Array.isArray(response.data) ? response.data : [];
      setProblems(list);
    } catch (error) {
      console.error("Erro ao buscar problemas:", error);
      setProblems([]);
    }
  };

  const fetchProblemJson = async (problemId) => {
    if (!problemId) return;
    try {
      setProblemJsonLoading(true);
      const response = await axios.get(`${baseurl}/problems/${encodeURIComponent(problemId)}/json`);
      setProblemJson(response.data);
    } catch (error) {
      console.error("Erro ao buscar problem.json:", error);
      setProblemJson(null);
    } finally {
      setProblemJsonLoading(false);
    }
  };

  useEffect(() => {
    if (mode === "problem" && selectedProblemId) {
      fetchProblemJson(selectedProblemId);
      return;
    }
    setProblemJson(null);
  }, [mode, selectedProblemId]);

  useEffect(() => {
    if (mode !== "problem") {
      return;
    }
    if (!problemJson) {
      setScheduleType("");
      setShifts("");
      setYear("");
      return;
    }
    const temporal = problemJson.temporalScope || {};
    const demand = problemJson.demand || {};
    const shiftCount = Array.isArray(demand.shifts) && demand.shifts.length ? demand.shifts.length : null;
    const hasWorkPeriods = Array.isArray(demand.workPeriods) && demand.workPeriods.length > 0;

    if (shiftCount != null) {
      setScheduleType("Turno");
      setShifts(shiftCount);
    } else if (hasWorkPeriods) {
      setScheduleType("Horas");
      setShifts("");
    } else {
      setScheduleType("");
      setShifts("");
    }
    setSelectedAlgorithm("");
    setYear(temporal.year != null ? String(temporal.year) : "");
  }, [mode, problemJson]);

  const handleSave = async () => {
    const shiftsValue = scheduleType === "Turno" ? parseInt(shifts, 10) : null;
    const hoursValue = scheduleType === "Horas" ? parseInt(shifts, 10) : null;
    const safeShifts = Number.isNaN(shiftsValue) ? null : shiftsValue;
    const safeHours = Number.isNaN(hoursValue) ? null : hoursValue;

    try {
      console.log("Minimum Template:", minimumTemplate);
      if (mode === "problem") {
        if (!selectedProblem) {
          setErrorMessage("Please select a problem to solve.");
          setErrorOpen(true);
          return;
        }
        const data = {
          algorithm: selectedAlgorithm,
          title: title.trim(),
          maxTime: maxDuration,
          year: year,
          shifts: safeShifts,
          hours: safeHours,
        };

        const response = await axios.post(
          `${baseurl}/problems/${encodeURIComponent(selectedProblem.problemId)}/solve`,
          data
        );
        console.log("API Response:", response.data);
      } else {
        const data = {
          year: year,
          algorithm: selectedAlgorithm,
          title: title.trim(),
          maxTime: maxDuration,
          requestedAt: new Date().toISOString(),
          vacationTemplate: vacationTemplate,
          minimuns: minimumTemplate,
          shifts: safeShifts,
          hours: safeHours,
          groupName: selectedGroup,
          solver: scheduleType === "Horas" ? selectedSolver : null,
        };

        const response = await axios.post(`${baseurl}/schedules/generate`, data);
        console.log("API Response:", response.data);
      }

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
    setScheduleType("");
    setShifts("");
    setVacationTemplate("");
    setMinimumTemplate("");
    setSelectedGroup("");
    setSelectedProblemId("");
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

  const problemShiftAlgorithms = [
    { value: "ILP General", label: "ILP General" },
    { value: "CSP General", label: "CSP General" },
    { value: "Genetic Algorithm", label: "Genetic Algorithm" },
  ];
  const problemHourAlgorithms = [
    { value: "ILP_Sisqual_Hours", label: "ILP Sisqual Hours" },
    { value: "CSP_Sisqual_Hours", label: "CSP Sisqual Hours" },
  ];

  const manualShiftAlgorithms = [
    { value: "hill climbing", label: "Hill Climbing" },
    { value: "Greedy Randomized", label: "Greedy Randomized" },
    { value: "Greedy Randomized + Hill Climbing", label: "Greedy Randomized + Hill Climbing" },
    { value: "CSP Scheduling", label: "CSP Scheduling" },
    { value: "linear programming", label: "Integer Linear Programming" },
    { value: "linear programming 2", label: "Integer Linear Programming 2" },
  ];
  const manualHourAlgorithms = [
    { value: "CSP_Afonso_Hours", label: "CSP Afonso 13 Hours" },
    { value: "ILP_2", label: "Integer Linear Programming 2" },
    { value: "ILP_2_Half_Intervals", label: "Integer Linear Programming 2 Half Intervals" },
    { value: "ILP_3", label: "Integer Linear Programming 3" },
    { value: "ILP_3_Half_Intervals", label: "Integer Linear Programming 3 Half Intervals" },
    { value: "ILP_4", label: "Integer Linear Programming 4" },
    { value: "ILP_4_Half_Intervals", label: "Integer Linear Programming 4 Half Intervals" },
    { value: "COP_1", label: "Constraint Optimization Problem 1" },
    { value: "COP_1_Half_Intervals", label: "Constraint Optimization Problem 1 Half Intervals" },
    { value: "COP_2", label: "Constraint Optimization Problem 2" },
    { value: "COP_2_Half_Intervals", label: "Constraint Optimization Problem 2 Half Intervals" },
    { value: "Heuristica_1", label: "Heurística 1" },
    { value: "Heuristica_Half_Intervals", label: "Heurística Half Intervals" },
  ];

  const availableAlgorithms = useMemo(() => {
    if (mode === "problem") {
      if (!problemJson) {
        return [];
      }
      const demand = problemJson.demand || {};
      if (Array.isArray(demand.shifts) && demand.shifts.length > 0) {
        return problemShiftAlgorithms;
      }
      if (Array.isArray(demand.workPeriods) && demand.workPeriods.length > 0) {
        return problemHourAlgorithms;
      }
      return [];
    }
    if (scheduleType === "Turno") {
      return manualShiftAlgorithms;
    }
    if (scheduleType === "Horas") {
      return manualHourAlgorithms;
    }
    return [];
  }, [mode, problemJson, scheduleType]);

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
                disabled={mode === "problem"}
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
                inputProps={{ min: 1, max: 1000 }}
                error={maxDurationError}
                helperText={maxDurationError ? "Duration must be a positive integer (até 1000)" : ""}
              />

              <FormControl fullWidth margin="normal">
                <InputLabel id="mode-select-label">Mode</InputLabel>
                <Select
                  labelId="mode-select-label"
                  value={mode}
                  label="Mode"
                  onChange={(e) => {
                    const nextMode = e.target.value;
                    setMode(nextMode);
                    if (nextMode === "manual") {
                      setSelectedProblemId("");
                    }
                  }}
                >
                  <MenuItem value="problem">Problem</MenuItem>
                  <MenuItem value="manual">Manual</MenuItem>
                </Select>
              </FormControl>

              {mode === "problem" && (
                <FormControl fullWidth margin="normal">
                  <InputLabel id="problem-select-label">Problem</InputLabel>
                  <Select
                    labelId="problem-select-label"
                    value={selectedProblemId}
                    label="Problem"
                    onChange={(e) => setSelectedProblemId(e.target.value)}
                  >
                    <MenuItem value="">
                      <em>None</em>
                    </MenuItem>
                    {problems.map((problem) => (
                      <MenuItem key={problem.problemId} value={problem.problemId}>
                        {problem.name ? `${problem.name} (${problem.problemId})` : problem.problemId}
                      </MenuItem>
                    ))}
                  </Select>
                </FormControl>
              )}
              {problemSelected && (
                <Typography variant="caption" color="text.secondary">
                  {problemJsonLoading
                    ? "Loading problem details..."
                    : "Problem mode uses the bundled input files and defaults."}
                </Typography>
              )}

              {/* Novo input para tipo de horário */}
              {mode === "manual" && (
                <FormControl fullWidth margin="normal">
                  <InputLabel id="schedule-type-label">Tipo de Horário</InputLabel>
                  <Select
                    labelId="schedule-type-label"
                    value={scheduleType}
                    label="Tipo de Horário"
                    onChange={(e) => {
                      setScheduleType(e.target.value);
                      setShifts("");
                      setSelectedAlgorithm("");
                    }}
                  >
                    <MenuItem value="Turno">Turnos</MenuItem>
                    <MenuItem value="Horas">Horas</MenuItem>
                  </Select>
                </FormControl>
              )}

              {mode === "manual" && (
                <FormControl fullWidth margin="normal">
                  <InputLabel id="group-select-label">Group</InputLabel>
                  <Select
                    labelId="group-select-label"
                    value={selectedGroup}
                    label="Group"
                    onChange={(e) => setSelectedGroup(e.target.value)}
                  >
                    {groupNames.map((g) => (
                      <MenuItem key={g} value={g}>
                        {g}
                      </MenuItem>
                    ))}
                  </Select>
                </FormControl>
              )}

              {/* Select condicional para turnos ou horas */}
              {mode === "manual" && scheduleType === "Turno" && (
                <FormControl fullWidth margin="normal">
                  <InputLabel id="shifts-select-label">Turnos</InputLabel>
                  <Select
                    labelId="shifts-select-label"
                    value={shifts}
                    label="Turnos"
                    onChange={(e) => setShifts(e.target.value)}
                  >
                    <MenuItem value={2}>2 turnos</MenuItem>
                    <MenuItem value={3}>3 turnos</MenuItem>
                  </Select>
                </FormControl>
              )}
              {mode === "manual" && scheduleType === "Horas" && (
                <FormControl fullWidth margin="normal">
                  <InputLabel id="hours-select-label">Horas</InputLabel>
                  <Select
                    labelId="hours-select-label"
                    value={shifts}
                    label="Horas"
                    onChange={(e) => setShifts(e.target.value)}
                  >
                    <MenuItem value={13}>13 Horas</MenuItem>
                    <MenuItem value={26}>26 Horas</MenuItem>
                  </Select>
                </FormControl>
              )}

              {/* Select de algoritmo filtrado */}
              {(mode === "problem" || scheduleType) && (
                <FormControl fullWidth margin="normal">
                  <InputLabel id="algorithm-select-label">Algoritmo</InputLabel>
                  <Select
                    labelId="algorithm-select-label"
                    value={selectedAlgorithm}
                    label="Algoritmo"
                    onChange={(e) => setSelectedAlgorithm(e.target.value)}
                  >
                    {availableAlgorithms.map((alg) => (
                      <MenuItem key={alg.value} value={alg.value}>{alg.label}</MenuItem>
                    ))}
                  </Select>
                </FormControl>
              )}

              {mode === "manual" && ["ILP_2", "ILP_2_Half_Intervals", "ILP_3", "ILP_3_Half_Intervals", "ILP_4", "ILP_4_Half_Intervals"].includes(selectedAlgorithm) && (
                <FormControl fullWidth margin="normal">
                  <InputLabel id="solver-select-label">Solver</InputLabel>
                  <Select
                    labelId="solver-select-label"
                    value={selectedSolver}
                    label="Solver"
                    onChange={(e) => setSelectedSolver(e.target.value)}
                  >
                    <MenuItem value="CBC">CBC (Open Source)</MenuItem>
                    <MenuItem value="GUROBI">Gurobi (Commercial)</MenuItem>
                  </Select>
                </FormControl>
              )}

              {mode === "manual" && (
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
              )}

              {mode === "manual" && (
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
              )}
            </Paper>
          </Grid>
        </Grid>

        <Box sx={{ display: "flex", justifyContent: "left", marginTop: 3, marginLeft: "17%", gap: 2 }}>
          <Button variant="contained" color="success" onClick={handleSave} >
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
