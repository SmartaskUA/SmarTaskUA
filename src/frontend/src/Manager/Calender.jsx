import React, { useState, useEffect, useRef } from "react";
import { useParams } from "react-router-dom";
import axios from "axios";
import Sidebar_Manager from "../components/Sidebar_Manager";
import CalendarTable from "../components/manager/CalendarTable";
import CalendarHeader from "../components/manager/CalendarHeader";
import KPIReport from "../components/manager/KPIReport";
import BaseUrl from "../components/BaseUrl";
import MetadataInfo from "../components/manager/MetadataInfo";
import MinimumsTemplate from "../components/manager/MinimumsTemplate";
import SockJS from "sockjs-client";
import { Client } from "@stomp/stompjs";
import { inferHourGranularity, inferScheduleType } from "../utils/scheduleType";
import { Box, Button, Paper, Typography } from "@mui/material";

const Calendar = () => {
  const [data, setData] = useState([]);
  const [selectedMonth, setSelectedMonth] = useState(1);
  const [startDay, setStartDay] = useState(1);
  const [endDay, setEndDay] = useState(31);
  const [firstDayOfYear, setFirstDayOfYear] = useState(0);
  const { calendarId } = useParams();
  const [metadata, setMetadata] = useState(null);
  const [kpiSummary, setKpiSummary] = useState(null);
  const [holidayMap, setHolidayMap] = useState({});
  const reqToCalRef = useRef({});
  const [viewMode, setViewMode] = useState("schedule");
  const [coverageMode, setCoverageMode] = useState("min");

  const months = [
    "November", "December", "January", "February", "March", "April",
    "May", "June", "July", "August", "September", "October"
  ];

  const daysInMonth = [30, 31, 31, 28, 31, 30, 31, 30, 31, 31, 30, 31];

  useEffect(() => {
    setStartDay(1);
    setEndDay(daysInMonth[selectedMonth - 1]);
  }, [selectedMonth]);

  useEffect(() => {
    const baseUrl = BaseUrl;
    axios.get(`${baseUrl}/schedules/fetch/${calendarId}`)
      .then((response) => {
        const responseData = response.data;
        if (responseData) {
          const scheduleData = responseData.data;
          const year = responseData.metadata?.year || new Date().getFullYear();
          const firstDay = new Date(`2021-11-01`).getDay();
          setFirstDayOfYear(firstDay);
          setData(scheduleData);
          setMetadata(responseData.metadata);
          fetchNationalHolidays(year);
          analyzeScheduleViaWebSocket(scheduleData, responseData.metadata);
        }
      })
      .catch(console.error);
  }, [calendarId]);

  useEffect(() => {
    const socket = new SockJS(`${BaseUrl}/ws`);
    const stompClient = new Client({
      webSocketFactory: () => socket,
      onConnect: () => {
        stompClient.subscribe("/topic/comparison/all", (msg) => {
          try {
            const data = JSON.parse(msg.body);
            data.forEach(async (item) => {
              const mappedCalId = reqToCalRef.current[item.requestId];
              if (mappedCalId === calendarId) {
                console.log("✅ KPI recebido:", item.result);
                setKpiSummary(item.result);
              }
              const res = await axios.post(`${BaseUrl}/schedules/analyze`, fd);
              console.log("🛰️ Enviado para análise com requestId:", res.data.requestId);

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

  const analyzeScheduleViaWebSocket = async (scheduleData, metadata) => {
    try {
      const toCsvString = (rows) => rows.map((row) => row.join(",")).join("\n");
      const blob = new Blob([toCsvString(scheduleData)], {
        type: "text/csv;charset=utf-8",
      });

      const fd = new FormData();
      fd.append("files", blob, `${calendarId}.csv`); 
      fd.append("vacationTemplate", metadata?.vacationTemplateData || "");
      fd.append("minimunsTemplate", metadata?.minimunsTemplateData || "");
      fd.append("employees", JSON.stringify(metadata?.employeesTeamInfo || []));
      fd.append("year", String(metadata?.year || new Date().getFullYear()));
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

  const scheduleType = inferScheduleType(metadata);
  const isHourly = scheduleType === "Horas";
  const missingMinimums =
    kpiSummary?.hourlyCoverageGaps ?? kpiSummary?.missedTeamMin ?? null;
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

  return (
    <div className="admin-container" style={{ display: "flex", height: "100vh" }}>
      <Sidebar_Manager />
      <div className="main-content" style={{ flex: 1, overflowY: "auto", padding: "20px", boxSizing: "border-box", marginRight: "20px" }}>
        <CalendarHeader
          months={months}
          selectedMonth={selectedMonth}
          setSelectedMonth={setSelectedMonth}
          downloadCSV={downloadCSV}
          calendarTitle={metadata?.scheduleName || "Work Calendar"}
          algorithmName={metadata?.algorithmType}
          viewMode={viewMode}
          onToggleView={() =>
            setViewMode((prev) => (prev === "minimums" ? "schedule" : "minimums"))
          }
        />

        {viewMode === "schedule" ? (
          <CalendarTable
            data={data}
            selectedMonth={selectedMonth}
            daysInMonth={daysInMonth}
            startDay={startDay}
            endDay={endDay}
            firstDayOfYear={firstDayOfYear}
            holidayMap={holidayMap}
            scheduleType={scheduleType}
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
              mode={coverageView}
              showDiff
              selectedMonth={selectedMonth}
            />
          </Box>
        )}

        <MetadataInfo metadata={metadata} />
        <KPIReport metrics={kpiSummary || {}} scheduleType={scheduleType} />
      </div>
    </div>
  );
};

export default Calendar;
