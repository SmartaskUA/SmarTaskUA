import React from "react";

const CalendarHeader = ({ months, selectedMonth, setSelectedMonth, downloadCSV, startDay, endDay, setStartDay, setEndDay }) => {
  return (
    <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", flexWrap: "wrap", gap: "10px" }}>
      <h2 className="heading">Calendário de Trabalho</h2>
      <div style={{ display: "flex", alignItems: "center", gap: "10px" }}>
        <select
          onChange={(e) => setSelectedMonth(Number(e.target.value))}
          value={selectedMonth}
          style={{ padding: "8px", backgroundColor: "#28a745", color: "white", border: "none", borderRadius: "5px", fontSize: "14px" }}
        >
          {months.map((month, index) => (
            <option key={index + 1} value={index + 1}>{month}</option>
          ))}
        </select>
        <label>Início:
          <input 
            type="number" 
            value={startDay} 
            min={1} 
            max={31} 
            onChange={(e) => setStartDay(Number(e.target.value))} 
            style={{ width: "60px", marginLeft: "5px" }}
          />
        </label>
        <label>Fim:
          <input 
            type="number" 
            value={endDay} 
            min={1} 
            max={31} 
            onChange={(e) => setEndDay(Number(e.target.value))} 
            style={{ width: "60px", marginLeft: "5px" }}
          />
        </label>
        <button 
          onClick={downloadCSV} 
          style={{ padding: "8px 12px", backgroundColor: "#006FD5", color: "white", border: "none", cursor: "pointer", borderRadius: "5px", fontSize: "14px" }}
        >
          Download CSV
        </button>
      </div>
    </div>
  );
};

export default CalendarHeader;
