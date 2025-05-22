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

const Calendar = () => {
  const [data, setData] = useState([]);
  const [selectedMonth, setSelectedMonth] = useState(1);
  const [startDay, setStartDay] = useState(1);
  const [endDay, setEndDay] = useState(31);
  const [firstDayOfYear, setFirstDayOfYear] = useState(0);
  const { calendarId } = useParams();
  const [metadata, setMetadata] = useState(null);
  const [kpiSummary, setKpiSummary] = useState(null);

  const months = [
    "Janeiro", "Fevereiro", "Março", "Abril", "Maio", "Junho",
    "Julho", "Agosto", "Setembro", "Outubro", "Novembro", "Dezembro"
  ];
  const daysInMonth = [31, 28, 31, 30, 31, 30, 31, 31, 30, 31, 30, 31];

  useEffect(() => {
    setStartDay(1);
    setEndDay(daysInMonth[selectedMonth - 1]);
  }, [selectedMonth]);

  const analyzeScheduleViaAPI = async (csvData) => {
    try {
      const toCsvString = (rows) => rows.map((row) => row.join(",")).join("\n");
      const blob = new Blob([toCsvString(csvData)], {
        type: "text/csv;charset=utf-8",
      });

      const formData = new FormData();
      formData.append("files", blob, `${calendarId}.csv`);

      const response = await axios.post(`${BaseUrl}/schedules/analyze`, formData);
      const result = response.data?.[0]?.result;
      if (result) {
        const thisResult = Object.values(result)?.[0];
        setKpiSummary(thisResult);
      }
    } catch (error) {
      console.error("Erro ao analisar calendário via API:", error);
    }
  };

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
          analyzeScheduleViaAPI(scheduleData); // API KPI analysis
        }
      })
      .catch(console.error);
  }, [calendarId]);

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

        <Box
          sx={{
            mt: 4,
            p: 2,
            border: '1px solid #ccc',
            borderRadius: 2,
            backgroundColor: '#f9f9f9',
            maxHeight: 400,
            overflowY: 'auto',
            fontSize: 12,
            whiteSpace: 'pre-wrap',
            wordBreak: 'break-word',
          }}
        >
          <Typography variant="h6" gutterBottom>Debug: Dados do Schedule (API)</Typography>
          <pre>{JSON.stringify(data, null, 2)}</pre>
        </Box>
      </div>
    </div>
  );
};

export default Calendar;
