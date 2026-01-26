import React from "react";

const LegendBox = ({ scheduleType, teamLegends = [] }) => {
  const normalizedType = String(scheduleType || "").toLowerCase();
  const isHourly = normalizedType === "horas" || normalizedType === "hours";

  const shiftLegends = [
    { label: "Vacation", color: "#ffcccb" },
    { label: "Off", color: "#f5f7fa" },
    { label: "Holiday", color: "#800080" },
    { label: "Morning", color: "#d4edda" },
    { label: "Afternoon", color: "#f9e79f" },
    { label: "Night", color: "#9eb3caff" },
  ];

  const hourlyLegends = [
    { label: "Vacation", color: "#ffe5e5" },
    { label: "Off", color: "#f5f7fa" },
    ...teamLegends,
  ];

  const legends = isHourly ? hourlyLegends : [...shiftLegends, ...teamLegends];

  return (
    <div
      style={{
        marginTop: "1rem",
        padding: "12px 16px",
        borderRadius: "12px",
        display: "flex",
        justifyContent: "flex-start",
        alignItems: "center",
        gap: "16px",
        flexWrap: "wrap",
        backgroundColor: "#f8fafc",
        border: "1px solid #e2e8f0",
      }}
    >
      {legends.map((item, index) => (
        <div key={index} style={{ display: "flex", alignItems: "center" }}>
          <span style={{ fontWeight: 600, marginRight: "6px", fontSize: "12px" }}>
            {item.label}
          </span>
          <span
            style={{
              display: "inline-block",
              width: "18px",
              height: "18px",
              backgroundColor: item.color,
              borderRadius: "6px",
              border: "1px solid rgba(15, 23, 42, 0.12)",
            }}
          ></span>
        </div>
      ))}
    </div>
  );
};

export default LegendBox;
