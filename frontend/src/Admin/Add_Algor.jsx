import React, { useState } from "react";
import Sidebar from "../components/Sidebar";
import AlgorithmForm from "../components/admin/AlgorithmForm";
const Add_Algor = () => {
  return (
    <div className="admin-container">
      <Sidebar />
      <div className="main-content">
        <h2 className="heading">Add Algorithm</h2>
        <hr />
        <AlgorithmForm />
      </div>
    </div>
  );
};

export default Add_Algor;