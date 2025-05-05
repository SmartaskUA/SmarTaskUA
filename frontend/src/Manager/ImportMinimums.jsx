import React, { useState, useEffect } from "react";
import axios from "axios";
import baseurl from "../components/BaseUrl";
import Sidebar_Manager from "../components/Sidebar_Manager";
import MinimumsTemplate from "../components/manager/MinimumsTemplate";
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

const ImportMinimums = () => {
  const [templateName, setTemplateName] = useState("");
  const [csvFile, setCsvFile] = useState(null);
  const [uploadedFileName, setUploadedFileName] = useState("");
  const [successOpen, setSuccessOpen] = useState(false);
  const [errorOpen, setErrorOpen] = useState(false);
  const [nameError, setNameError] = useState(false);
  const [templates, setTemplates] = useState([]);
  const [selectedTemplate, setSelectedTemplate] = useState(null);

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
      console.error("Erro ao importar CSV de mínimos:", err);
      setErrorOpen(true);
    }
  };

  const fetchTemplates = async () => {
    try {
      const response = await axios.get(`${baseurl}/reference/`);
      setTemplates(response.data);
    } catch (err) {
      console.error("Erro ao buscar templates:", err);
    }
  };

  const showTemplateDetails = async (id) => {
    try {
      const response = await axios.get(`${baseurl}/reference/${id}`);
      console.log("Resposta recebida (JSON):", response.data);
      setSelectedTemplate(response.data);
    } catch (err) {
      console.error("Erro ao carregar detalhes do template:", err);
    }
  };

  useEffect(() => {
    fetchTemplates();
  }, []);

  return (
    <div className="admin-container">
      <Sidebar_Manager />
      <div className="main-content" style={{ padding: 20  , marginRight: "5%" }}>
        <Typography variant="h4" gutterBottom >
          Importar Mínimos por Dia
        </Typography>

        <Paper style={{ padding: 20, marginBottom: 20, width: "100%" }}>
          <Typography variant="h6" gutterBottom>
            Nome do Template de Mínimos
          </Typography>

          <Box display="flex" alignItems="center" gap={2} mt={2} style={{ width: "40%" }}>
            <TextField
              label="Nome do Template"
              value={templateName}
              onChange={(e) => setTemplateName(e.target.value)}
              error={nameError && !templateName.trim()}
              helperText={nameError && !templateName.trim() ? "Insira um nome para o template" : ""}
              size="small"
              sx={{ flex: 1 }}
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
                Escolher CSV
              </Button>
            </label>
            <Button
              variant="outlined"
              onClick={handleCsvUpload}
              disabled={!csvFile}
            >
              Enviar CSV
            </Button>
          </Box>

          {uploadedFileName && (
            <Box mt={2}>
              <Typography variant="body2" color="textSecondary">
                Ficheiro selecionado: <strong>{uploadedFileName}</strong>
              </Typography>
            </Box>
          )}
        </Paper>

        {templates.length > 0 && (
          <Box mt={4}>
            <Typography variant="h5" gutterBottom>Templates Existentes</Typography>
            <Box display="flex" flexWrap="wrap" gap={2}>
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
                    {template.minimuns?.length || 0} linhas de dados
                  </Typography>
                  <Box display="flex" justifyContent="center" mt={2}>
                    <Button
                      variant="outlined"
                      size="small"
                      onClick={() => showTemplateDetails(template.id)}
                    >
                      Abrir
                    </Button>
                  </Box>
                </Paper>
              ))}
            </Box>
          </Box>
        )}

        {selectedTemplate && (
          <Box mt={4}>
            <MinimumsTemplate name={selectedTemplate.name} data={selectedTemplate.minimuns} />
          </Box>
        )}

        <Snackbar open={successOpen} autoHideDuration={3000} onClose={() => setSuccessOpen(false)}>
          <Alert onClose={() => setSuccessOpen(false)} severity="success" sx={{ width: "100%" }}>
            CSV de mínimos enviado com sucesso!
          </Alert>
        </Snackbar>

        <Snackbar open={errorOpen} autoHideDuration={3000} onClose={() => setErrorOpen(false)}>
          <Alert onClose={() => setErrorOpen(false)} severity="error" sx={{ width: "100%" }}>
            Erro ao enviar o CSV. Verifique o formato.
          </Alert>
        </Snackbar>
      </div>
    </div>
  );
};

export default ImportMinimums;
