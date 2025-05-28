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
  tmFails: {
    label: "Afternoon-Morning Sequence",
    description:
      "Number of times an employee works in an afternoon shift followed by a morning shift in the day after.",
  },
  consecutiveDays: {
    label: "Consecutive Work-Day Violations",
    description:
      "Number of times employees exceeded the maximum allowed run of five consecutive working days.",
  },
  workHolidays: {
    label: "Holidays and Sundays Work Days",
    description:
      "Number of work days falling on holidays and Sundays that exceed the predefined threshold.",
  },
  missedVacationDays: {
    label: "Missed Vacation Days",
    description:
      "Total variance between actual and target vacation days for all employees, expressed as the number of days above or below the target.",
  },
  missedWorkDays: {
    label: "Missed Working Days",
    description:
      "Total variance between actual and target working days for all employees, expressed as the number of days above or below the target.",
  },
  missedTeamMin: {
    label: "Missed Minimums",
    description:
      "Each team, shift, and day, the count of employees below the required minimum staffing level.",
  },
  singleTeamViolations: {
    label: "Single Team Violations",
    description:
      "Number of employees that are allowed to work for only one team and end up working for more than one.",
  },
  shiftBalance: {
    label: "Shift Balance",
    description:
      "Percentage deviation of the most unbalanced shift distribution exhibited by any employee.",
  },
  twoTeamPreferenceViolations: {
    label: "Two Team Preference Level",
    description:
      "Among employees assigned to exactly two teams, the median distribution of work between their primary (preferred) team and their secondary team.",
  },
  twoTeamShiftDistribution: {
    label: "Two-Team Shift Distribution",
    description:
      "Breakdown of shifts between team A and B by employee.",
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
      onConnect: () => {
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
    });
    stompClient.activate();
    return () => stompClient.deactivate();
  }, []);

  useEffect(() => {
    axios
      .get("/schedules/fetch")
      .then((res) => setCalendars(res.data))
      .catch(() => setError("Error fetching calendars."));
  }, []);

  const handleCompare = async () => {
    if (!selected1 || !selected2) {
      setError("Please select two calendars.");
      return;
    }

    const cal1 = calendars.find((c) => c.id === selected1);
    const cal2 = calendars.find((c) => c.id === selected2);
    if (!cal1 || !cal2) return;

    const toCsvString = (rows) => rows.map((row) => row.join(",")).join("\n");

    const buildFd = (cal) => {
      const blob = new Blob([toCsvString(cal.data)], { type: "text/csv;charset=utf-8" });
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
      reqToCalRef.current[res1.data.requestId] = cal1.id;
      reqToCalRef.current[res2.data.requestId] = cal2.id;
      setError(null);
    } catch (e) {
      setError("Error starting comparison: " + e.message);
    }
  };

  const r1 = comparisonResults.result[selected1];
  const r2 = comparisonResults.result[selected2];

  const orderedMetrics = [
    "missedWorkDays",
    "missedVacationDays",
    "workHolidays",
    "tmFails",
    "consecutiveDays",
    "singleTeamViolations",
    "missedTeamMin",
    "shiftBalance",
    "twoTeamPreferenceViolations"
  ];

  return (
    <div className="admin-container">
      <Sidebar_Manager />
      <div className="main-content" style={{ marginRight: 24 }}>
        <Typography variant="h4" gutterBottom>
          Compare Calendars
        </Typography>

        {error && (
          <Typography color="error" gutterBottom>{error}</Typography>
        )}

        <Box display="flex" alignItems="center" gap={2} mb={4}>
          {[{ label: "Calendar 1", value: selected1, set: setSelected1 },
            { label: "Calendar 2", value: selected2, set: setSelected2 }]
            .map(({ label, value, set }, idx) => (
              <FormControl sx={{ minWidth: 300 }} key={idx}>
                <InputLabel>{label}</InputLabel>
                <Select value={value} label={label} onChange={(e) => set(e.target.value)}>
                  {calendars.filter(c => c.id !== (idx === 0 ? selected2 : selected1))
                    .map(c => <MenuItem key={c.id} value={c.id}>{c.title}</MenuItem>)}
                </Select>
              </FormControl>
            ))}
          <Button variant="contained" onClick={handleCompare} disabled={!selected1 || !selected2}>
            Compare
          </Button>
        </Box>

        {r1 && r2 && (
          <Box>
            <Typography variant="h5" gutterBottom>Comparison Results</Typography>
            <table style={{
              width: "100%",
              borderCollapse: "collapse",
              borderRadius: 8,
              overflow: "hidden",
              background: "#fff"
            }}>
              <thead style={{ background: "#1976D2", color: "#fff" }}>
                <tr>
                  <th style={{ padding: 12, textAlign: "left" }}>KPIs</th>
                  <th style={{ padding: 12, textAlign: "left" }}>Calendar 1</th>
                  <th style={{ padding: 12, textAlign: "left" }}>Calendar 2</th>
                  <th style={{ padding: 12, textAlign: "left" }}>Difference</th>
                </tr>
              </thead>
              <tbody>
                {orderedMetrics.map((metric, i) => {
                  const val1 = r1[metric] ?? 0;
                  const val2 = r2[metric] ?? 0;
                  const diff = val2 - val1;
                  const isPercentage = metric === "shiftBalance" || metric === "twoTeamPreferenceViolations";

                  const displayVal = (v) => isPercentage ? `${parseFloat(v).toFixed(2)}%` : v;
                  const diffDisplay = diff === 0 ? "Equal" :
                    isPercentage ? `${parseFloat(diff).toFixed(2)}%` : `${diff > 0 ? "+" : ""}${diff}`;

                  const valueColor = (val) => {
                    if (isPercentage) return "#000";
                    if (val > 0) return "#d32f2f";
                    if (val < 0) return "#2e7d32";
                    return "#2e7d32";
                  };

                  return (
                    <tr key={metric} style={{ background: i % 2 ? "#fff" : "#f9f9f9" }}>
                      <td style={{ padding: 12 }}>
                        <Tooltip title={metricInfo[metric]?.description || "No description"} arrow>
                          <span style={{ display: "flex", alignItems: "center", gap: 6 }}>
                            {metricInfo[metric]?.label || metric}
                            <HelpOutlineIcon fontSize="small" />
                          </span>
                        </Tooltip>
                      </td>
                      <td style={{ padding: 12, color: valueColor(val1) }}>{displayVal(val1)}</td>
                      <td style={{ padding: 12, color: valueColor(val2) }}>{displayVal(val2)}</td>
                      <td style={{ padding: 12, color: "#1976D2" }}>{diffDisplay}</td>
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