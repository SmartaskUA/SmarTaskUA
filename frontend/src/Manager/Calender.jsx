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
  const { calendarId } = useParams();
  const [metadata, setMetadata] = useState(null); 


  const months = ["Janeiro", "Fevereiro", "Março", "Abril", "Maio", "Junho", "Julho", "Agosto", "Setembro", "Outubro", "Novembro", "Dezembro"];
  const daysInMonth = [31, 28, 31, 30, 31, 30, 31, 31, 30, 31, 30, 31];
  // Lista de feriados representados por números de dias no ano
const holidays = [31, 60, 120, 150, 200, 240, 300, 330]; 

const getDayOfYear = (date) => {
  const start = new Date(date.getFullYear(), 0, 0);
  const diff = date - start;
  const oneDay = 1000 * 60 * 60 * 24;
  return Math.floor(diff / oneDay);
};

const checkUnderworkedEmployees = () => {
  const employeeWorkDays = {};
  const holidays = [31, 60, 120, 150, 200, 240, 300, 330];

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

      // Só conta se for domingo ou feriado
      if (isSunday || isHoliday) {
        employeeWorkDays[employee].add(day);
      }
    }
  });

  const overworked = [];

  for (const employee in employeeWorkDays) {
    const specialDaysWorked = employeeWorkDays[employee].size;
    if (specialDaysWorked > 22) {
      overworked.push(employee);
    }
  }

  return overworked;
};


useEffect(() => {
  const baseUrl = BaseUrl;

  axios.get(`${baseUrl}/schedules/fetch/${calendarId}`)
    .then((response) => {
      if (response.data) {
        setData(response.data.data);
        setMetadata(response.data.metadata); // <- ESTA LINHA É ESSENCIAL

        console.log("Dados recebidos:", response.data.data);
        console.log("Metadata completo:", response.data.metadata);
      }
    })
    .catch((error) => {
      console.error("Erro ao buscar dados do calendário:", error);
    });
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

  // Funções para verificar conflitos  
  const checkScheduleConflicts = () => checkConflicts((shifts) => shifts.has("T") && shifts.has("M"));
  //const checkWorkloadConflicts = () => Object.keys(groupByEmployee()).filter(employee => groupByEmployee()[employee].size > 5); 
  //const checkUnderworkedEmployees = () => Object.keys(groupByEmployee()).filter(employee => groupByEmployee()[employee].size  <= 22);

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

    console.log("data:",data);
    console.log("employeeVACTIONS",employeeVacations);
  
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
        />

        <CalendarTable
          data={data}
          selectedMonth={selectedMonth}
          daysInMonth={daysInMonth}
          startDay={startDay}
          endDay={endDay}
        />
        <MetadataInfo metadata={metadata} />

        <KPIReport
          checkScheduleConflicts={checkScheduleConflicts} // sequencia inválida T-M
          checkWorkloadConflicts={checkWorkloadConflicts} // não pode ter masi do 5 dias em sequencia de trabalho
          checkUnderworkedEmployees={checkUnderworkedEmployees} // funcionários com mais de 22 Dias de Trabalho no ano feriados e domingos
          checkVacationDays={checkVacationDays}  // 30 dias de trabalho máximo (feriados) durante todo ano
      
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
