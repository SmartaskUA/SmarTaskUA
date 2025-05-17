import React, { useState, useEffect } from "react";
import { useParams } from "react-router-dom";
import axios from "axios";
import Sidebar_Manager from "../components/Sidebar_Manager";
import CalendarTable from "../components/manager/CalendarTable";
import CalendarHeader from "../components/manager/CalendarHeader";
import BarChartDropdown from "../components/manager/BarChartDropdown";
import BarChartDropdownFolgasFerias from "../components/manager/BarChartDropdownFolgasFerias";
import KPIReport from "../components/manager/KPIReport";
import BaseUrl from "../components/BaseUrl";
import MetadataInfo from "../components/manager/MetadataInfo";
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

  useEffect(() => {
    setStartDay(1);
    setEndDay(daysInMonth[selectedMonth - 1]);
  }, [selectedMonth, daysInMonth]);
  
  const holidays = [31, 60, 120, 150, 200, 240, 300, 330];

  const getDayOfYear = (date) => {
    const start = new Date(date.getFullYear(), 0, 0);
    const diff = date - start;
    const oneDay = 1000 * 60 * 60 * 24;
    return Math.floor(diff / oneDay);
  };

  const checkUnderworkedEmployees = () => {
    const employeeWorkDays = {};
    const getDayOfYear = (dateStr) => {
      const date = new Date(dateStr);
      const start = new Date(date.getFullYear(), 0, 0);
      const diff = date - start;
      const oneDay = 1000 * 60 * 60 * 24;
      return Math.floor(diff / oneDay);
    };

    data.forEach(({ employee, day, shift }) => {
      if (!employeeWorkDays[employee]) {
        employeeWorkDays[employee] = new Set();
      }

      if (shift !== "F") {
        const date = new Date(day);
        const dayOfWeek = date.getDay(); // 0 = Domingo
        const dayOfYear = getDayOfYear(day);
        const isSunday = dayOfWeek === 0;
        const isHoliday = holidays.includes(dayOfYear);

        if (isSunday || isHoliday) {
          employeeWorkDays[employee].add(day);
        }
      }
    });

    return Object.keys(employeeWorkDays).filter(
      (employee) => employeeWorkDays[employee].size > 22
    );
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
        }
        if (response.data) {
          setData(response.data.data);
          setMetadata(response.data.metadata);
        }
    
      })
      .catch(console.error);
  }, [calendarId]);

  const groupByEmployee = () => {
    const employeeDays = {};
    data.forEach(({ employee, day }) => {
      if (!employeeDays[employee]) employeeDays[employee] = new Set();
      employeeDays[employee].add(day);
    });
    return employeeDays;
  };

  const checkConflicts = (condition) => {
    const dayShifts = data.reduce((acc, { day, shift }) => {
      if (!acc[day]) acc[day] = new Set();
      acc[day].add(shift);
      return acc;
    }, {});
    return Object.keys(dayShifts).filter(day => condition(dayShifts[day]));
  };

  const checkScheduleConflicts = () => checkConflicts((shifts) => shifts.has("T") && shifts.has("M"));

  const checkWorkloadConflicts = () => {
    const conflicts = [];
    const grouped = groupByEmployee();
    for (const employee in grouped) {
      const days = Array.from(grouped[employee]).map(Number).sort((a, b) => a - b);
      let consecutiveCount = 1;
      for (let i = 1; i < days.length; i++) {
        if (days[i] === days[i - 1] + 1) {
          consecutiveCount++;
          if (consecutiveCount > 5) {
            conflicts.push(employee);
            break;
          }
        } else {
          consecutiveCount = 1;
        }
      }
    }
    return conflicts;
  };

  const checkVacationDays = () => {
    const employeeVacations = data.reduce((acc, { employee, shift }) => {
      if (employee === "Employee") return acc;
      if (shift === "F") {
        acc[employee] = (acc[employee] || 0) + 1;
      }
      return acc;
    }, {});
    return Object.keys(employeeVacations).filter(employee => employeeVacations[employee] !== 30);
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

        <BarChartDropdown
          data={data}
          selectedMonth={selectedMonth}
          daysInMonth={daysInMonth}
        />
        <BarChartDropdownFolgasFerias
          data={data}
          selectedMonth={selectedMonth}
          daysInMonth={daysInMonth}
        />
      </div>
    </div>
  );
};

export default Calendar;
