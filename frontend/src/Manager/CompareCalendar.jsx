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
            console.error("Error processing result:", err);
            setError("Error processing result.");
          }
        });
      },
      onStompError: (frame) => {
        console.error("STOMP error:", frame);
        setError("WebSocket connection error.");
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
        console.error("Error fetching calendars:", err);
        setError("Error fetching calendars.");
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
      console.error("Error starting comparison:", err);
      setError("Error starting comparison.");
    }
  };

  return (
    <div className="admin-container">
      <Sidebar_Manager />
      <div className="main-content" style={{ marginRight: "5%" }}>
        <Typography variant="h4" style={{marginBottom:"3.5%"}}gutterBottom>
          Compare Calendars
        </Typography>

        {error && (
          <Typography color="error" gutterBottom>
            {error}
          </Typography>
        )}

        <Box display="flex" gap={2} mb={2} mt={2} alignItems="center">
          <FormControl fullWidth>
            <InputLabel>Calendar 1</InputLabel>
            <Select
              value={selected1}
              label="Calendar 1"
              onChange={(e) => setSelected1(e.target.value)}
              style={{ width: "500px" }}
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
            <InputLabel>Calendar 2</InputLabel>
            <Select
              value={selected2}
              label="Calendar 2"
              onChange={(e) => setSelected2(e.target.value)}
              style={{ width: "500px" }}
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

          <Button
            variant="contained"
            color="primary"
            disabled={!selected1 || !selected2}
            onClick={handleCompare}
            style={{ height: '100%' , width: '60%', alignItems: 'center', justifyContent: 'center', display: 'flex'}}
          >
            Compare
          </Button>
        </Box>

        {comparisonResults?.result && (
          <Box mt={4}>
            <Typography variant="h6" gutterBottom>
              Comparison Results
            </Typography>

            <table style={{ width: "100%", borderCollapse: "collapse", backgroundColor: "#fafafa" }}>
              <thead>
                <tr>
                  <th style={{ borderBottom: "2px solid #ccc", padding: "10px", textAlign: "left" }}>Metric</th>
                  <th style={{ borderBottom: "2px solid #ccc", padding: "10px", textAlign: "left" }}>Calendar 1</th>
                  <th style={{ borderBottom: "2px solid #ccc", padding: "10px", textAlign: "left" }}>Calendar 2</th>
                  <th style={{ borderBottom: "2px solid #ccc", padding: "10px", textAlign: "left" }}>Difference</th>
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
                        {diff === 0 ? "Equal" : `${diff > 0 ? "+" : ""}${diff}`}
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
