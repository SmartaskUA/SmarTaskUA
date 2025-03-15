import React from "react";
import { Link } from "react-router-dom";  
import Sidebar_Manager from "../components/Sidebar_Manager"; 

const ListCalendar = () => {
  return (
    <div className="admin-container">
      <Sidebar_Manager />  
      <div className="main-content">
        <h2 className="heading">List Calendar</h2>
        <Link to="/manager/calendar" className="btn">Calendário de Teste</Link>  
      </div> 
    </div>
  );
};

export default ListCalendar;
