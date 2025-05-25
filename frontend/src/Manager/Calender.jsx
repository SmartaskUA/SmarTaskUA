import React, { useState, useEffect } from "react";
import { useParams } from "react-router-dom";
import axios from "axios";
import Sidebar_Manager from "../components/Sidebar_Manager";
import CalendarTable from "../components/manager/CalendarTable";
import CalendarHeader from "../components/manager/CalendarHeader";
import KPIReport from "../components/manager/KPIReport";
import BaseUrl from "../components/BaseUrl";
import MetadataInfo from "../components/manager/MetadataInfo";
import { Box, Typography } from "@mui/material";
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

  const months = ["January", "February", "March", "April", "May", "June", "July", "August", "September", "October", "November", "December"];

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
          setFirstDayOfYear(firstDay);
          setData(scheduleData);
          setMetadata(responseData.metadata);
          analyzeScheduleViaWebSocket(scheduleData); // nova função com WebSocket
        }
      })
      .catch(console.error);
  }, [calendarId]);

  const analyzeScheduleViaWebSocket = (csvData) => {
    const socket = new SockJS(`${BaseUrl}/ws`);
    const stompClient = new Client({
      webSocketFactory: () => socket,
      onConnect: () => {
        stompClient.subscribe("/topic/comparison/all", (msg) => {
          try {
            const data = JSON.parse(msg.body);
            if (Array.isArray(data) && data.length > 0) {
              const result = data[0]?.result;
              if (result) {
                const firstFile = Object.keys(result)[0];
                const thisResult = result[firstFile];
                setKpiSummary(thisResult);
              }
            }
          } catch (e) {
            console.error("Erro a processar resultado via WebSocket:", e);
          }
        });

        const toCsvString = (rows) => rows.map((row) => row.join(",")).join("\n");
        const csvString = toCsvString(csvData);
        const blob1 = new Blob([csvString], { type: "text/csv;charset=utf-8" });
        const blob2 = new Blob([csvString], { type: "text/csv;charset=utf-8" });

        const fd = new FormData();
        fd.append("files", blob1, `${calendarId}-A.csv`);
        fd.append("files", blob2, `${calendarId}-B.csv`);

        axios.post(`${BaseUrl}/schedules/analyze`, fd).catch((e) => {
          console.error("Erro ao enviar CSV para análise:", e);
        });
      },
      onStompError: (frame) => {
        console.error("Erro STOMP:", frame);
      },
    });

    stompClient.activate();
  };

  const downloadCSV = () => {
    const csvContent = data.map(row => row.join(",")).join("\n");
    const blob = new Blob([csvContent], { type: "text/csv" });
    const link = document.createElement("a");
    link.href = URL.createObjectURL(blob);
    link.download = `${calendarId}.csv`;
    link.click();
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

        <CalendarTable
          data={data}
          selectedMonth={selectedMonth}
          daysInMonth={daysInMonth}
          startDay={startDay}
          endDay={endDay}
          firstDayOfYear={firstDayOfYear}
        />

        <MetadataInfo metadata={metadata} />

        <KPIReport metrics={kpiSummary || {}} />

      </div>
    </div>
  );
};

export default Calendar;
