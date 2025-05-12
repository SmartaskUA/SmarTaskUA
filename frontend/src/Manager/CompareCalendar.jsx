import React, { useEffect, useState } from "react";
import {
  Box,
  Typography,
  Select,
  MenuItem,
  Button,
  FormControl,
  InputLabel,
  Tooltip,
} from "@mui/material";
import Sidebar_Manager from "../components/Sidebar_Manager";
import SockJS from "sockjs-client";
import { Client } from "@stomp/stompjs";
import axios from "axios";
import HelpOutlineIcon from "@mui/icons-material/HelpOutline";
import { Margin } from "@mui/icons-material";

const metricInfo = {
  missedWorkDays: {
    label: "Missed Work Days",
    description: "Number of workdays that were missed.",
  },
  missedVacationDays: {
    label: "Missed Vacation Days",
    description: "Days of vacation that were not used as planned.",
  },
  missedTeamMin: {
    label: "Missed Team Minimum Time",
    description: "Minutes when the team was below the minimum number of members.",
  },
  workHolidays: {
    label: "Work on Holidays",
    description: "How many times someone was scheduled to work on a holiday.",
  },
  consecutiveDays: {
    label: "Consecutive Days Worked",
    description: "How many times a person worked multiple consecutive days without a break.",
  },
  shiftBalance: {
    label: "Shift Balancing",
    description: "Difference in the number of shifts assigned to people.",
  },
  tmFails: {
    label: "TM Failures",
    description: "Failures in following the shift model restrictions.",
  },
  singleTeamViolations: {
    label: "Single Team Violations",
    description: "Cases where members of a team were scheduled alone.",
  },
  twoTeamPreferenceViolations: {
    label: "Two-Team Preference Violations",
    description: "Break in the preference to work with a specific colleague.",
  },
};

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
        setError("Error with WebSocket connection.");
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
        <Typography variant="h4" gutterBottom sx={{ mb: 4 }}>
          Compare Calendars
        </Typography>

        {error && (
          <Typography color="error" gutterBottom>
            {error}
          </Typography>
        )}

        <Box display="flex" gap={2} mb={2} alignItems="center">
          <FormControl fullWidth>
            <InputLabel>Calendar 1</InputLabel>
            <Select
              value={selected1}
              label="Calendar 1"
              onChange={(e) => setSelected1(e.target.value)}
              style={{ width: "400px" }}
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
              style={{ width: "400px" }}
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
            sx={{
              height: "45px",
              width: "35%",
              fontSize: "16px",
              padding: "0 20px",
              borderRadius: "8px",
              backgroundColor: "#1976D2",
              "&:hover": {
                backgroundColor: "#1565C0",
              },
            }}
          >
            Compare
          </Button>
        </Box>

        {comparisonResults?.result && (
          <Box mt={4}>
            <Typography variant="h5" gutterBottom>
              Comparison Results
            </Typography>
            <table
              style={{
                width: "100%",
                borderCollapse: "collapse",
                backgroundColor: "#f4f4f4",
                fontSize: "1rem",
                borderRadius: "8px",
                overflow: "hidden",
              }}
            >
              <thead>
                <tr style={{ backgroundColor: "#1976D2", color: "white" }}>
                  <th
                    style={{
                      padding: "12px",
                      textAlign: "left",
                      borderBottom: "2px solid #ddd",
                    }}
                  >
                    Metric
                  </th>
                  <th
                    style={{
                      padding: "12px",
                      textAlign: "left",
                      borderBottom: "2px solid #ddd",
                    }}
                  >
                    Calendar 1
                  </th>
                  <th
                    style={{
                      padding: "12px",
                      textAlign: "left",
                      borderBottom: "2px solid #ddd",
                    }}
                  >
                    Calendar 2
                  </th>
                  <th
                    style={{
                      padding: "12px",
                      textAlign: "left",
                      borderBottom: "2px solid #ddd",
                    }}
                  >
                    Difference
                  </th>
                </tr>
              </thead>
              <tbody>
                {Object.keys(comparisonResults.result["/shared_tmp/1.csv"]).map(
                  (key, index) => {
                    const val1 = comparisonResults.result["/shared_tmp/1.csv"][key];
                    const val2 = comparisonResults.result["/shared_tmp/2.csv"][key];
                    const diff = val2 - val1;

                    return (
                      <tr
                        key={key}
                        style={{
                          backgroundColor: index % 2 === 0 ? "#f9f9f9" : "#ffffff",
                          borderBottom: "1px solid #ddd",
                        }}
                      >
                        <td
                          style={{
                            padding: "12px",
                            display: "flex",
                            alignItems: "center",
                            gap: "8px",
                          }}
                        >
                          <Tooltip
                            title={
                              <Typography sx={{ fontSize: "0.9rem", p: 1, maxWidth: 280 }}>
                                {metricInfo[key]?.description || "No description available."}
                              </Typography>
                            }
                            arrow
                            placement="top"
                            componentsProps={{
                              tooltip: {
                                sx: {
                                  backgroundColor: "#333",
                                  color: "#fff",
                                  borderRadius: 2,
                                  boxShadow: 3,
                                },
                              },
                            }}
                          >
                            <span
                              style={{
                                cursor: "help",
                                fontWeight: 500,
                                display: "flex",
                                alignItems: "center",
                                gap: "6px",
                              }}
                            >
                              {metricInfo[key]?.label || key}
                              <HelpOutlineIcon fontSize="small" sx={{ color: "#888" }} />
                            </span>
                          </Tooltip>
                        </td>
                        <td style={{ padding: "12px" }}>{val1}</td>
                        <td style={{ padding: "12px" }}>{val2}</td>
                        <td
                          style={{
                            padding: "12px",
                            color: diff === 0 ? "#1976D2" : "#f44336", 
                          }}
                        >
                          {diff === 0 ? "Equal" : `${diff > 0 ? "+" : ""}${diff}`}
                        </td>
                      </tr>
                    );
                  }
                )}
              </tbody>
            </table>
          </Box>
        )}
      </div>
    </div>
  );
}

export default CompareCalendar;
