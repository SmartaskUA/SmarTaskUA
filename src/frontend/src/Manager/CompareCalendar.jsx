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
import { inferHourGranularity, inferScheduleType } from "../utils/scheduleType";
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
      "Total variance between actual and target vacation days for all employees.",
  },
  missedWorkDays: {
    label: "Missed Working Days",
    description:
      "Total variance between actual and target working days for all employees.",
  },
  missedTeamMin: {
    label: "Missed Minimums",
    description:
      "Each team, shift, and day, the count of employees below the required minimum staffing level.",
  },
  missedTeamIdeal: {
    label: "Missed Ideals",
    description: "Each team, shift, and day, the count of employees below the ideal staffing level.",
  },
  singleTeamViolations: {
    label: "Single Team Violations",
    description:
      "Number of employees allowed to work only one team but worked in more than one.",
  },
  shiftBalance: {
    label: "Shift Balance",
    description:
      "Percentage deviation of the most unbalanced shift distribution exhibited by any employee.",
  },
  teamSatisfactionLevel: {
    label: "Team Satisfaction Level",
    description: "Median distribution of work between primary and secondary team for employees assigned to two teams.",
  },

  // ── Hourly metrics ──────────────────────────────────────────────
  workDaysTargetDeviation: {
    label: "Work Days Target Deviation",
    description: "Total absolute deviation from the target of 223 workdays per year, summed across all employees.",
  },
  vacationDaysQuotaDeviation: {
    label: "Vacation Days Quota Deviation",
    description: "Total absolute deviation from the mandatory vacation days per year, across all employees.",
  },
  holidayWorkLimitViolations: {
    label: "Holiday Work Limit Violations",
    description: "Total number of holiday/sunday workdays beyond the legal limit of 22, summed across employees.",
  },
  consecutiveDaysViolations: {
    label: "Consecutive Days Violations",
    description: "Total count of violations where an employee worked 6 or more consecutive days without a rest day.",
  },
  minRestViolations: {
    label: "Minimum Rest Violations",
    description: "Number of shift-to-shift transitions where rest time between consecutive working days is less than 12 hours.",
  },
  preferredDayOffWorkedDays: {
    label: "Preferred Day-Off Worked Days",
    description: "Number of template `DO` days that still ended up worked. Direct KPI for objective 4.",
  },
  preferredDayOffPreservationRate: {
    label: "Preferred Day-Off Preservation",
    description: "Percentage of template `DO` days that remained off in the generated schedule.",
  },
  skillPriorityPenaltyScore: {
    label: "Skill Priority Penalty",
    description: "Weighted slot-level penalty for assigning employees to lower-priority skills. Lower is better. Direct KPI for objective 5.",
  },
  totalStaffingGap: {
    label: "Total Staffing Gap",
    description: "Total missing staff compared to required minimums across all teams, time slots and days.",
  },
  staffingRobustnessGap: {
    label: "Staffing Robustness Gap",
    description: "Total missing staff compared to synthetic ideal levels (minimum + 1) across all teams, time slots and days.",
  },
  staffingCoverageRate: {
    label: "Staffing Coverage Rate",
    description: "Percentage of time slots where the minimum staffing requirement was met (100% means all minimums were satisfied).",
  },
  totalIdealGap: {
    label: "Total Ideal Gap",
    description: "Total missing staff compared to ideal staffing levels across all teams, time slots and days.",
  },
  excessStaffing: {
    label: "Excess Staffing",
    description: "Total extra staff assigned beyond required minimums across all teams, time slots and days.",
  },
  weightedMinimumCoverageRate: {
    label: "Weighted Minimum Coverage",
    description: "Fulfilled required headcount divided by total required headcount across all 30-minute team slots.",
  },
  criticalUnderfilledPeriods: {
    label: "Critical Underfilled Slots",
    description: "Count of 30-minute date, team, slot cells where actual coverage is below the required minimum.",
  },
  maxPeriodShortage: {
    label: "Max Period Shortage",
    description: "Largest single shortage found in any date, team, work-period cell.",
  },
  totalMinimumGap: {
    label: "Total Minimum Gap",
    description: "Total missing headcount across all required 30-minute team slots.",
  },
  totalOverstaff: {
    label: "Total Overstaff",
    description: "Total surplus headcount above minimum requirements across all required 30-minute team slots.",
  },
  intraDayTeamSwitches: {
    label: "Intra-Day Team Switches",
    description: "Number of times employees switch teams between consecutive assigned segments inside the same day.",
  },
  fragmentedWorkDays: {
    label: "Fragmented Work Days",
    description: "Count of employee-days with more than one assigned segment.",
  },
  primaryTeamUtilizationRate: {
    label: "Primary Team Utilization",
    description: "Share of assigned hours worked in each employee's strongest-ranked team.",
  },
  nonPrimaryTeamHours: {
    label: "Non-Primary Team Hours",
    description: "Total assigned hours worked outside each employee's strongest-ranked team.",
  },
  durationComplianceRate: {
    label: "Duration Compliance",
    description: "Share of employee-days that respect the daily duration or exact time rule defined in schedule_input.csv.",
  },
  demandedHoursComplianceRate: {
    label: "Demanded Hours Compliance",
    description: "Share of working-rule employee-days where assigned hours exactly match the hours requested in schedule_input.csv.",
  },
  availabilityViolations: {
    label: "Availability Violations",
    description: "Count of employee-days where the generated schedule violates the employee's stated schedule_input rule.",
  },
};

const sisqualHourlyMetrics = [
  "weightedMinimumCoverageRate",
  "criticalUnderfilledPeriods",
  "maxPeriodShortage",
  "totalMinimumGap",
  "totalOverstaff",
  "preferredDayOffWorkedDays",
  "preferredDayOffPreservationRate",
  "skillPriorityPenaltyScore",
  "primaryTeamUtilizationRate",
  "durationComplianceRate",
  "demandedHoursComplianceRate",
  "consecutiveDaysViolations",
  "minRestViolations",
  "availabilityViolations",
];

const percentMetrics = new Set([
  "shiftBalance",
  "teamSatisfactionLevel",
  "staffingCoverageRate",
  "weightedMinimumCoverageRate",
  "primaryTeamUtilizationRate",
  "durationComplianceRate",
  "demandedHoursComplianceRate",
  "preferredDayOffPreservationRate",
]);

const higherIsBetter = new Set([
  "staffingCoverageRate",
  "teamSatisfactionLevel",
  "shiftBalance",
  "weightedMinimumCoverageRate",
  "primaryTeamUtilizationRate",
  "durationComplianceRate",
  "demandedHoursComplianceRate",
  "preferredDayOffPreservationRate",
]);

export default function CompareCalendar() {
  const [calendars, setCalendars] = useState([]);
  const [selected1, setSelected1] = useState("");
  const [selected2, setSelected2] = useState("");
  const [comparisonResults, setComparisonResults] = useState({ result: {} });
  const [error, setError] = useState(null);
  const reqToCalRef = useRef({});

  useEffect(() => {
    const socket = new SockJS(`${BaseUrl}/ws`);
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
      .get(`${BaseUrl}/schedules/fetch`)
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
      fd.append("vacationTemplate", cal.metadata.vacationTemplateName || "");
      fd.append("minimunsTemplate", cal.metadata.minimunsTemplateName || "");
      fd.append("employees", JSON.stringify(cal.metadata.employeesTeamInfo));
      fd.append("year", String(cal.metadata.year));
      const scheduleType = inferScheduleType(cal.metadata);
      if (scheduleType) {
        fd.append("scheduleType", scheduleType);
        if (scheduleType === "Horas") {
          fd.append("hourGranularity", inferHourGranularity(cal.metadata));
        }
      }
      return fd;
    };

    try {
      const [res1, res2] = await Promise.all([
        axios.post(`${BaseUrl}/schedules/analyze`, buildFd(cal1)),
        axios.post(`${BaseUrl}/schedules/analyze`, buildFd(cal2)),
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

  const cal1 = calendars.find((c) => c.id === selected1);
  const cal2 = calendars.find((c) => c.id === selected2);

  const isSisqualHourly =
    [r1, r2].some((r) =>
      r && (
        r.weightedMinimumCoverageRate !== undefined ||
        r.preferredDayOffWorkedDays !== undefined ||
        Array.isArray(r.teamCoverageBreakdown)
      )
    );

  const isHourly =
    inferScheduleType(cal1?.metadata) === "Horas" ||
    inferScheduleType(cal2?.metadata) === "Horas" ||
    [r1, r2].some((r) =>
      r && (
        r.totalStaffingGap !== undefined ||
        r.excessStaffing !== undefined ||
        r.workDaysTargetDeviation !== undefined
      )
    );

  const orderedMetrics = isSisqualHourly
    ? sisqualHourlyMetrics
    : isHourly
    ? [
        "workDaysTargetDeviation",
        "vacationDaysQuotaDeviation",
        "holidayWorkLimitViolations",
        "consecutiveDaysViolations",
        "minRestViolations",
        "totalStaffingGap",
        "staffingRobustnessGap",
        "staffingCoverageRate",
        "totalIdealGap",
        "excessStaffing",
      ]
    : [
        "missedWorkDays",
        "missedVacationDays",
        "workHolidays",
        "tmFails",
        "consecutiveDays",
        "singleTeamViolations",
        "missedTeamMin",
        "shiftBalance",
        "missedTeamIdeal",
        "teamSatisfactionLevel",
      ];

  return (
    <div className="admin-container">
      <Sidebar_Manager />
      <div className="main-content" style={{ marginRight: 24 }}>
        <Typography variant="h4" gutterBottom>
          Compare Schedules
        </Typography>

        {error && (
          <Typography color="error" gutterBottom>{error}</Typography>
        )}

        <Box display="flex" alignItems="center" gap={2} mb={4}>
          {[{ label: "Schedule 1", value: selected1, set: setSelected1 },
            { label: "Schedule 2", value: selected2, set: setSelected2 }]
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
                  <th style={{ padding: 12, textAlign: "left" }}>Schedule 1</th>
                  <th style={{ padding: 12, textAlign: "left" }}>Schedule 2</th>
                  <th style={{ padding: 12, textAlign: "left" }}>Difference</th>
                </tr>
              </thead>
              <tbody>
                {orderedMetrics.map((metric, i) => {
                  const raw1 = r1[metric];
                  const raw2 = r2[metric];
                  const isNull1 = raw1 === null || raw1 === undefined;
                  const isNull2 = raw2 === null || raw2 === undefined;
                  const val1 = isNull1 ? 0 : raw1;
                  const val2 = isNull2 ? 0 : raw2;
                  const diff = val2 - val1;
                  const isPercentage = percentMetrics.has(metric);

                  const normalize = (v) => metric === "shiftBalance" ? parseFloat((v * 2).toFixed(2)) : v;

                  const displayVal = (v, isNullVal) => {
                    if (isNullVal) return "N/A";
                    return isPercentage ? `${parseFloat(normalize(v)).toFixed(2)}%` : v;
                  };
                  const normalizedDiff = metric === "shiftBalance" ? parseFloat((diff * 2).toFixed(2)) : diff;
                  const diffDisplay = (isNull1 || isNull2) ? "N/A" :
                    normalizedDiff === 0 ? "Equal" :
                    isPercentage ? `${normalizedDiff > 0 ? "+" : ""}${parseFloat(normalizedDiff).toFixed(2)}%` : `${diff > 0 ? "+" : ""}${diff}`;

                  const valueColor = (val, isNullVal) => {
                    if (isNullVal || isPercentage) return "#000";
                    if (val > 0) return "#d32f2f";
                    if (val < 0) return "#2e7d32";
                    return "#2e7d32";
                  };

                  const diffColor = () => {
                    if (diffDisplay === "N/A" || diffDisplay === "Equal") return "#000";
                    const positive = diff > 0;
                    const good = higherIsBetter.has(metric) ? positive : !positive;
                    return good ? "#2e7d32" : "#d32f2f";
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
                      <td style={{ padding: 12, color: valueColor(val1, isNull1) }}>{displayVal(val1, isNull1)}</td>
                      <td style={{ padding: 12, color: valueColor(val2, isNull2) }}>{displayVal(val2, isNull2)}</td>
                      <td style={{ padding: 12, color: diffColor() }}>{diffDisplay}</td>
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
