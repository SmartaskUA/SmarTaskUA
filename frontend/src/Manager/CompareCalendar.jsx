import React, { useEffect, useState } from "react";
import {
  Box,
  Typography,
  Select,
  MenuItem,
  Button,
  FormControl,
  InputLabel,
} from "@mui/material";
import Sidebar_Manager from "../components/Sidebar_Manager";
import SockJS from "sockjs-client";
import { Client } from "@stomp/stompjs";
import axios from "axios";
import { CheckCircle, Cancel } from "@mui/icons-material";


function CompareCalendar() {
  const [calendars, setCalendars] = useState([]);
  const [selected1, setSelected1] = useState("");
  const [selected2, setSelected2] = useState("");
  const [comparisonResults, setComparisonResults] = useState(null);
  const [error, setError] = useState(null);

  useEffect(() => {
    const socket = new SockJS("http://localhost:8081/ws");
    const stompClient = new Client({
      webSocketFactory: () => socket,
      onConnect: () => {
        stompClient.subscribe("/topic/comparison/all", (message) => {
          try {
            const data = JSON.parse(message.body);
            if (Array.isArray(data) && data.length > 0) {
              setComparisonResults(data[0]);
            }
          } catch (err) {
            console.error("Erro ao processar resultado:", err);
            setError("Erro ao processar resultado.");
          }
        });
      },
      onStompError: (frame) => {
        console.error("Erro STOMP:", frame);
        setError("Erro de conexão WebSocket.");
      },
    });
    stompClient.activate();
    return () => stompClient.deactivate();
  }, []);

  useEffect(() => {
    axios
      .get("http://localhost:8081/schedules/fetch")
      .then((res) => setCalendars(res.data))
      .catch((err) => {
        console.error("Erro ao buscar calendários:", err);
        setError("Erro ao buscar calendários.");
      });
  }, []);

  const handleCompare = async () => {
    try {
      const cal1 = calendars.find((c) => c.id === selected1);
      const cal2 = calendars.find((c) => c.id === selected2);
      if (!cal1 || !cal2) return;

      const file1 = cal1.data[0];
      const file2 = cal2.data[0];

      const formData = new FormData();
      formData.append("files", new Blob([file1]), "1.csv");
      formData.append("files", new Blob([file2]), "2.csv");

      await axios.post("http://localhost:8081/schedules/analyze", formData, {
        headers: { "Content-Type": "multipart/form-data" },
      });
    } catch (err) {
      console.error("Erro ao iniciar comparação:", err);
      setError("Erro ao iniciar comparação.");
    }
  };

  return (
    <div className="admin-container">
      <Sidebar_Manager />
      <div className="main-content">
        <Typography variant="h4" gutterBottom>
          Comparar Calendários
        </Typography>

        {error && (
          <Typography color="error" gutterBottom>
            {error}
          </Typography>
        )}

        <Box display="flex" gap={2} mb={2} mt={2}>
          <FormControl fullWidth>
            <InputLabel>Calendário 1</InputLabel>
            <Select
              value={selected1}
              label="Calendário 1"
              onChange={(e) => setSelected1(e.target.value)}
            >
              {calendars
                .filter((c) => c.id !== selected2)
                .map((calendar) => (
                  <MenuItem key={calendar.id} value={calendar.id}>
                    {calendar.title}
                  </MenuItem>
                ))}
            </Select>
          </FormControl>

          <FormControl fullWidth>
            <InputLabel>Calendário 2</InputLabel>
            <Select
              value={selected2}
              label="Calendário 2"
              onChange={(e) => setSelected2(e.target.value)}
            >
              {calendars
                .filter((c) => c.id !== selected1)
                .map((calendar) => (
                  <MenuItem key={calendar.id} value={calendar.id}>
                    {calendar.title}
                  </MenuItem>
                ))}
            </Select>
          </FormControl>
        </Box>

        <Button
          variant="contained"
          color="primary"
          disabled={!selected1 || !selected2}
          onClick={handleCompare}
        >
          Comparar
        </Button>

        {comparisonResults?.result && (
          <Box mt={4}>
            <Typography variant="h6" gutterBottom>
              Resultado da Comparação
            </Typography>

            <table style={{ width: "100%", borderCollapse: "collapse", backgroundColor: "#fafafa" }}>
              <thead>
                <tr>
                  <th style={{ borderBottom: "2px solid #ccc", padding: "10px", textAlign: "left" }}>Métrica</th>
                  <th style={{ borderBottom: "2px solid #ccc", padding: "10px", textAlign: "left" }}>Calendário 1</th>
                  <th style={{ borderBottom: "2px solid #ccc", padding: "10px", textAlign: "left" }}>Calendário 2</th>
                  <th style={{ borderBottom: "2px solid #ccc", padding: "10px", textAlign: "left" }}>Diferença</th>
                </tr>
              </thead>
              <tbody>
                {Object.keys(comparisonResults.result["/shared_tmp/1.csv"]).map((key) => {
                  const val1 = comparisonResults.result["/shared_tmp/1.csv"][key];
                  const val2 = comparisonResults.result["/shared_tmp/2.csv"][key];
                  const diff = val2 - val1;

                  return (
                    <tr key={key}>
                      <td style={{ padding: "10px", borderBottom: "1px solid #eee" }}>{key}</td>
                      <td style={{ padding: "10px", borderBottom: "1px solid #eee" }}>{val1}</td>
                      <td style={{ padding: "10px", borderBottom: "1px solid #eee" }}>{val2}</td>
                      <td
                        style={{
                          padding: "10px",
                          borderBottom: "1px solid #eee",
                          color: diff === 0 ? "green" : "red",
                        }}
                      >
                        {diff === 0 ? "Igual" : `${diff > 0 ? "+" : ""}${diff}`}
                      </td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </Box>
        )} 
       
     


      </div>
    </div>
  );
}

export default CompareCalendar;
