import React from "react";

const CalendarHeader = ({ months, selectedMonth, setSelectedMonth, downloadCSV, calendarTitle, algorithmName }) => {
  return (
    <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", flexWrap: "wrap", gap: "10px" }}>
      <div style={{ display: "flex", alignItems: "center", gap: "10px" }}>
        <h2 className="heading" style={{ margin: 0 }}>{calendarTitle}</h2>
        {algorithmName && (
          <span
            style={{
              backgroundColor: "#e3f2fd",
              color: "black",
              padding: "4px 10px",
              borderRadius: "5px",
              fontSize: "1rem",
              fontWeight: "700",
              display: "inline-block",
            }}
          >
            {algorithmName}
          </span>
        )}
      </div>
      <div style={{ display: "flex", alignItems: "center", gap: "10px" }}>
        <select
          onChange={(e) => setSelectedMonth(Number(e.target.value))}
          value={selectedMonth}
          style={{
            padding: "8px",
            backgroundColor: "#28a745",
            color: "white",
            border: "none",
            borderRadius: "5px",
            fontSize: "14px",
          }}
        >
          {months.map((month, index) => (
            <option key={index + 1} value={index + 1}>
              {month}
            </option>
          ))}
        </select>

        <button
          onClick={downloadCSV}
          style={{
            padding: "8px 12px",
            backgroundColor: "#006FD5",
            color: "white",
            border: "none",
            cursor: "pointer",
            borderRadius: "5px",
            fontSize: "14px",
          }}
        >
          Download CSV
        </button>
      </div>
    </div>
  );
};

export default CalendarHeader;
