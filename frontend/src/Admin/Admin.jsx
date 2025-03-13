import React from "react";
import Sidebar from "../components/Sidebar"; 
import "./Admin.css"; 

const Admin = () => {
  return (
    <div className="admin-container">
      <div> 
        <Sidebar /> 
      </div>
      <div className="main-content">
        <h2 className="heading">Algorithm’s List</h2>
      </div>
    </div>
  );
};

export default Admin;
