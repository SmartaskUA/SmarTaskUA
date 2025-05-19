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

  const months = [
    "Janeiro", "Fevereiro", "Março", "Abril", "Maio", "Junho",
    "Julho", "Agosto", "Setembro", "Outubro", "Novembro", "Dezembro"
  ];
  const daysInMonth = [31, 28, 31, 30, 31, 30, 31, 31, 30, 31, 30, 31];

  const getFixedHolidaysAsDayOfYear = (year) => {
    const fixedHolidays = [
      [1, 1],    // 1 Jan
      [4, 25],   // 25 Apr
      [5, 1],    // 1 May
      [6, 10],   // 10 Jun
      [8, 15],   // 15 Aug
      [10, 5],   // 5 Oct
      [11, 1],   // 1 Nov
      [12, 1],   // 1 Dec
      [12, 8],   // 8 Dec
      [12, 25],  // 25 Dec
    ];
    return fixedHolidays.map(([month, day]) => {
      const date = new Date(year, month - 1, day);
      const start = new Date(date.getFullYear(), 0, 0);
      const diff = date - start;
      const oneDay = 1000 * 60 * 60 * 24;
      return Math.floor(diff / oneDay);
    });
  };

  const [holidays, setHolidays] = useState([]);

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
          setHolidays(getFixedHolidaysAsDayOfYear(year));
        }
      })
      .catch(console.error);
  }, [calendarId]);

  const parseRawCSVData = () => {
    if (!Array.isArray(data) || data.length < 3) return [];
    const header = data[0];
    const teamIndex = header.length - 1;
    const content = data.slice(1, -1);

    const result = [];
    content.forEach((row) => {
      const id = row[0];
      for (let i = 1; i < teamIndex; i++) {
        result.push({
          employee: id,
          day: i,
          shift: row[i]
        });
      }
    });
    return result;
  };

  const kpiData = parseRawCSVData();

  const checkScheduleConflicts = () => {
    const conflicts = [];
    const shiftsByDay = {};
    kpiData.forEach(({ day, shift }) => {
      if (!shiftsByDay[day]) shiftsByDay[day] = new Set();
      shiftsByDay[day].add(shift);
    });
    Object.entries(shiftsByDay).forEach(([day, shifts]) => {
      if (shifts.has("T") && shifts.has("M")) {
        conflicts.push({ day, motivo: "Turnos T e M no mesmo dia" });
      }
    });
    return conflicts;
  };

  const checkWorkloadConflicts = () => {
    const conflicts = [];
    const byEmp = {};
    kpiData.forEach(({ employee, day, shift }) => {
      if (!byEmp[employee]) byEmp[employee] = [];
      if (shift !== "F" && shift !== "0") byEmp[employee].push(day);
    });

    for (const [employee, days] of Object.entries(byEmp)) {
      const sorted = days.sort((a, b) => a - b);
      let count = 1;
      for (let i = 1; i < sorted.length; i++) {
        if (sorted[i] === sorted[i - 1] + 1) {
          count++;
          if (count > 5) {
            const year = metadata?.year || new Date().getFullYear();
            const dayNum = sorted[i];
            const date = new Date(year, 0, dayNum);
            conflicts.push({ employee, day: date.toLocaleDateString("pt-PT"), motivo: "Mais de 5 dias consecutivos de trabalho" });
            break;
          }
        } else {
          count = 1;
        }
      }
    }
    return conflicts;
  };

  const checkUnderworkedEmployees = () => {
    const workDays = {};
    kpiData.forEach(({ employee, day, shift }) => {
      if (!workDays[employee]) workDays[employee] = [];
      if (shift !== "F" && shift !== "0") {
        const year = metadata?.year || new Date().getFullYear();
        const date = new Date(year, 0, day);
        const dayOfWeek = date.getDay();
        const dayOfYear = day;
        const isSunday = dayOfWeek === 0;
        const isHoliday = holidays.includes(dayOfYear);
        if (isSunday || isHoliday) {
          workDays[employee].push(day);
        }
      }
    });
    return Object.entries(workDays)
      .filter(([_, days]) => days.length > 22)
      .map(([employee, days]) => {
        const year = metadata?.year || new Date().getFullYear();
        const date = new Date(year, 0, days[22]);
        return { employee, day: date.toLocaleDateString("pt-PT"), motivo: "Mais de 22 dias úteis trabalhados" };
      });
  };

  const checkVacationDays = () => {
    const vacationCounts = {};
    kpiData.forEach(({ employee, shift }) => {
      if (shift === "F") {
        vacationCounts[employee] = (vacationCounts[employee] || 0) + 1;
      }
    });
    return Object.entries(vacationCounts)
      .filter(([_, count]) => count !== 30)
      .map(([employee]) => ({ employee, motivo: `Número de dias de férias incorreto: ${vacationCounts[employee]}` }));
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

        <KPIReport
          checkScheduleConflicts={checkScheduleConflicts}
          checkWorkloadConflicts={checkWorkloadConflicts}
          checkUnderworkedEmployees={checkUnderworkedEmployees}
          checkVacationDays={checkVacationDays}
        />

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
