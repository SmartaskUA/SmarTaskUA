import React from "react";
import { Link } from "react-router-dom";  
import Sidebar_Manager from "../components/Sidebar_Manager"; 

const ListCalendar = () => {
  return (
    <div className="admin-container">
      <Sidebar_Manager />  
      <div className="main-content">
        <h2 className="heading">List Calendar</h2>
        
        <Link to="/manager/calendar/schedule1" className="btn">Calendário 1</Link>
        <Link to="/manager/calendar/schedule2" className="btn">Calendário 2</Link>
      </div> 
    </div>
  );
};

export default ListCalendar;
