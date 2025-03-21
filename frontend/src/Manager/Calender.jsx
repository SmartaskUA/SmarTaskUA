import React, { useState, useEffect } from "react";
import { useParams } from "react-router-dom";
 import axios from "axios";
import Sidebar_Manager from "../components/Sidebar_Manager";
import CalendarTable from "../components/manager/CalendarTable";
import CalendarHeader from "../components/manager/CalendarHeader"; 
import BarChartDropdown from "../components/manager/BarChartDropdown";
import BarChartDropdownFolgasFerias from "../components/manager/BarChartDropdownFolgasFerias";
import BaseUrl from "../components/BaseUrl";

const Calendar = () => {
  const [data, setData] = useState([]);
  const [selectedMonth, setSelectedMonth] = useState(1);
  const { calendarId } = useParams();

  const months = [
    "Janeiro", "Fevereiro", "Março", "Abril", "Maio", "Junho",
    "Julho", "Agosto", "Setembro", "Outubro", "Novembro", "Dezembro"
  ];

  const daysInMonth = [31, 28, 31, 30, 31, 30, 31, 31, 30, 31, 30, 31];

  useEffect(() => {
    const baseUrl = BaseUrl(); // Retorna 'http://localhost:8081/'
    // Faz a requisição GET para o endpoint que retorna o JSON do calendário
    axios.get(`${baseUrl}schedules/fetch/${calendarId}`)
      .then((response) => {
        // Supomos que o JSON retornado possui a propriedade "data" com a matriz desejada:
        if (response.data) {
          setData(response.data.data);
        }
      })
      .catch((error) => {
        console.error("Erro ao carregar o JSON:", error);
      });
  }, [calendarId]);

  const downloadCSV = () => {
    // Converte os dados (que agora vêm do JSON) em CSV
    const csvContent = data.map((row) => row.join(",")).join("\n");
    const blob = new Blob([csvContent], { type: "text/csv" });
    const link = document.createElement("a");
    link.href = URL.createObjectURL(blob);
    link.download = `${calendarId}.csv`;
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
  };

  return (
    <div className="admin-container" style={{ display: "flex", height: "100vh" }}>
      <Sidebar_Manager />
      <div className="main-content" style={{ flex: 1, overflowY: "auto", padding: "20px", boxSizing: "border-box" }}>
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
