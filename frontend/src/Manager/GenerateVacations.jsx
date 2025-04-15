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
      console.error("Erro ao buscar templates:", error);
    }
  };

  useEffect(() => {
    fetchTemplates();
  }, []);

  const handleGenerate = async () => {
    if (!templateName.trim()) {
      setNameError(true);
      return;
    }
    try {
      await axios.post(`${baseurl}/vacation/random/${templateName}`);
      await fetchTemplates();
      await showTemplateDetails(templateName);
      setSuccessOpen(true);
      setNameError(false);
    } catch (err) {
      console.error("Erro ao gerar férias:", err);
      setErrorOpen(true);
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
      await axios.post(`${baseurl}/vacation/csv/${templateName}`, formData, {
        headers: { "Content-Type": "multipart/form-data" },
      });
      await fetchTemplates();
      await showTemplateDetails(templateName);
      setCsvFile(null);
      setSuccessOpen(true);
      setNameError(false);
    } catch (err) {
      console.error("Erro ao importar CSV:", err);
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
      console.error("Erro ao buscar detalhes do template:", err);
    }
  };

  return (
    <div className="admin-container">
      <Sidebar_Manager />
      <div className="main-content" style={{ padding: 20 }}>
        <Typography variant="h4" gutterBottom>
          Geração de Férias
        </Typography>

        <Paper style={{ padding: 20, marginBottom: 20 }}>
          <Typography variant="h6" gutterBottom>
            Criar novo template
          </Typography>
          <TextField
            label="Nome do Template"
            fullWidth
            value={templateName}
            onChange={(e) => setTemplateName(e.target.value)}
            margin="normal"
            error={nameError && !templateName.trim()}
            helperText={nameError && !templateName.trim() ? "Insira um nome para o template" : ""}
          />
          <Box display="flex" justifyContent="center" gap={2} mt={2}>
            <Button
              variant="contained"
              color="primary"
              onClick={handleGenerate}
            >
              Gerar Aleatório
            </Button>
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
                color="secondary"
              >
                Escolher CSV
              </Button>
            </label>
            <Button
              variant="outlined"
              onClick={handleCsvUpload}
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

        {log && <VacationsTemplate name={log.name} data={log.data} />}

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
                    {Object.keys(template.vacations).length} empregados com férias
                  </Typography>
                  <Box display="flex" justifyContent="center" mt={2}>
                    <Button
                      variant="outlined"
                      size="small"
                      onClick={() => showTemplateDetails(template.name)}
                    >
                      Abrir
                    </Button>
                  </Box>
                </Paper>
              ))}
            </Box>
          </Box>
        )}

        <Snackbar open={successOpen} autoHideDuration={3000} onClose={() => setSuccessOpen(false)}>
          <Alert onClose={() => setSuccessOpen(false)} severity="success" sx={{ width: "100%" }}>
            Operação realizada com sucesso!
          </Alert>
        </Snackbar>

        <Snackbar open={errorOpen} autoHideDuration={3000} onClose={() => setErrorOpen(false)}>
          <Alert onClose={() => setErrorOpen(false)} severity="error" sx={{ width: "100%" }}>
            Ocorreu um erro. Verifique o formato do CSV.
          </Alert>
        </Snackbar>
      </div>
    </div>
  );
};

export default GenerateVacations;
