import React from "react";
import Sidebar_Manager from "../components/Sidebar_Manager"; 
import "./manager.css"; 
import { Link } from "react-router-dom";


const home = () => {
  return (
    <div className="admin-container">
      <div> 
        <Sidebar_Manager /> 
      </div>
      <div className="main-content">
        <h2 className="heading">HOME PAGE</h2>
        <Link to="/manager/createCalendar" className="btn">
          Criar Calendário
        </Link>
      </div> 
    </div>
  );
};

export default home;
