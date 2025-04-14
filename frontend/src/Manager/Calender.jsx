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

const Calendar = () => {
  const [data, setData] = useState([]);
  const [selectedMonth, setSelectedMonth] = useState(1);
  const [startDay, setStartDay] = useState(1);
  const [endDay, setEndDay] = useState(31);
  const { calendarId } = useParams();

  const months = ["Janeiro", "Fevereiro", "Março", "Abril", "Maio", "Junho", "Julho", "Agosto", "Setembro", "Outubro", "Novembro", "Dezembro"];
  const daysInMonth = [31, 28, 31, 30, 31, 30, 31, 31, 30, 31, 30, 31];
  // Lista de feriados representados por números de dias no ano
const holidays = [31, 60, 120, 150, 200, 240, 300, 330]; // Exemplo de feriados

// Função que retorna o dia do ano de uma data (1 = 1º de janeiro, 365 = 31 de dezembro)
const getDayOfYear = (date) => {
  const start = new Date(date.getFullYear(), 0, 0);
  const diff = date - start;
  const oneDay = 1000 * 60 * 60 * 24;
  return Math.floor(diff / oneDay);
};

const checkUnderworkedEmployees = () => {
  const employeeDays = groupByEmployee();
  const underworkedEmployees = [];

  Object.keys(employeeDays).forEach(employee => {
    const daysWorked = employeeDays[employee];
    let totalWorkedDays = 0;

    daysWorked.forEach(day => {
      // Convertendo o dia para um objeto Date (supondo que `day` seja uma data no formato 'YYYY-MM-DD')
      const date = new Date(day); 

      // Calculando o número do dia no ano
      const dayOfYear = getDayOfYear(date);

      // Verifica se o dia é sábado, domingo ou um feriado
      const isWeekend = date.getDay() === 6 || date.getDay() === 0; // Verifica se é sábado (6) ou domingo (0)
      const isHoliday = holidays.includes(dayOfYear); // Verifica se o dia é um feriado

      // Se for um dia útil ou feriado, conta como dia trabalhado
      if (isWeekend || isHoliday) {
        totalWorkedDays++;
      }
    });

    // Se o funcionário tem 22 ou menos dias de trabalho, ele está subtrabalhado
    if (totalWorkedDays <= 22) {
      underworkedEmployees.push(employee);
    }
  });

  return underworkedEmployees;
};

  useEffect(() => {
    const baseUrl = BaseUrl;
    axios.get(`${baseUrl}/schedules/fetch/${calendarId}`)
      .then((response) => {
        if (response.data) setData(response.data.data);
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
