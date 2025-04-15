import React from "react";
import { Link } from "react-router-dom";
import "../styles/NotFound.css";
import Sidebar_Manager from "../components/Sidebar_Manager";
import erro404 from "../assets/images/404Erro.png";  

const NotFound = () => {
  return (
    <div className="notfound-container">
      <Sidebar_Manager />
      <div className="notfound-main-content"> 
        <img src={erro404} alt="Erro 404" className="not-found-image" />
        <h1>Oops! Page not found</h1>
        <Link to="/" className="back-home">Back to top</Link>
      </div>
    </div>
  );
};

export default NotFound;
