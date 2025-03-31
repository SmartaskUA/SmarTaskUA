import React, { useState } from "react";
import axios from "axios";
import baseurl from "../components/BaseUrl";
import Sidebar_Manager from "../components/Sidebar_Manager";
import {
  Container,
  Paper,
  Typography,
  Grid,
  TextField,
  Button,
  Box,
  ToggleButton,
  ToggleButtonGroup
} from "@mui/material";
import BaseUrl from "../components/BaseUrl";

const CreateCalendar = () => {
  // Estados para os campos do formulário
  const [title, setTitle] = useState("");
  const [dateStart, setDateStart] = useState("");
  const [dateEnd, setDateEnd] = useState("");
  const [maxDuration, setMaxDuration] = useState("");
  
  // Estado para o algoritmo selecionado
  const [selectedAlgorithm, setSelectedAlgorithm] = useState("Algoritmo1");

  // Lida com a troca do algoritmo
  const handleAlgorithmChange = (event, newAlgorithm) => {
    if (newAlgorithm !== null) {
      setSelectedAlgorithm(newAlgorithm);
    }
  };

  // POST /schedules/generate: gera um ID aleatório e envia os dados
  const handleSave = async () => {
    // Gera um ID aleatório com 8 caracteres
    const randomId = Math.random().toString(36).substring(2, 10);
    
    const data = {
      id: randomId,
      init: dateStart,
      end: dateEnd,
      algorithm: selectedAlgorithm,
      title: title,
      maxTime: maxDuration,
      requestedAt: new Date().toISOString()
    };

    try {
      const response = await axios.post(`${baseurl}/schedules/generate`, data);
      alert("Dados enviados com sucesso!");
      console.log("Resposta da API:", response.data);
    } catch (error) {
      console.error("Erro ao enviar os dados:", error);
      alert("Erro ao enviar os dados.");
    }
  };

  return (
    <div className="admin-container">
      <Sidebar_Manager />
      <Container maxWidth="md" className="calendar-wrapper" sx={{ mt: 4 }}>
        <Paper elevation={3} sx={{ p: 3 }}>
          <Typography variant="h5" gutterBottom>
            Gerar Horário
          </Typography>
          <Grid container spacing={2}>
            {/* 1ª Linha: Título, Data Início, Data Fim */}
            <Grid item xs={4}>
              <TextField
                fullWidth
                label="Título"
                value={title}
                onChange={(e) => setTitle(e.target.value)}
              />
            </Grid>
            <Grid item xs={4}>
              <TextField
                fullWidth
                type="date"
                label="Data Início"
                value={dateStart}
                onChange={(e) => setDateStart(e.target.value)}
                InputLabelProps={{ shrink: true }}
              />
            </Grid>
            <Grid item xs={4}>
              <TextField
                fullWidth
                type="date"
                label="Data Fim"
                value={dateEnd}
                onChange={(e) => setDateEnd(e.target.value)}
                InputLabelProps={{ shrink: true }}
              />
            </Grid>

            {/* 2ª Linha: Tempo Máximo */}
            <Grid item xs={12}>
              <TextField
                fullWidth
                type="number"
                label="Tempo Máximo (minutos)"
                value={maxDuration}
                onChange={(e) => setMaxDuration(e.target.value)}
              />
            </Grid>

            {/* 3ª Linha: Selecione o Algoritmo */}
            <Grid item xs={12}>
              <Box display="flex" flexDirection="column">
                <Typography variant="subtitle1" gutterBottom>
                  Selecione o Algoritmo:
                </Typography>
                <ToggleButtonGroup
                  color="primary"
                  value={selectedAlgorithm}
                  exclusive
                  onChange={handleAlgorithmChange}
                >
                  <ToggleButton value="Algoritmo1">ALGORITMO 1</ToggleButton>
                  <ToggleButton value="Algoritmo2">ALGORITMO 2</ToggleButton>
                </ToggleButtonGroup>
              </Box>
            </Grid>

            {/* 4ª Linha: Botão Gerar */}
            <Grid item xs={12}>
              <Box sx={{ display: "flex", gap: 2 }}>
                <Button variant="contained" color="primary" onClick={handleSave}>
                  Gerar
                </Button>
              </Box>
            </Grid>
          </Grid>
        </Paper>
      </Container>
    </div>
  );
};

export default CreateCalendar;
