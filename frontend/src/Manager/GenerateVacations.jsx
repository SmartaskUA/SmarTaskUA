import React, { useEffect, useState } from "react";
import axios from "axios";
import baseurl from "../components/BaseUrl";
import Sidebar_Manager from "../components/Sidebar_Manager";
import VacationsTemplate from "../components/manager/VacationsTemplate";
import {
  Box,
  Button,
  Paper,
  TextField,
  Typography,
  Snackbar,
  Alert,
  Input,
} from "@mui/material";

const GenerateVacations = () => {
  const [templateName, setTemplateName] = useState("");
  const [csvFile, setCsvFile] = useState(null);
  const [uploadedFileName, setUploadedFileName] = useState("");
  const [successOpen, setSuccessOpen] = useState(false);
  const [errorOpen, setErrorOpen] = useState(false);
  const [nameError, setNameError] = useState(false);
  const [log, setLog] = useState(null);
  const [templates, setTemplates] = useState([]);

  const fetchTemplates = async () => {
    try {
      const response = await axios.get(`${baseurl}/vacation/`);
      setTemplates(response.data);
    } catch (error) {
      console.error("Error fetching templates:", error);
    }
  };

  useEffect(() => {
    fetchTemplates();
  }, []);

  const handleCsvUpload = async () => {
    if (!templateName.trim()) {
      setNameError(true);
      return;
    }
    if (!csvFile) return;

    const formData = new FormData();
    formData.append("file", csvFile);

    try {
      await axios.post(`${baseurl}/vacation/csv/${templateName}`, formData, {
        headers: { "Content-Type": "multipart/form-data" },
      });
      await fetchTemplates();
      await showTemplateDetails(templateName);
      setCsvFile(null);
      setUploadedFileName("");
      setSuccessOpen(true);
      setNameError(false);
    } catch (err) {
      console.error("Error uploading CSV:", err);
      setErrorOpen(true);
    }
  };

  const handleFileSelection = (e) => {
    const file = e.target.files[0];
    if (file) {
      setCsvFile(file);
      setUploadedFileName(file.name);
    }
  };

  const showTemplateDetails = async (name) => {
    try {
      const response = await axios.get(`${baseurl}/vacation/`);
      const entry = response.data.find((v) => v.name === name);
      if (entry) {
        setLog({ name: entry.name, data: entry.vacations });
      } else {
        setLog(null);
      }
    } catch (err) {
      console.error("Error fetching template details:", err);
    }
  };

  return (
    <div className="admin-container">
      <Sidebar_Manager />
      <div className="main-content" style={{ padding: 20 }}>
        <Typography variant="h4" gutterBottom>
          Vacation Generation
        </Typography>

        <Paper
          style={{ padding: 20, marginBottom: 20, width: "35%", marginTop: 50 }}
        >
          <Typography variant="h6" gutterBottom>
            Create New Template
          </Typography>

          <Box display="flex" alignItems="center" gap={2} flexWrap="wrap">
            <TextField
              label="Template Name"
              value={templateName}
              onChange={(e) => setTemplateName(e.target.value)}
              error={nameError && !templateName.trim()}
              helperText={
                nameError && !templateName.trim()
                  ? "Please enter a template name"
                  : ""
              }
              size="small"
              style={{ flex: "0 0 250px" }}
            />
            <label htmlFor="csv-upload">
              <Input
                id="csv-upload"
                type="file"
                inputProps={{ accept: ".csv" }}
                onChange={handleFileSelection}
                style={{ display: "none" }}
              />
              <Button
                variant="contained"
                component="span"
                color="success" // Green button
              >
                Choose CSV
              </Button>
            </label>
            <Button variant="outlined" onClick={handleCsvUpload}>
              Upload CSV
            </Button>
          </Box>

          {uploadedFileName && (
            <Box mt={2}>
              <Typography variant="body2" color="textSecondary">
                Selected file: <strong>{uploadedFileName}</strong>
              </Typography>
            </Box>
          )}
        </Paper>

        {log && <VacationsTemplate name={log.name} data={log.data} />}

        {templates.length > 0 && (
          <Box mt={4}>
            <Typography variant="h5" gutterBottom>
              Existing Templates
            </Typography>
            <Box display="flex" flexWrap="wrap" gap={2} style={{ marginTop: 30 }}>
              {templates.map((template) => (
                <Paper
                  key={template.id}
                  style={{
                    width: "250px",
                    padding: "16px",
                    borderRadius: "8px",
                    border: "1px solid #ccc",
                    boxShadow: "0 2px 5px rgba(0,0,0,0.1)",
                  }}
                >
                  <Typography variant="h6" gutterBottom>
                    {template.name}
                  </Typography>
                  <Typography variant="body2" color="textSecondary">
                    {Object.keys(template.vacations).length} employees with
                    vacations
                  </Typography>
                  <Box display="flex" justifyContent="center" mt={2}>
                    <Button
                      variant="outlined"
                      size="small"
                      onClick={() => showTemplateDetails(template.name)}
                    >
                      Open
                    </Button>
                  </Box>
                </Paper>
              ))}
            </Box>
          </Box>
        )}

        <Snackbar
          open={successOpen}
          autoHideDuration={3000}
          onClose={() => setSuccessOpen(false)}
        >
          <Alert
            onClose={() => setSuccessOpen(false)}
            severity="success"
            sx={{ width: "100%" }}
          >
            Operation completed successfully!
          </Alert>
        </Snackbar>

        <Snackbar
          open={errorOpen}
          autoHideDuration={3000}
          onClose={() => setErrorOpen(false)}
        >
          <Alert
            onClose={() => setErrorOpen(false)}
            severity="error"
            sx={{ width: "100%" }}
          >
            An error occurred. Please check the CSV format.
          </Alert>
        </Snackbar>
      </div>
    </div>
  );
};

export default GenerateVacations;
