import React, { useState } from "react";
import Sidebar from "../components/Sidebar"; 
import AlgorithmCard from "../components/AlgorithmCard";
import "./Admin.css";

const Admin = () => {
  const [isDropdownOpen, setIsDropdownOpen] = useState(false);

  const toggleDropdown = () => {
    setIsDropdownOpen(!isDropdownOpen);
  };

  const handleOptionClick = (option) => {
    console.log(`Ordenando por: ${option}`);
    setIsDropdownOpen(false); 
  };

  return (
    <div className="admin-container">
      <div> 
        <Sidebar /> 
      </div>
      <div className="main-content">
        <div className="heading-container">
          <h2 className="heading">Algorithm’s List</h2>
          <div className="dropdown-container">
            <button className="order-button" onClick={toggleDropdown}>
              Order
            </button>
            {isDropdownOpen && (
              <div className="dropdown-menu">
                <div className="dropdown-item" onClick={() => handleOptionClick("Name")}>
                  Sort by Name
                </div>
                <div className="dropdown-item" onClick={() => handleOptionClick("Date")}>
                  Sort by Date
                </div>
                <div className="dropdown-item" onClick={() => handleOptionClick("Popularity")}>
                  Sort by Popularity
                </div>
              </div>
            )}
          </div>
        </div>
        <button className="algorithm-card add-button">Adicionar Algoritmo</button>
        <div className="algorithm-cards">
          <AlgorithmCard color="purple" textColor="#7a52aa" name="Algorithms 1" />
          <AlgorithmCard color="green" textColor="#4a7c4a" name="Algorithms 2" />
          <AlgorithmCard color="yellow" textColor="#b38b00" name="Algorithms 3" />
        </div>
      </div>
    </div>
  );
};

export default Admin;
