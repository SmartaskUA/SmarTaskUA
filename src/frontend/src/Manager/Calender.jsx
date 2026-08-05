import React, { useEffect, useMemo, useRef, useState } from "react";
import { useParams } from "react-router-dom";
import axios from "axios";
import Sidebar_Manager from "../components/Sidebar_Manager";
import CalendarTable from "../components/manager/CalendarTable";
import CalendarHeader from "../components/manager/CalendarHeader";
import KPIReport from "../components/manager/KPIReport";
import SisqualKPIReport from "./SisqualKPIReport";
import BaseUrl from "../components/BaseUrl";
import MetadataInfo from "../components/manager/MetadataInfo";
import MinimumsTemplate from "../components/manager/MinimumsTemplate";
import ProblemDemandTable from "../components/manager/ProblemDemandTable";
import SockJS from "sockjs-client";
import { Client } from "@stomp/stompjs";
import { inferHourGranularity, inferScheduleType } from "../utils/scheduleType";
import {
  buildMonthOptions,
  buildScheduleColumns,
  inferPreferredMonth,
} from "../utils/scheduleCalendar";
import { Box, Button, Paper, Typography } from "@mui/material";

const Calendar = () => {
  const [data, setData] = useState([]);
  const [selectedMonth, setSelectedMonth] = useState(1);
  const { calendarId } = useParams();
  const [metadata, setMetadata] = useState(null);
  const [kpiSummary, setKpiSummary] = useState(null);
  const [holidayMap, setHolidayMap] = useState({});
  const reqToCalRef = useRef({});
  const [elapsed_time, setElapsedTime] = useState(null);
  const [viewMode, setViewMode] = useState("schedule");
  const [coverageMode, setCoverageMode] = useState("min");
  const [hasSisqualExport, setHasSisqualExport] = useState(false);
  const [isExportingSisqual, setIsExportingSisqual] = useState(false);
  const resolvedYear = Number(metadata?.year) || new Date().getFullYear();
  const scheduleType = inferScheduleType(metadata);
  const scheduleColumns = useMemo(
    () => buildScheduleColumns(data?.[0], resolvedYear),
    [data, resolvedYear]
  );
  const monthOptions = useMemo(
    () => buildMonthOptions(scheduleColumns, resolvedYear),
    [scheduleColumns, resolvedYear]
  );
  const monthColumns = useMemo(
    () => scheduleColumns.filter((column) => column.month === selectedMonth),
    [scheduleColumns, selectedMonth]
  );

  useEffect(() => {
    const baseUrl = BaseUrl;
    axios.get(`${baseUrl}/schedules/fetch/${calendarId}`)
      .then((response) => {
        const responseData = response.data;
        if (responseData) {
          const scheduleData = responseData.data;
          const elapsed_time = responseData?.elapsed_time || null;
          setData(scheduleData);
          setMetadata(responseData.metadata);
          // If KPIs were produced server-side (e.g. Sisqual) they may be
          // present in `metadata.analysis.kpis` — load them into state.
          if (responseData.metadata?.analysis?.kpis) {
            setKpiSummary(responseData.metadata.analysis.kpis);
          }
          setElapsedTime(elapsed_time);
          setHasSisqualExport(Boolean(responseData.sisqualExport));
          console.log("Elapsed time:", elapsed_time);
          fetchNationalHolidays(responseData.metadata?.year || new Date().getFullYear());
        }
      })
      .catch(console.error);
  }, [calendarId]);

  useEffect(() => {
    if (!data?.length || !metadata || !monthColumns.length) {
      return;
    }
    analyzeScheduleViaWebSocket(data, metadata, monthColumns);
  }, [data, metadata, monthColumns, calendarId]);

  useEffect(() => {
    if (!monthOptions.length) {
      return;
    }
    if (!monthOptions.some((month) => month.value === selectedMonth)) {
      setSelectedMonth(inferPreferredMonth(data, scheduleColumns));
    }
  }, [monthOptions, selectedMonth, data, scheduleColumns]);

  useEffect(() => {
    const socket = new SockJS(`${BaseUrl}/ws`);
    const stompClient = new Client({
      webSocketFactory: () => socket,
      onConnect: () => {
        stompClient.subscribe("/topic/comparison/all", (msg) => {
          try {
            const payload = JSON.parse(msg.body);
            const items = Array.isArray(payload) ? payload : [payload];
            items.forEach((item) => {
              if (!item || !item.requestId) {
                return;
              }
              const mappedCalId = reqToCalRef.current[item.requestId];
              if (mappedCalId === calendarId && item.result) {
                console.log("KPI recebido via WebSocket:", item.result);
                setKpiSummary((prev) => {
                  const prevIsSisqualHourly =
                    prev?.weightedMinimumCoverageRate !== undefined ||
                    Array.isArray(prev?.teamCoverageBreakdown) ||
                    prev?.["Total_Shortage"] !== undefined;
                  const nextIsSisqualHourly =
                    item.result?.weightedMinimumCoverageRate !== undefined ||
                    Array.isArray(item.result?.teamCoverageBreakdown);
                  if (prevIsSisqualHourly && !nextIsSisqualHourly) {
                    console.log("KPIs Sisqual já presentes — ignorando WebSocket.");
                    return prev;
                  }
                  return item.result;
                });
              }
            });
          } catch (e) {
            console.error("Erro a processar resultado via WebSocket:", e);
          }
        });
      },
      onStompError: (frame) => {
        console.error("Erro STOMP:", frame);
      },
    });
    stompClient.activate();
    return () => stompClient.deactivate();
  }, [calendarId]);

  const buildMonthScopedScheduleData = (scheduleData, columns) => {
    if (!Array.isArray(scheduleData) || !scheduleData.length || !columns?.length) {
      return scheduleData;
    }
    const selectedIndexes = columns.map((column) => column.index + 1);
    return scheduleData.map((row, rowIndex) => {
      if (!Array.isArray(row)) return row;
      const firstCell = rowIndex === 0 ? "employee_id" : row[0];
      return [firstCell, ...selectedIndexes.map((index) => row[index] ?? "")];
    });
  };

  const analyzeScheduleViaWebSocket = async (scheduleData, metadata, columns) => {
    try {
      const hasVacationTemplate =
        Array.isArray(metadata?.vacationTemplateData) &&
        metadata.vacationTemplateData.length > 0;
      const hasMinimumsTemplate =
        Array.isArray(metadata?.minimunsTemplateData) &&
        metadata.minimunsTemplateData.length > 0;
      const hasProblemBundle = Boolean(metadata?.problemPath);
      const shouldUseLegacyInputs = hasVacationTemplate && hasMinimumsTemplate;

      if (!shouldUseLegacyInputs && !hasProblemBundle) {
        console.info("Skipping KPI analysis because this schedule has no analysis inputs.");
        return;
      }

      // Server-computed KPIs (stored in metadata.analysis.kpis) cover the full
      // schedule and are already loaded into state. Don't wipe them — the
      // WebSocket re-analysis is month-scoped and would overwrite a richer result.
      if (metadata?.analysis?.kpis) {
        console.info("Skipping WebSocket KPI re-analysis: server-computed KPIs already present.");
        return;
      }

      const scopedScheduleData = buildMonthScopedScheduleData(scheduleData, columns);
      setKpiSummary(null);

      const toCsvString = (rows) => rows.map((row) => row.join(",")).join("\n");
      const blob = new Blob([toCsvString(scopedScheduleData)], {
        type: "text/csv;charset=utf-8",
      });

      const fd = new FormData();
      fd.append("files", blob, `${calendarId}.csv`); 
      fd.append("vacationTemplate", shouldUseLegacyInputs ? metadata?.vacationTemplateName || "" : "");
      fd.append("minimunsTemplate", shouldUseLegacyInputs ? metadata?.minimunsTemplateName || "" : "");
      fd.append("employees", JSON.stringify(metadata?.employeesTeamInfo || []));
      fd.append("year", String(metadata?.year || new Date().getFullYear()));
      if (metadata?.rules) {
        fd.append("rules", JSON.stringify(metadata.rules));
      }
      if (hasProblemBundle) {
        fd.append("problemPath", metadata.problemPath);
      }
      const scheduleType = inferScheduleType(metadata);
      if (scheduleType) {
        fd.append("scheduleType", scheduleType);
        if (scheduleType === "Horas") {
          fd.append("hourGranularity", inferHourGranularity(metadata));
        }
      }

      const res = await axios.post(`${BaseUrl}/schedules/analyze`, fd);
      console.log("🛰️ Enviado para análise com requestId:", res.data.requestId);
      reqToCalRef.current[res.data.requestId] = calendarId;
    } catch (e) {
      console.error("Erro ao enviar CSV para análise:", e);
    }
  };

  const fetchNationalHolidays = async (year) => {
    try {
      const res = await axios.get(`https://date.nager.at/api/v3/PublicHolidays/${year}/PT`);
      const holidays = {};
      res.data
        .filter((h) => h.counties === null)
        .forEach((holiday) => {
          const date = new Date(holiday.date);
          const month = date.getMonth() + 1;
          const day = date.getDate();
          if (!holidays[month]) holidays[month] = [];
          holidays[month].push(day);
        });
      setHolidayMap(holidays);
    } catch (err) {
      console.error("Failed to fetch national holidays:", err);
    }
  };

  const downloadCSV = () => {
    const csvContent = data.map((row) => row.join(",")).join("\n");
    const blob = new Blob([csvContent], { type: "text/csv" });
    const link = document.createElement("a");
    link.href = URL.createObjectURL(blob);
    link.download = `${calendarId}.csv`;
    link.click();
  };

  const downloadSisqualExport = async () => {
    setIsExportingSisqual(true);
    try {
      const response = await axios.get(`${BaseUrl}/schedules/fetch/${calendarId}/sisqual-export`);
      const blob = new Blob([JSON.stringify(response.data, null, 2)], { type: "application/json" });
      const link = document.createElement("a");
      link.href = URL.createObjectURL(blob);
      link.download = `${calendarId}_sisqual_import.json`;
      link.click();
    } catch (err) {
      console.error("Failed to download Sisqual export:", err);
    } finally {
      setIsExportingSisqual(false);
    }
  };

  const formatElapsedTime = (seconds) => {
  if (!seconds && seconds !== 0) return null;
  if (seconds < 60) return `${seconds.toFixed(2)} sec`;
  const mins = Math.floor(seconds / 60);
  const secs = Math.round(seconds % 60);
  return `${mins} min${secs > 0 ? ` ${secs} sec` : ""}`;
};
  const isHourly = scheduleType === "Horas";
  const missingMinimums = isHourly
    ? kpiSummary?.hourlyCoverageGaps ?? kpiSummary?.missedTeamMin ?? null
    : kpiSummary?.missedTeamMin ?? kpiSummary?.hourlyCoverageGaps ?? null;
  const missingIdeals = kpiSummary?.missedTeamIdeal ?? null;
  const hasIdeals =
    Array.isArray(metadata?.minimunsTemplateData) &&
    metadata.minimunsTemplateData.some((row) =>
      row?.some((cell) => String(cell || "").toLowerCase().includes("ideal"))
    );
  const coverageView = hasIdeals ? coverageMode : "min";
  const missingLabel =
    coverageView === "ideal" ? "Missing ideals" : "Missing minimums";
  const missingValue =
    coverageView === "ideal" ? missingIdeals : missingMinimums;
  const hasLegacyAnalysisInputs =
    Array.isArray(metadata?.vacationTemplateData) &&
    metadata.vacationTemplateData.length > 0 &&
    Array.isArray(metadata?.minimunsTemplateData) &&
    metadata.minimunsTemplateData.length > 0;
  const hasProblemAnalysisInputs = Boolean(metadata?.problemPath);
  const hasAnalysisInputs = hasLegacyAnalysisInputs || hasProblemAnalysisInputs;
  const hasProblemDemandData =
    Array.isArray(metadata?.problemDemandData) &&
    metadata.problemDemandData.length > 0;
  const hasViewToggle =
    (Array.isArray(metadata?.minimunsTemplateData) &&
      metadata.minimunsTemplateData.length > 0) ||
    hasProblemDemandData;
  const toggleViewLabel = hasProblemDemandData ? "View Demand" : "View Minimums";

  return (
    <div className="admin-container" style={{ display: "flex", height: "100vh" }}>
      <Sidebar_Manager />
      <div className="main-content" style={{ flex: 1, overflowY: "auto", padding: "20px", boxSizing: "border-box", marginRight: "20px" }}>
        <CalendarHeader
          months={monthOptions}
          selectedMonth={selectedMonth}
          setSelectedMonth={setSelectedMonth}
          downloadCSV={downloadCSV}
          onDownloadSisqualExport={hasSisqualExport ? downloadSisqualExport : null}
          isExportingSisqual={isExportingSisqual}
          calendarTitle={metadata?.scheduleName || "Work Calendar"}
          algorithmName={metadata?.algorithmType}
          scheduleType={scheduleType}
          viewMode={viewMode}
          onToggleView={
            hasViewToggle
              ? () => setViewMode((prev) => (prev === "minimums" ? "schedule" : "minimums"))
              : null
          }
          toggleViewLabel={toggleViewLabel}
        />

        {elapsed_time != null && (
          <div
            style={{
              fontSize: "1rem",
              color: "#555",
              margin: "10px 0 20px 5px",
              display: "flex",
              alignItems: "center",
              gap: "6px",
            }}
          >
            <span style={{ fontSize: "1.2rem" }}>⏱</span>
            <span>
              Generated in <strong>{formatElapsedTime(elapsed_time)}</strong>
            </span>
          </div>
        )}

        {!hasAnalysisInputs && (
          <Paper
            elevation={0}
            sx={{
              p: 1.5,
              mt: 1,
              mb: 2,
              borderRadius: 2,
              border: "1px solid #e2e8f0",
              backgroundColor: "#f8fafc",
            }}
          >
            <Typography variant="body2" color="text.secondary">
              KPI analysis is not available for this schedule bundle yet.
            </Typography>
          </Paper>
        )}

        {viewMode === "schedule" ? (
          <CalendarTable
            data={data}
            monthColumns={monthColumns}
            holidayMap={holidayMap}
            scheduleType={scheduleType}
            employees={metadata?.employeesTeamInfo || []}
          />
        ) : hasProblemDemandData ? (
          <ProblemDemandTable
            demandData={metadata?.problemDemandData || []}
            workPeriods={metadata?.problemWorkPeriods || []}
            teams={metadata?.problemTeams || []}
            monthColumns={monthColumns}
            holidayMap={holidayMap}
            scheduleData={data}
          />
        ) : (
          <Box mt={3}>
            <Paper
              elevation={0}
              sx={{
                p: 2,
                mb: 2,
                borderRadius: 2,
                border: "1px solid",
                borderColor: "divider",
                backgroundColor: "#f8fafc",
              }}
            >
              <Box
                display="flex"
                alignItems="center"
                justifyContent="space-between"
                flexWrap="wrap"
              >
                <Typography variant="subtitle1" fontWeight="bold" gutterBottom>
                  {coverageView === "ideal" ? "Ideals Summary" : "Minimums Summary"}
                </Typography>
                {hasIdeals && (
                  <Box display="flex" gap={1} mb={1}>
                    <Button
                      variant={coverageMode === "min" ? "contained" : "outlined"}
                      size="small"
                      onClick={() => setCoverageMode("min")}
                    >
                      Minimums
                    </Button>
                    <Button
                      variant={coverageMode === "ideal" ? "contained" : "outlined"}
                      size="small"
                      onClick={() => setCoverageMode("ideal")}
                    >
                      Ideals
                    </Button>
                  </Box>
                )}
              </Box>
              <Typography variant="body2">
                {missingLabel}:{" "}
                {missingValue !== null ? missingValue : "Loading KPI results..."}
              </Typography>
              {coverageView === "min" &&
                isHourly &&
                kpiSummary?.hourlyOverstaff !== undefined && (
                  <Typography variant="body2" sx={{ mt: 0.5 }}>
                    Hourly overstaff: {kpiSummary.hourlyOverstaff}
                  </Typography>
                )}
            </Paper>
            <MinimumsTemplate
              name={metadata?.minimunsTemplateName || "Minimums Template"}
              data={metadata?.minimunsTemplateData || []}
              scheduleData={data}
              scheduleType={scheduleType}
              year={resolvedYear}
              mode={coverageView}
              showDiff
              selectedMonth={selectedMonth}
            />
          </Box>
        )}

        <MetadataInfo metadata={metadata} />

        {kpiSummary?.weightedMinimumCoverageRate !== undefined || Array.isArray(kpiSummary?.teamCoverageBreakdown) ? (
          <KPIReport metrics={kpiSummary || {}} scheduleType={scheduleType} />
        ) : kpiSummary?.["Total_Shortage"] !== undefined ? (
          <SisqualKPIReport kpis={kpiSummary} />
        ) : (
          <KPIReport metrics={kpiSummary || {}} scheduleType={scheduleType} />
        )}
        
      </div>
    </div>
  );
};

export default Calendar;
