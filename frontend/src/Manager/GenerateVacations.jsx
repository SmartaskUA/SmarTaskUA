import React, { useEffect, useState } from "react";
import axios from "axios";
import baseurl from "../components/BaseUrl";
import Sidebar_Manager from "../components/Sidebar_Manager";
import VacationsTemplate from "../components/manager/VacationsTemplate";
import NotificationSnackbar from "../components/manager/NotificationSnackbar";
import EmptySVG from "../assets/images/Empty-pana.svg";

import {
  Box,
  Button,
  Paper,
  TextField,
  Typography,
  Input,
  Dialog,
  DialogActions,
  DialogContent,
  DialogContentText,
  DialogTitle,
  IconButton,
} from "@mui/material";
import { Close } from "@mui/icons-material";

const GenerateVacations = () => {
  const [templateName, setTemplateName] = useState("");
  const [csvFile, setCsvFile] = useState(null);
  const [uploadedFileName, setUploadedFileName] = useState("");
  const [successOpen, setSuccessOpen] = useState(false);
  const [errorOpen, setErrorOpen] = useState(false);
  const [errorMessage, setErrorMessage] = useState("An error occurred.");
  const [nameError, setNameError] = useState(false);
  const [log, setLog] = useState(null);
  const [templates, setTemplates] = useState([]);
  const [confirmDialogOpen, setConfirmDialogOpen] = useState(false);
  const [templateToDelete, setTemplateToDelete] = useState(null);
  const [hoveredTemplateId, setHoveredTemplateId] = useState(null);

  const fetchTemplates = async () => {
    try {
      const response = await axios.get(`${baseurl}/vacation/`);
      setTemplates(response.data);
    } catch (error) {
      console.error("Error fetching templates:", error);
      setErrorMessage(error.response?.data?.message || "Error fetching templates.");
      setErrorOpen(true);
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
      setCsvFile(null);
      setUploadedFileName("");
      setSuccessOpen(true);
      setNameError(false);
    } catch (err) {
      console.error("Error uploading CSV:", err);
      const rawMsg = err.response?.data?.message || err.response?.data;
      let displayMsg = rawMsg || "An error occurred. Please check the CSV format.";
      if (typeof displayMsg === "string" && displayMsg.includes("Caused by:")) {
        const [, cause] = displayMsg.split("Caused by:");
        displayMsg = cause?.trim() || displayMsg;
      }
      setErrorMessage(displayMsg);
      setErrorOpen(true);
    }
  };

  const handleDeleteAllTemplates = async () => {
    try {
      await axios.delete(`${baseurl}/clearnreset/clean-vacation-templates`);
      await fetchTemplates();
      setLog(null);
      setSuccessOpen(true);
    } catch (err) {
      console.error("Error deleting templates:", err);
      setErrorMessage(err.response?.data?.message || "Failed to delete templates.");
      setErrorOpen(true);
    }
  };

  const handleDeleteOneTemplate = async () => {
    if (!templateToDelete) return;
    try {
      await axios.delete(`${baseurl}/vacation/${templateToDelete.id}`);
      setTemplates((prev) => prev.filter((t) => t.id !== templateToDelete.id));
      if (log?.name === templateToDelete.name) {
        setLog(null);
      }
      setSuccessOpen(true);
    } catch (err) {
      console.error("Error deleting template:", err);
      setErrorMessage(err.response?.data?.message || "Failed to delete template.");
      setErrorOpen(true);
    } finally {
      setConfirmDialogOpen(false);
      setTemplateToDelete(null);
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
      setErrorMessage(err.response?.data?.message || "Failed to fetch template details.");
      setErrorOpen(true);
    }
  };

  return (
    <div className="admin-container">
      <Sidebar_Manager />
      <div className="main-content" style={{ padding: 20 }}>
        <Typography variant="h4" gutterBottom>
          Vacation Generation
        </Typography>

        <Paper style={{ padding: 20, marginBottom: 20, width: "90%", marginTop: 30 }}>
          <Typography variant="h6" gutterBottom>
            Create New Template
          </Typography>

          <Box display="flex" flexWrap="wrap" alignItems="center" gap={2}>
            <TextField
              label="Template Name"
              value={templateName}
              onChange={(e) => setTemplateName(e.target.value)}
              error={nameError && !templateName.trim()}
              helperText={nameError && !templateName.trim() ? "Please enter a template name" : ""}
              size="small"
              sx={{ width: "250px" }}
            />

            <label htmlFor="csv-upload" style={{ height: 40 }}>
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
                color="success"
                size="small"
                sx={{ height: 40, minWidth: 100 }}
              >
                Choose CSV
              </Button>
            </label>

            <Button
              variant="outlined"
              onClick={handleCsvUpload}
              size="small"
              sx={{ height: 40, minWidth: 100 }}
            >
              Upload CSV
            </Button>

            <Box flexGrow={1} />

            <Button
              variant="contained"
              color="error"
              onClick={() => setConfirmDialogOpen(true)}
              size="small"
              sx={{ height: 40, minWidth: 140 }}
            >
              Delete All Templates
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

        {templates.length > 0 && (
          <Box mt={4}>
            <Typography variant="h5" gutterBottom>Existing Templates</Typography>
            <Box display="flex" flexWrap="wrap" gap={2}>
              {templates.map((template) => (
                <Paper
                  key={template.id}
                  onMouseEnter={() => setHoveredTemplateId(template.id)}
                  onMouseLeave={() => setHoveredTemplateId(null)}
                  style={{
                    width: "250px",
                    padding: "16px",
                    borderRadius: "8px",
                    border: "1px solid #ccc",
                    boxShadow: "0 2px 5px rgba(0,0,0,0.1)",
                    position: "relative",
                  }}
                >
                  <IconButton
                    size="small"
                    onClick={() => {
                      setTemplateToDelete(template);
                      setConfirmDialogOpen(true);
                    }}
                    sx={{
                      position: "absolute",
                      top: 6,
                      right: 6,
                      backgroundColor: hoveredTemplateId === template.id ? "#ff5252" : "#e0e0e0",
                      color: hoveredTemplateId === template.id ? "#fff" : "#555",
                      "&:hover": { backgroundColor: "#ff1744" },
                      width: "20px",
                      height: "20px",
                      padding: "2px",
                    }}
                  >
                    <Close fontSize="10px" />
                  </IconButton>

                  <Typography variant="h6" gutterBottom>
                    {template.name}
                  </Typography>
                  <Typography variant="body2" color="textSecondary">
                    {Object.keys(template.vacations).length} employees with vacations
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

        {templates.length === 0 && (
          <Box display="flex" flexDirection="column" alignItems="center" justifyContent="center" height="50vh" mt={6}>
            <img
              src={EmptySVG}
              alt="No templates"
              style={{ width: 400, height: 400, marginBottom: 20 }}
            />
            <Typography variant="h6" color="textSecondary">
              No templates created yet.
            </Typography>
          </Box>
        )}

        {log && (
          <Box mt={6}>
            <VacationsTemplate name={log.name} data={log.data} />
          </Box>
        )}

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

        <Dialog open={confirmDialogOpen} onClose={() => setConfirmDialogOpen(false)}>
          <DialogTitle>Confirm Deletion</DialogTitle>
          <DialogContent>
            <DialogContentText>
              {templateToDelete
                ? `Are you sure you want to delete the template "${templateToDelete.name}"?`
                : "Are you sure you want to delete all templates? This action cannot be undone."}
            </DialogContentText>
          </DialogContent>
          <DialogActions>
            <Button onClick={() => {
              setConfirmDialogOpen(false);
              setTemplateToDelete(null);
            }} color="primary">
              Cancel
            </Button>
            <Button
              onClick={() =>
                templateToDelete ? handleDeleteOneTemplate() : handleDeleteAllTemplates()
              }
              color="error"
            >
              Delete
            </Button>
          </DialogActions>
        </Dialog>
      </div>
    </div>
  );
};

export default GenerateVacations;
