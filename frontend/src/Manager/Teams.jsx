import React from "react";
import Sidebar_Manager from "../components/Sidebar_Manager"; 

const Teams = () => {
  return (
    <div className="admin-container">
      <Sidebar_Manager />  
      <div className="main-content">
        <h2 className="heading">Teams</h2>
      </div> 
    </div>
  );
};

export default Teams;
