import React, { useState, useEffect, useRef } from "react";
import { useParams } from "react-router-dom";
import axios from "axios";
import Sidebar_Manager from "../components/Sidebar_Manager";
import CalendarTable from "../components/manager/CalendarTable";
import CalendarHeader from "../components/manager/CalendarHeader";
import KPIReport from "../components/manager/KPIReport";
import BaseUrl from "../components/BaseUrl";
import MetadataInfo from "../components/manager/MetadataInfo";
import SockJS from "sockjs-client";
import { Client } from "@stomp/stompjs";

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
  const [elapsed_time, setElapsedTime] = useState(null);

  const months = [
    "January", "February", "March", "April", "May", "June",
    "July", "August", "September", "October", "November", "December"
  ];
  const daysInMonth = [31, 28, 31, 30, 31, 30, 31, 31, 30, 31, 30, 31];

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
          const firstDay = new Date(`${year}-01-01`).getDay();
          const elapsed_time = responseData?.elapsed_time || null;
          setFirstDayOfYear(firstDay);
          setData(scheduleData);
          setMetadata(responseData.metadata);
          setElapsedTime(elapsed_time);
          console.log("Elapsed time:", elapsed_time);
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
            data.forEach((item) => {
              const mappedCalId = reqToCalRef.current[item.requestId];
              if (mappedCalId === calendarId) {
                console.log("KPI recebido:", item.result);
                setKpiSummary(item.result);
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

  const formatElapsedTime = (seconds) => {
  if (!seconds && seconds !== 0) return null;
  if (seconds < 60) return `${seconds.toFixed(2)} sec`;
  const mins = Math.floor(seconds / 60);
  const secs = Math.round(seconds % 60);
  return `${mins} min${secs > 0 ? ` ${secs} sec` : ""}`;
};

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


        <CalendarTable
          data={data}
          selectedMonth={selectedMonth}
          daysInMonth={daysInMonth}
          startDay={startDay}
          endDay={endDay}
          firstDayOfYear={firstDayOfYear}
          holidayMap={holidayMap}
        />

        <MetadataInfo metadata={metadata} />
        <KPIReport metrics={kpiSummary || {}} />
      </div>
    </div>
  );
};

export default Calendar;
