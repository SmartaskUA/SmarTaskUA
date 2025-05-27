import React, { useState, useEffect } from "react";
import axios from "axios";
import baseurl from "../components/BaseUrl";
import Sidebar_Manager from "../components/Sidebar_Manager";
import MinimumsTemplate from "../components/manager/MinimumsTemplate";
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
  DialogTitle,
  DialogContent,
  DialogContentText,
  DialogActions,
  IconButton,
} from "@mui/material";
import { Close } from "@mui/icons-material";

const ImportMinimums = () => {
  const [templateName, setTemplateName] = useState("");
  const [csvFile, setCsvFile] = useState(null);
  const [uploadedFileName, setUploadedFileName] = useState("");
  const [successOpen, setSuccessOpen] = useState(false);
  const [errorOpen, setErrorOpen] = useState(false);
  const [errorMessage, setErrorMessage] = useState("An error occurred.");
  const [nameError, setNameError] = useState(false);
  const [templates, setTemplates] = useState([]);
  const [selectedTemplate, setSelectedTemplate] = useState(null);
  const [templateToDelete, setTemplateToDelete] = useState(null);
  const [confirmDialogOpen, setConfirmDialogOpen] = useState(false);
  const [hoveredTemplateId, setHoveredTemplateId] = useState(null);

  useEffect(() => {
    fetchTemplates();
  }, []);

  const fetchTemplates = async () => {
    try {
      const response = await axios.get(`${baseurl}/reference/`);
      setTemplates(response.data);
    } catch (err) {
      console.error("Error fetching templates:", err);
      setErrorMessage(err.response?.data?.message || "Error fetching templates.");
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

  const handleCsvUpload = async () => {
    if (!templateName.trim()) {
      setNameError(true);
      return;
    }
    if (!csvFile) return;

    const formData = new FormData();
    formData.append("file", csvFile);

    try {
      await axios.post(`${baseurl}/reference/create?name=${templateName}`, formData, {
        headers: { "Content-Type": "multipart/form-data" },
      });
      setSuccessOpen(true);
      setCsvFile(null);
      setUploadedFileName("");
      setTemplateName("");
      fetchTemplates();
    } catch (err) {
      console.error("Error uploading minimums CSV:", err);
      setErrorMessage(err.response?.data?.message || "An error occurred while uploading.");
      setErrorOpen(true);
    }
  };

  const handleDeleteAllReferenceTemplates = async () => {
    try {
      await axios.delete(`${baseurl}/clearnreset/clean-reference-templates`);
      await fetchTemplates();
      setSelectedTemplate(null);
      setSuccessOpen(true);
    } catch (err) {
      console.error("Error deleting reference templates:", err);
      setErrorMessage(err.response?.data?.message || "Failed to delete reference templates.");
      setErrorOpen(true);
    } finally {
      setConfirmDialogOpen(false);
      setTemplateToDelete(null);
    }
  };

  const handleDeleteOneTemplate = async () => {
    if (!templateToDelete) return;
    try {
      await axios.delete(`${baseurl}/reference/${templateToDelete.id}`);
      setTemplates((prev) => prev.filter((t) => t.id !== templateToDelete.id));
      if (selectedTemplate?.id === templateToDelete.id) {
        setSelectedTemplate(null);
      }
      setSuccessOpen(true);
    } catch (err) {
      console.error("Error deleting template:", err);
      setErrorMessage(err.response?.data?.message || "Failed to delete template.");
      setErrorOpen(true);
    } finally {
      setTemplateToDelete(null);
      setConfirmDialogOpen(false);
    }
  };

  const showTemplateDetails = async (id) => {
    try {
      const response = await axios.get(`${baseurl}/reference/${id}`);
      setSelectedTemplate(response.data);
    } catch (err) {
      console.error("Error loading template details:", err);
      setErrorMessage(err.response?.data?.message || "Failed to load template details.");
      setErrorOpen(true);
    }
  };

  return (
    <div className="admin-container" style={{ overflow: "auto", height: "100vh" }}>
      <Sidebar_Manager />
      <div className="main-content" style={{ padding: 20, marginRight: "2%", maxWidth: "100%" }}>
        <Typography variant="h4" gutterBottom>
          Import Daily Minimums
        </Typography>

        <Paper style={{ padding: 20, marginBottom: 20, width: "60%", marginTop: 30 }}>
          <Typography variant="h6" gutterBottom>
            Reference Template Name
          </Typography>

          <Box display="flex" alignItems="center" gap={2} mt={2} flexWrap="wrap">
            <TextField
              label="Template Name"
              value={templateName}
              onChange={(e) => setTemplateName(e.target.value)}
              error={nameError && !templateName.trim()}
              helperText={nameError && !templateName.trim() ? "Please enter a template name" : ""}
              size="small"
              sx={{ flex: 1, minWidth: "220px", maxWidth: "250px" }}
            />
            <label htmlFor="csv-upload">
              <Input
                id="csv-upload"
                type="file"
                inputProps={{ accept: ".csv" }}
                onChange={handleFileSelection}
                style={{ display: "none" }}
              />
              <Button variant="contained" component="span" color="success">
                Choose CSV
              </Button>
            </label>
            <Button
              variant="outlined"
              onClick={handleCsvUpload}
              disabled={!csvFile}
            >
              Upload CSV
            </Button>
            <Button
              variant="contained"
              color="error"
              onClick={() => {
                setTemplateToDelete(null); 
                setConfirmDialogOpen(true);
              }}
              sx={{ ml: 21 }}
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
                    {template.minimuns?.length || 0} rows of data
                  </Typography>
                  <Box display="flex" justifyContent="center" mt={2}>
                    <Button
                      variant="outlined"
                      size="small"
                      onClick={() => showTemplateDetails(template.id)}
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
          <Box
            display="flex"
            flexDirection="column"
            alignItems="center"
            justifyContent="center"
            height="50vh"
            mt={6}
          >
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

        {selectedTemplate && (
          <Box mt={4} style={{ overflowX: "auto" }}>
            <MinimumsTemplate name={selectedTemplate.name} data={selectedTemplate.minimuns} />
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
                templateToDelete
                  ? handleDeleteOneTemplate()
                  : handleDeleteAllReferenceTemplates()
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

export default ImportMinimums;
