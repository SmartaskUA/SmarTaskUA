import React from "react";
import Sidebar_Manager from "../components/Sidebar_Manager";

const CompareCalendar = () => {
  return (
    <div className="admin-container">
      <Sidebar_Manager />
      <div className="main-content">
        <h1>Compare Algorithms</h1>
        <p>Select two calendars to compare algorithms.</p>
      </div>
    </div>
  );
};

export default CompareCalendar;
