import React from "react";
import {
  Home,
  CalendarDays,
  Users,
  Briefcase,
  CircleUserRound,
  Code2,
  Sun,
  FileText,
} from "lucide-react";
import { Link, useLocation } from "react-router-dom";
import "../styles/Manager.css";
import logo from '../assets/images/Logo.png';

const Sidebar_Manager = () => {
  const location = useLocation();

  const isActive = (path) => location.pathname === path;

  return (
    <div className="sidebar">
      <Link to="/">
        <img src={logo} alt="SmarTask Logo" className="logo-img" />
      </Link>
      <nav className="nav-links">
        <Link to="/manager" className={`nav-item ${isActive("/manager") ? "active" : ""}`}>
          <Home size={20} className="icon" /> Home
        </Link>
        <Link to="/manager/listcalendar" className={`nav-item ${isActive("/manager/listcalendar") ? "active" : ""}`}>
          <CalendarDays size={20} className="icon"/> Schedule
        </Link>
        <Link to="/manager/teams" className={`nav-item ${isActive("/manager/teams") ? "active" : ""}`}>
          <Users size={20} className="icon"/> Teams
        </Link>
        <Link to="/manager/employer" className={`nav-item ${isActive("/manager/employer") ? "active" : ""}`}>
          <Briefcase size={20} className="icon"/> Employees
        </Link>
        <Link to="/manager/compareCalendar" className={`nav-item ${isActive("/manager/compareCalendar") ? "active" : ""}`}>
          <Code2 size={20} className="icon"/> Compare Schedules
        </Link>
        <Link to="/manager/generatevacations" className={`nav-item ${isActive("/manager/generatevacations") ? "active" : ""}`}>
          <Sun size={20} className="icon"/> Vacation Generation
        </Link>
        <Link to="/manager/importminimus" className={`nav-item ${isActive("/manager/importminimus") ? "active" : ""}`}>
          <FileText size={20} className="icon"/> Import Minimums
        </Link>
        <Link to="/manager/rulesets" className={`nav-item ${isActive("/manager/rulesets") ? "active" : ""}`}>
          <Briefcase size={20} className="icon"/> Rule Sets
        </Link>
      </nav>
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