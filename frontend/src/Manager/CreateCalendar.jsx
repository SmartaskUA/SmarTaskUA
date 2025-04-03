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
  Paper
} from "@mui/material";

const CreateCalendar = () => {
  // States for the form fields
  const [title, setTitle] = useState("");
  const [dateStart, setDateStart] = useState("");
  const [dateEnd, setDateEnd] = useState("");
  const [maxDuration, setMaxDuration] = useState("");

  // State for the selected algorithm
  const [selectedAlgorithm, setSelectedAlgorithm] = useState("Algorithm1");

  // Handles the change of the selected algorithm
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
      alert("Data sent successfully!");
      console.log("API Response:", response.data);
    } catch (error) {
      console.error("Error sending data:", error);
      if (error.response && error.response.data && error.response.data.trace) {
        console.error("Trace:", error.response.data.trace);
      }
      alert("Error sending data.");
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
        <h1>Generate Schedule</h1>

        {/* Grid layout dividing the screen into two columns */}
        <Grid container spacing={10}>
          {/* Left column - Form */}
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

          {/* Right column - Algorithm selection */}
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
                  <ToggleButton value="Algorithm1">ALGORITHM 1</ToggleButton>
                  <ToggleButton value="Algorithm2">ALGORITHM 2</ToggleButton>
                  <ToggleButton value="Algorithm3">ALGORITHM 3</ToggleButton>
                </ToggleButtonGroup>
              </Box>
            </Paper>
          </Grid>
        </Grid>

        {/* Buttons to save and clear the form */}
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
      </div>
    </div>
  );
};

export default CreateCalendar;
