import React from "react";

const CalendarHeader = ({ months, selectedMonth, setSelectedMonth, downloadCSV }) => {
  return (
    <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between" }}>
      <h2 className="heading">Calendário de Trabalho</h2>
      <div>
        <select
          onChange={(e) => setSelectedMonth(Number(e.target.value))}
          value={selectedMonth}
          style={{ marginRight: "10px", padding: "8px", backgroundColor: "#28a745", color: "white", border: "none", borderRadius: "5px", fontSize: "14px" }}
        >
          {months.map((month, index) => (
            <option key={index + 1} value={index + 1}>{month}</option>
          ))}
        </select>
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
