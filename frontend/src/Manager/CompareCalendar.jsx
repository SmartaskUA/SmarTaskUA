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
  Collapse,
  Table,
  TableHead,
  TableRow,
  TableCell,
  TableBody,
} from "@mui/material";
import Sidebar_Manager from "../components/Sidebar_Manager";
import SockJS from "sockjs-client";
import { Client } from "@stomp/stompjs";
import axios from "axios";
import HelpOutlineIcon from "@mui/icons-material/HelpOutline";
import BaseUrl from "../components/BaseUrl";

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
  const [comparisonResults, setComparisonResults] = useState(null);
  const [error, setError] = useState(null);
  const [rawComparisonData, setRawComparisonData] = useState(null);

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

  const renderTwoTeamShiftTable = (dist1, dist2) => {
    const employees = Array.from(new Set([...Object.keys(dist1), ...Object.keys(dist2)]));
    return (
      <Box mt={4}>
        <Typography variant="h6" gutterBottom>
          Two-Team Shift Distribution
        </Typography>
        <Table>
          <TableHead>
            <TableRow>
              <TableCell>Employee ID</TableCell>
              <TableCell>Team A (Cal 1)</TableCell>
              <TableCell>Team B (Cal 1)</TableCell>
              <TableCell>Team A (Cal 2)</TableCell>
              <TableCell>Team B (Cal 2)</TableCell>
            </TableRow>
          </TableHead>
          <TableBody>
            {employees.map((emp) => (
              <TableRow key={emp}>
                <TableCell>{emp}</TableCell>
                <TableCell>{dist1[emp]?.teamA_shifts ?? 0}</TableCell>
                <TableCell>{dist1[emp]?.teamB_shifts ?? 0}</TableCell>
                <TableCell>{dist2[emp]?.teamA_shifts ?? 0}</TableCell>
                <TableCell>{dist2[emp]?.teamB_shifts ?? 0}</TableCell>
              </TableRow>
            ))}
          </TableBody>
        </Table>
      </Box>
    );
  };

  // antes do return
  const orderedMetrics = [
    "missedWorkDays",
    "missedVacationDays",
    "workHolidays",
    "tmFails",
    "consecutiveDays",
    "singleTeamViolations",
    "missedTeamMin",
    "shiftBalance",
    "twoTeamPreferenceViolations",
  ];


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
                    {["KPIs", "Calendar 1", "Calendar 2", "Difference"].map(
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
                  {orderedMetrics.map((metric, i) => {
                    const v1 = res[f1][metric];
                    const v2 = res[f2][metric];
                    const diff = v2 - v1;

                    const isPercentage = metric === "shiftBalance" || metric === "twoTeamPreferenceViolations";
                    const getColor = (val) =>
                      isPercentage ? "#212121" : val > 0 ? "#d32f2f" : "#2e7d32";

                    return (
                      <tr
                        key={metric}
                        style={{
                          background: i % 2 ? "#fff" : "#f9f9f9",
                          borderBottom: "1px solid #ddd",
                        }}
                      >
                        <td style={{ padding: 12, display: "flex", gap: 8 }}>
                          <Tooltip title={metricInfo[metric]?.description || "No description"} arrow>
                            <span style={{ display: "flex", gap: 4 }}>
                              {metricInfo[metric]?.label || metric}
                              <HelpOutlineIcon fontSize="small" />
                            </span>
                          </Tooltip>
                        </td>
                        <td style={{ padding: 12, color: getColor(v1) }}>
                          {isPercentage ? `${v1}%` : v1}
                        </td>
                        <td style={{ padding: 12, color: getColor(v2) }}>
                          {isPercentage ? `${v2}%` : v2}
                        </td>
                        <td style={{ padding: 12, color: "#1976D2" }}>
                          {diff === 0 ? "Equal" : `${diff > 0 ? "+" : ""}${diff}`}
                        </td>
                      </tr>
                    );
                  })}
                </tbody>
              </table>
              {res[f1].twoTeamShiftDistribution && res[f2].twoTeamShiftDistribution &&
                renderTwoTeamShiftTable(res[f1].twoTeamShiftDistribution, res[f2].twoTeamShiftDistribution)}
            </Box>
          );
        })()}
      </div>
    </div>
  );
}
