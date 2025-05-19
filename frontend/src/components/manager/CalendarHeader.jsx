import React from "react";
import { ChevronLeft, ChevronRight } from "lucide-react"; // ícones leves e modernos

const CalendarHeader = ({
  months,
  selectedMonth,
  setSelectedMonth,
  downloadCSV,
  calendarTitle,
  algorithmName
}) => {
  const handlePrevMonth = () => {
    setSelectedMonth(prev => Math.max(prev - 1, 1));
  };

  const handleNextMonth = () => {
    setSelectedMonth(prev => Math.min(prev + 1, 12));
  };

  return (
    <div style={{
      display: "flex",
      alignItems: "center",
      justifyContent: "space-between",
      flexWrap: "wrap",
      gap: "10px"
    }}>
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
        <button
          onClick={handlePrevMonth}
          title="Mês anterior"
          style={{
            backgroundColor: "#28a745",
            border: "none",
            borderRadius: "5px",
            padding: "6px",
            cursor: "pointer",
            display: "flex",
            alignItems: "center",
            justifyContent: "center",
            transition: "background 0.3s"
          }}
        >
          <ChevronLeft color="white" size={20} />
        </button>

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
          onClick={handleNextMonth}
          title="Próximo mês"
          style={{
            backgroundColor: "#28a745",
            border: "none",
            borderRadius: "5px",
            padding: "6px",
            cursor: "pointer",
            display: "flex",
            alignItems: "center",
            justifyContent: "center",
            transition: "background 0.3s"
          }}
        >
          <ChevronRight color="white" size={20} />
        </button>

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
            transition: "background 0.3s"
          }}
        >
          Download CSV
        </button>
      </div>
    </div>
  );
};

export default CalendarHeader;
