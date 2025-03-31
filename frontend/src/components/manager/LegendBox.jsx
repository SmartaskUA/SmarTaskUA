import React from "react";

const LegendBox = () => {
  const legends = [
    { label: "Folga", color: "#a0d8ef" },
    { label: "Férias", color: "#ffcccb" },
    { label: "Manhã", color: "#d4edda" },
    { label: "Tarde", color: "#f9e79f" },
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
            }}
          ></span>
        </div>
      ))}
    </div>
  );
};

export default LegendBox;
