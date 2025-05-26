import React, { useEffect, useState, useRef } from "react";
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
    label: "E→M Failures",
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
  const [comparisonResults, setComparisonResults] = useState({ result: {} });
  const [error, setError] = useState(null);
  const reqToCalRef = useRef({});

  useEffect(() => {
    const socket = new SockJS("http://localhost:8081/ws");
    const stompClient = new Client({
      webSocketFactory: () => socket,
      debug: (str) => console.log("STOMP debug:", str),
      onConnect: () => {
        console.log("WebSocket connected");
        stompClient.subscribe("/topic/comparison/all", (msg) => {
          let data;
          try {
            data = JSON.parse(msg.body);
          } catch {
            setError("Invalid data format");
            return;
          }
          const newResults = {};
          data.forEach((item) => {
            const calId = reqToCalRef.current[item.requestId];
            if (calId) {
              newResults[calId] = item.result;
            }
          });
          setComparisonResults((prev) => ({
            result: { ...prev.result, ...newResults },
          }));
        });
      },
      onStompError: (frame) => {
        console.error(frame);
        setError("WebSocket error: " + (frame.body || frame));
      },
      onWebSocketError: (err) => {
        console.error(err);
        setError("Failed to connect to WebSocket.");
      },
      onDisconnect: () => console.log("WebSocket disconnected"),
    });
    stompClient.activate();
    return () => stompClient.deactivate();
  }, []);

  useEffect(() => {
    axios
      .get("/schedules/fetch")
      .then((res) => setCalendars(res.data))
      .catch((e) => {
        console.error(e);
        setError("Error fetching calendars.");
      });
  }, []);

  const handleCompare = async () => {
    if (!selected1 || !selected2) {
      setError("Please select two calendars.");
      return;
    }
    const cal1 = calendars.find((c) => c.id === selected1);
    const cal2 = calendars.find((c) => c.id === selected2);
    if (!cal1 || !cal2) {
      setError("Please select two valid calendars.");
      return;
    }

    const toCsvString = (rows) =>
      rows.map((row) => row.join(",")).join("\n");

    const buildFd = (cal) => {
      const blob = new Blob([toCsvString(cal.data)], {
        type: "text/csv;charset=utf-8",
      });
      const fd = new FormData();
      fd.append("files", blob, `${cal.id}.csv`);
      fd.append("vacationTemplate", cal.metadata.vacationTemplateData);
      fd.append("minimunsTemplate", cal.metadata.minimunsTemplateData);
      fd.append("employees", JSON.stringify(cal.metadata.employeesTeamInfo));
      fd.append("year", String(cal.metadata.year));
      return fd;
    };

    try {
      const [res1, res2] = await Promise.all([
        axios.post("/schedules/analyze", buildFd(cal1)),
        axios.post("/schedules/analyze", buildFd(cal2)),
      ]);
      const id1 = res1.data.requestId;
      const id2 = res2.data.requestId;
      reqToCalRef.current[id1] = cal1.id;
      reqToCalRef.current[id2] = cal2.id;
      setError(null);
    } catch (e) {
      console.error(e);
      setError("Error starting comparison: " + e.message);
    }
  };

  const r1 = comparisonResults.result[selected1];
  const r2 = comparisonResults.result[selected2];

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

        {r1 && r2 && (
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
                        style={{ padding: 12, textAlign: "left" }}
                      >
                        {h}
                      </th>
                    )
                  )}
                </tr>
              </thead>
              <tbody>
                {Object.keys(r1).map((metric, i) => {
                  const v1 = r1[metric];
                  const v2 = r2[metric];
                  const diff = v2 - v1;
                  const formattedDiff =
                    metric === "shiftBalance" ||
                    metric === "twoTeamPreferenceLevel"
                      ? diff.toFixed(2)
                      : diff === 0
                      ? "Equal"
                      : `${diff > 0 ? "+" : ""}${diff}`;
                  return (
                    <tr
                      key={metric}
                      style={{
                        background: i % 2 ? "#fff" : "#f9f9f9",
                        borderBottom: "1px solid #ddd",
                      }}
                    >
                      <td
                        style={{ padding: 12, display: "flex", gap: 8 }}
                      >
                        <Tooltip
                          title={
                            metricInfo[metric]?.description ||
                            "No description"
                          }
                          arrow
                        >
                          <span
                            style={{ display: "flex", gap: 4 }}
                          >
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
                        {formattedDiff}
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
