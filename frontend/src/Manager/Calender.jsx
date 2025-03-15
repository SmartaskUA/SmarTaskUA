import React from "react";
import Sidebar_Manager from "../components/Sidebar_Manager"; 

const Calender = () => {
  return (
    <div className="admin-container">
      <Sidebar_Manager />  
      <div className="main-content">
        <h2 className="heading">Calendário de Exemplo</h2>
        <p>Seu calendário aparecerá aqui!</p>
      </div> 
    </div>
  );
};

export default Calender;
