import React from "react";
import { Home, Plus, User } from "lucide-react"; 
import "./Sidebar.css"; 
import logo from '../assets/images/Logo.png';


const Sidebar = () => {
  return (
    <div className="sidebar">
      <div className="logo">
        <img src={logo} alt="SmarTask Logo" className="logo-img" />
      </div>
      <nav className="nav-links">
        <a href="#" className="nav-item"><Home size={20} className="icon" /> Home</a>
        <a href="#" className="nav-item"><Plus size={20} className="icon" /> Add Algorithm</a>
      </nav>

      <div className="admin-btn">
        <button><User size={20} className="icon" /> Admin</button>
      </div>
    </div>
  );
};

export default Sidebar;
