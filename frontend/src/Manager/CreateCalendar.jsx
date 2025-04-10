import React, { useState } from "react";
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
} from "@mui/material";

const CreateCalendar = () => {
  const [title, setTitle] = useState("");
  const [dateStart, setDateStart] = useState("");
  const [dateEnd, setDateEnd] = useState("");
  const [maxDuration, setMaxDuration] = useState("");

  const [selectedAlgorithm, setSelectedAlgorithm] = useState("Algorithm1");

  const [successOpen, setSuccessOpen] = useState(false);
  const [errorOpen, setErrorOpen] = useState(false);

  const handleAlgorithmChange = (event, newAlgorithm) => {
    if (newAlgorithm !== null) {
      setSelectedAlgorithm(newAlgorithm);
    }
  };

  // Function to save the data
  const handleSave = async () => {
    const data = {
      init: dateStart,
      end: dateEnd,
      algorithm: selectedAlgorithm,
      title: title,
      maxTime: maxDuration,
      requestedAt: new Date().toISOString(),
    };

    try {
      const response = await axios.post(`${baseurl}/schedules/generate`, data);
      console.log("API Response:", response.data);
      setSuccessOpen(true); 
    } catch (error) {
      console.error("Error sending data:", error);
      if (error.response?.data?.trace) {
        console.error("Trace:", error.response.data.trace);
      }
      setErrorOpen(true); 
    }
  };

  // Function to clear the fields
  const handleClear = () => {
    setTitle("");
    setDateStart("");
    setDateEnd("");
    setMaxDuration("");
    setSelectedAlgorithm("Algorithm1");
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
        <div style={{ display: "flex", justifyContent: "center", marginBottom: "2%" }}>
          <h1>Generate Schedule</h1>
        </div>

        <Grid container spacing={10}>
          <Grid item xs={12} md={6}>
            <Paper style={{ padding: "20px" }}>
              <Typography variant="h6" gutterBottom>
                Schedule Information
              </Typography>
              <TextField
                fullWidth
                label="Title"
                value={title}
                onChange={(e) => setTitle(e.target.value)}
                margin="normal"
              />
              <TextField
                fullWidth
                type="date"
                label="Start Date"
                value={dateStart}
                onChange={(e) => setDateStart(e.target.value)}
                InputLabelProps={{ shrink: true }}
                margin="normal"
              />
              <TextField
                fullWidth
                type="date"
                label="End Date"
                value={dateEnd}
                onChange={(e) => setDateEnd(e.target.value)}
                InputLabelProps={{ shrink: true }}
                margin="normal"
              />
              <TextField
                fullWidth
                type="number"
                label="Max Duration (minutes)"
                value={maxDuration}
                onChange={(e) => setMaxDuration(e.target.value)}
                margin="normal"
              />
            </Paper>
          </Grid>
          <Grid item xs={12} md={6}>
            <Paper style={{ padding: "20px" }}>
              <Typography variant="h6" gutterBottom>
                Choose the Algorithm
              </Typography>
              <Box display="flex" justifyContent="center">
                <ToggleButtonGroup
                  color="primary"
                  value={selectedAlgorithm}
                  exclusive
                  onChange={handleAlgorithmChange}
                >
                  <ToggleButton value="Algorithm1">CSP</ToggleButton>
                  <ToggleButton value="Algorithm2"> Hill Climbing</ToggleButton>
                  <ToggleButton value="Algorithm3">ALGORITHM 3</ToggleButton>
                </ToggleButtonGroup>
              </Box>
            </Paper>
          </Grid>
        </Grid>

        <Grid container spacing={2} style={{ marginTop: "20px" }}>
          <Box sx={{ display: "flex", justifyContent: "center", marginTop: 3, gap: 2 }}>
            <Button variant="contained" color="primary" onClick={handleSave}>
              Generate
            </Button>
            <Button variant="contained" color="secondary" onClick={handleClear}>
              Clear All
            </Button>
          </Box>
        </Grid>
        <Snackbar
          open={successOpen}
          autoHideDuration={3000}
          onClose={() => setSuccessOpen(false)}
          anchorOrigin={{ vertical: "top", horizontal: "center" }}
        >
          <Alert onClose={() => setSuccessOpen(false)} severity="success" sx={{ width: "100%" }}>
            Task Requested Successfully!
          </Alert>
        </Snackbar>

        <Snackbar
          open={errorOpen}
          autoHideDuration={3000}
          onClose={() => setErrorOpen(false)}
          anchorOrigin={{ vertical: "top", horizontal: "center" }}
        >
          <Alert onClose={() => setErrorOpen(false)} severity="error" sx={{ width: "100%" }}>
            Failed to create calendar. Try again.
          </Alert>
        </Snackbar>
      </div>
    </div>
  );
};

export default CreateCalendar;
