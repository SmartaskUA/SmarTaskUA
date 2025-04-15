import React, { useState } from "react";
import { Link } from "react-router-dom";
import Sidebar from "../components/Sidebar"; 
import AlgorithmCard from "../components/admin/AlgorithmCard";
import "../styles/Admin.css";

const Admin = () => {
  const [isDropdownOpen, setIsDropdownOpen] = useState(false);
  const [algorithms, setAlgorithms] = useState([
    { name: "Algorithm 1", color: "purple", description: "Description 1" },
    { name: "Algorithm 2", color: "green", description: "Description 2" },
    { name: "Algorithm 3", color: "yellow", description: "Description 3" }
  ]);

  const toggleDropdown = () => {
    setIsDropdownOpen(!isDropdownOpen);
  };

  const handleOptionClick = (option) => {
    console.log(`Ordenando por: ${option}`);
    setIsDropdownOpen(false); 
  };


  const handleRemoveAlgorithm = (name) => {
    setAlgorithms(algorithms.filter(algorithm => algorithm.name !== name));
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
        
        <Link to="/admin/add_algor" className="algorithm-card add-button">
          Adicionar Algoritmo
        </Link>

        <div className="algorithm-cards">
          {algorithms.map((algorithm, index) => (
            <div key={index} className="algorithm-card-wrapper">
              <AlgorithmCard
                color={algorithm.color}
                textColor={algorithm.color}
                name={algorithm.name}
              />
              <button
                onClick={() => handleRemoveAlgorithm(algorithm.name)}
              >
                Remover
              </button>
            </div>
          ))}
        </div>

      </div>
    </div>
  );
};

export default Admin;
