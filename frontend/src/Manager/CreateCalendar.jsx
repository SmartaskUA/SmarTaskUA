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
  Input
} from "@mui/material";

const CreateCalendar = () => {
  const [title, setTitle] = useState("");
  const [dateStart, setDateStart] = useState("");
  const [dateEnd, setDateEnd] = useState("");
  const [maxDuration, setMaxDuration] = useState("");
  const [file, setFile] = useState(null);
  const [fileName, setFileName] = useState("Nenhum arquivo selecionado");
  const [selectedAlgorithm, setSelectedAlgorithm] = useState("Algoritmo1");

  const handleAlgorithmChange = (event, newAlgorithm) => {
    if (newAlgorithm !== null) {
      setSelectedAlgorithm(newAlgorithm);
    }
  };

  // Função para salvar os dados
  const handleSave = async () => {
    const formData = new FormData();
    formData.append("init", dateStart);
    formData.append("end", dateEnd);
    formData.append("algorithm", selectedAlgorithm);
    formData.append("title", title);
    formData.append("maxTime", maxDuration);
    formData.append("requestedAt", new Date().toISOString());
    
    if (file) {
      formData.append("file", file);
    }

    try {
      const response = await axios.post(`${baseurl}/schedules/generate`, formData, {
        headers: { "Content-Type": "multipart/form-data" }
      });
      alert("Dados enviados com sucesso!");
      console.log("Resposta da API:", response.data);
    } catch (error) {
      console.error("Erro ao enviar os dados:", error);
      alert("Erro ao enviar os dados.");
    }
  };
  const handleClear = () => {
    setTitle("");
    setDateStart("");
    setDateEnd("");
    setMaxDuration("");
    setSelectedAlgorithm("Algoritmo1");
    setFile(null);
    setFileName("Nenhum arquivo selecionado");
  };

  const handleFileChange = (event) => {
    const selectedFile = event.target.files[0];
    if (selectedFile) {
      setFile(selectedFile);
      setFileName(selectedFile.name);
    }
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
        <h1>Gerar Horário</h1>
        <Grid container spacing={10}>
          <Grid item xs={12} md={6}>
            <Paper style={{ padding: "20px" }}>
              <Typography variant="h6" gutterBottom>
                Informações do Horário
              </Typography>
              <TextField
                fullWidth
                label="Título"
                value={title}
                onChange={(e) => setTitle(e.target.value)}
                margin="normal"
              />
              <TextField
                fullWidth
                type="date"
                label="Data Início"
                value={dateStart}
                onChange={(e) => setDateStart(e.target.value)}
                InputLabelProps={{ shrink: true }}
                margin="normal"
              />
              <TextField
                fullWidth
                type="date"
                label="Data Fim"
                value={dateEnd}
                onChange={(e) => setDateEnd(e.target.value)}
                InputLabelProps={{ shrink: true }}
                margin="normal"
              />
              <TextField
                fullWidth
                type="number"
                label="Tempo Máximo (minutos)"
                value={maxDuration}
                onChange={(e) => setMaxDuration(e.target.value)}
                margin="normal"
              />
            </Paper>
          </Grid>

          <Grid item xs={12} md={6}>
            <Paper style={{ padding: "20px" }}>
              <Typography variant="h6" gutterBottom>
                Escolha o Algoritmo
              </Typography>
              <Box display="flex" justifyContent="center">
                <ToggleButtonGroup
                  color="primary"
                  value={selectedAlgorithm}
                  exclusive
                  onChange={handleAlgorithmChange}
                >
                  <ToggleButton value="Algoritmo1">ALGORITMO 1</ToggleButton>
                  <ToggleButton value="Algoritmo2">ALGORITMO 2</ToggleButton>
                  <ToggleButton value="Algoritmo3">ALGORITMO 3</ToggleButton>
                </ToggleButtonGroup>
              </Box>

              <Box sx={{ marginTop: 3 }}>
                <Typography variant="subtitle1">Selecionar Arquivo:</Typography>
                <Input
                  type="file"
                  onChange={handleFileChange}
                  fullWidth
                  sx={{ marginTop: 1 }}
                />
                <Typography variant="body2" sx={{ marginTop: 1, fontStyle: "italic" }}>
                  {fileName}
                </Typography>
              </Box>
            </Paper>
          </Grid>
        </Grid>

        <Grid container spacing={2} style={{ marginTop: "20px" }}>
          <Box sx={{ display: "flex", justifyContent: "center", marginTop: 3, gap: 2 }}>
            <Button variant="contained" color="primary" onClick={handleSave}>
              Gerar
            </Button>
            <Button variant="contained" color="secondary" onClick={handleClear}>
              Limpar Tudo
            </Button>
          </Box>
        </Grid>
      </div>
    </div>
  );
};

export default CreateCalendar;
