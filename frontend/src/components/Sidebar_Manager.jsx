import React from "react";
import { Home, SquarePlus, CalendarDays, Users, Briefcase, CircleUserRound } from "lucide-react"; 
import { Link } from "react-router-dom";  
import "./Sidebar.css"; 
import logo from '../assets/images/Logo.png';

const Sidebar_Manager = () => {
  return (
    <div className="sidebar">
      <div className="logo">
        <img src={logo} alt="SmarTask Logo" className="logo-img" />
      </div>
      <nav className="nav-links">
        <Link to="/manager" className="nav-item">
          <Home size={20} className="icon" /> Home
        </Link>
        <Link to="/manager/calender" className="nav-item">
          <CalendarDays size={20} className="icon"/> Calendar
        </Link>
        <Link to="/manager/teams" className="nav-item"> 
          <Users size={20} className="icon"/> Teams
        </Link> 
        <Link to="/manager/employer" className="nav-item"> 
          <Briefcase size={20} className="icon"/> Employees
        </Link> 
      </nav>

      {/* <div className="addCalendar-btn">
        <Link>
          <button>
            <SquarePlus size={20} className="icon" /> Calendar
          </button>
        </Link>
      </div> */}

      <div className="manager-btn">
        <Link>
          <button>
            <CircleUserRound size={20} className="icon" /> Team
          </button>
        </Link>
      </div>

    </div>
  );
};

export default Sidebar_Manager;
