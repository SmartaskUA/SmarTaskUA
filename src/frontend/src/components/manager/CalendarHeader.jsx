import React from "react";
import { ChevronLeft, ChevronRight } from "lucide-react"; // ícones leves e modernos

const CalendarHeader = ({
  months,
  selectedMonth,
  setSelectedMonth,
  downloadCSV,
  calendarTitle,
  algorithmName,
  scheduleType,
  viewMode,
  onToggleView,
  toggleViewLabel = "View Minimums",
  onDownloadSisqualExport,
  isExportingSisqual = false,
}) => {
  const selectedIndex = months.findIndex((month) => month.value === selectedMonth);
  const canGoPrev = selectedIndex > 0;
  const canGoNext = selectedIndex >= 0 && selectedIndex < months.length - 1;

  const handlePrevMonth = () => {
    if (canGoPrev) {
      setSelectedMonth(months[selectedIndex - 1].value);
    }
  };

  const handleNextMonth = () => {
    if (canGoNext) {
      setSelectedMonth(months[selectedIndex + 1].value);
    }
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
        {scheduleType && (
          <span
            style={{
              backgroundColor: scheduleType === "Horas" ? "#ecfeff" : "#eff6ff",
              color: "#0f172a",
              padding: "4px 10px",
              borderRadius: "999px",
              fontSize: "0.9rem",
              fontWeight: "700",
              display: "inline-block",
              border: "1px solid rgba(15, 23, 42, 0.12)",
            }}
          >
            {scheduleType}
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
            transition: "background 0.3s",
            opacity: canGoPrev ? 1 : 0.45
          }}
          disabled={!canGoPrev}
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
          {months.map((month) => (
            <option key={month.value} value={month.value}>
              {month.label}
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
            transition: "background 0.3s",
            opacity: canGoNext ? 1 : 0.45
          }}
          disabled={!canGoNext}
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
        {onDownloadSisqualExport && (
          <button
            onClick={onDownloadSisqualExport}
            disabled={isExportingSisqual}
            style={{
              padding: "8px 12px",
              backgroundColor: "#5b3fd6",
              color: "white",
              border: "none",
              cursor: isExportingSisqual ? "default" : "pointer",
              borderRadius: "5px",
              fontSize: "14px",
              transition: "background 0.3s",
              opacity: isExportingSisqual ? 0.7 : 1,
            }}
          >
            {isExportingSisqual ? "Exporting..." : "Download Sisqual JSON"}
          </button>
        )}
        {onToggleView && (
          <button
            onClick={onToggleView}
            style={{
              padding: "8px 12px",
              backgroundColor: viewMode === "minimums" ? "#6c757d" : "#17a2b8",
              color: "white",
              border: "none",
              cursor: "pointer",
              borderRadius: "5px",
              fontSize: "14px",
              transition: "background 0.3s"
            }}
          >
            {viewMode === "minimums" ? "View Schedule" : toggleViewLabel}
          </button>
        )}
      </div>
    </div>
  );
};

export default CalendarHeader;
