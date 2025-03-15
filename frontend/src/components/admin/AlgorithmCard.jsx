import React from "react";

const AlgorithmCard = ({ color, textColor, name }) => {
  return (
    <div className={`algorithm-card ${color}`} style={{ color: textColor }}>
      <p>{name}</p>
    </div>
  );
};

export default AlgorithmCard;
