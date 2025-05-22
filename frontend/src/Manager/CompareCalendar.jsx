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
import BaseUrl from "../components/BaseUrl";

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
    label: "Work on Holidays and Sundays",
    description: "How many times someone was scheduled to work on a holiday or Sunday.",
  },
  consecutiveDays: {
    label: "Consecutive Days Worked",
    description: "How many times a person worked multiple consecutive days without a break.",
  },
  shiftBalance: {
    label: "Shift Balancing",
    description: "Difference in the number of shifts assigned to people.",
  },
  emFails: {
    label: "E->M Failures",
    description: "An employee cannot be scheduled for an evening (E) shift followed by a morning (M) shift on the next day.",
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

export default function CompareCalendar() {
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
        stompClient.subscribe("/topic/comparison/all", (msg) => {
          try {
            const data = JSON.parse(msg.body);
            if (Array.isArray(data) && data.length > 0) {
              setComparisonResults(data[0]);
            }
          } catch (e) {
            console.error("Error processing result:", e);
            setError("Error processing comparison result.");
          }
        });
      },
      onStompError: (frame) => {
        console.error("STOMP error:", frame);
        setError("WebSocket error.");
      },
    });
    stompClient.activate();
    return () => stompClient.deactivate();
  }, []);

  useEffect(() => {
    axios
      .get(`${BaseUrl}/schedules/fetch`)
      .then((res) => setCalendars(res.data))
      .catch((e) => {
        console.error("Error fetching calendars:", e);
        setError("Error fetching calendars.");
      });
  }, []);

  const handleCompare = async () => {
    try {
      const cal1 = calendars.find((c) => c.id === selected1);
      const cal2 = calendars.find((c) => c.id === selected2);
      if (!cal1 || !cal2) {
        setError("Please select two calendars.");
        return;
      }

      const toCsvString = (rows) =>
        rows.map((row) => row.join(",")).join("\n");

      const blob1 = new Blob([toCsvString(cal1.data)], {
        type: "text/csv;charset=utf-8",
      });
      const blob2 = new Blob([toCsvString(cal2.data)], {
        type: "text/csv;charset=utf-8",
      });

      const fd = new FormData();
      fd.append("files", blob1, `${cal1.id}.csv`);
      fd.append("files", blob2, `${cal2.id}.csv`);

      await axios.post(`${BaseUrl}/schedules/analyze`, fd);
      setError(null);
    } catch (e) {
      console.error("Error starting comparison:", e);
      setError("Error starting comparison: " + e.message);
    }
  };

  // render
  return (
    <div className="admin-container">
      <Sidebar_Manager />
      <div className="main-content" style={{ marginRight: 24 }}>
        <Typography variant="h4" gutterBottom>
          Compare Calendars
        </Typography>

        {error && (
          <Typography color="error" gutterBottom>
            {error}
          </Typography>
        )}

        <Box display="flex" alignItems="center" gap={2} mb={4}>
          <FormControl sx={{ minWidth: 300 }}>
            <InputLabel>Calendar 1</InputLabel>
            <Select
              value={selected1}
              label="Calendar 1"
              onChange={(e) => setSelected1(e.target.value)}
            >
              {calendars
                .filter((c) => c.id !== selected2)
                .map((c) => (
                  <MenuItem key={c.id} value={c.id}>
                    {c.title}
                  </MenuItem>
                ))}
            </Select>
          </FormControl>

          <FormControl sx={{ minWidth: 300 }}>
            <InputLabel>Calendar 2</InputLabel>
            <Select
              value={selected2}
              label="Calendar 2"
              onChange={(e) => setSelected2(e.target.value)}
            >
              {calendars
                .filter((c) => c.id !== selected1)
                .map((c) => (
                  <MenuItem key={c.id} value={c.id}>
                    {c.title}
                  </MenuItem>
                ))}
            </Select>
          </FormControl>

          <Button
            variant="contained"
            disabled={!selected1 || !selected2}
            onClick={handleCompare}
          >
            Compare
          </Button>
        </Box>

        {comparisonResults?.result && (() => {
          const res = comparisonResults.result;
          const files = Object.keys(res);
          if (files.length < 2) return null;
          const [f1, f2] = files;

          return (
            <Box>
              <Typography variant="h5" gutterBottom>
                Comparison Results
              </Typography>

              <table
                style={{
                  width: "100%",
                  borderCollapse: "collapse",
                  background: "#f4f4f4",
                  borderRadius: 8,
                  overflow: "hidden",
                }}
              >
                <thead style={{ background: "#1976D2", color: "#fff" }}>
                  <tr>
                    {["Metric", "Calendar 1", "Calendar 2", "Difference"].map(
                      (h) => (
                        <th
                          key={h}
                          style={{
                            padding: 12,
                            textAlign: "left",
                            borderBottom: "2px solid #ddd",
                          }}
                        >
                          {h}
                        </th>
                      )
                    )}
                  </tr>
                </thead>
                <tbody>
                  {Object.keys(res[f1]).map((metric, i) => {
                    const v1 = res[f1][metric];
                    const v2 = res[f2][metric];
                    const diff = v2 - v1;
                    return (
                      <tr
                        key={metric}
                        style={{
                          background: i % 2 ? "#fff" : "#f9f9f9",
                          borderBottom: "1px solid #ddd",
                        }}
                      >
                        <td style={{ padding: 12, display: "flex", gap: 8 }}>
                          <Tooltip
                            title={
                              metricInfo[metric]?.description ||
                              "No description"
                            }
                            arrow
                          >
                            <span style={{ display: "flex", gap: 4 }}>
                              {metricInfo[metric]?.label || metric}
                              <HelpOutlineIcon fontSize="small" />
                            </span>
                          </Tooltip>
                        </td>
                        <td style={{ padding: 12 }}>{v1}</td>
                        <td style={{ padding: 12 }}>{v2}</td>
                        <td
                          style={{
                            padding: 12,
                            color: diff === 0 ? "#1976D2" : "#f44336",
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
          );
        })()}
      </div>
    </div>
  );
}
