import React from "react";

const LegendBox = () => {
  const legends = [
    { label: "Break", color: "#ffffff" }, 
    { label: "Holiday", color: "#800080" }, 
    { label: "Vacation", color: "#ffcccb" },
    { label: "Morning", color: "#d4edda" },
    { label: "Afternoon", color: "#f9e79f" },
    { label: "Night", color: "#9eb3caff" },
  ];

  return (
    <div
      style={{
        marginTop: "1rem",
        padding: "2%",
        borderRadius: "10px",
        display: "flex",
        justifyContent: "flex-start",
        alignItems: "center",
        gap: "20px",
      }}
    >
      {legends.map((item, index) => (
        <div key={index} style={{ display: "flex", alignItems: "center" }}>
          <span style={{ fontWeight: "bold", marginRight: "5px" }}>
            {item.label}
          </span>
          -{" "}
          <span
            style={{
              display: "inline-block",
              width: "25px",
              height: "25px",
              backgroundColor: item.color,
              marginLeft: "5px",
              border: "1px solid #ccc",
            }}
          ></span>
        </div>
      ))}
    </div>
  );
};

export default LegendBox;