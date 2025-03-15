import React from "react";
import { BrowserRouter as Router, Route, Routes } from "react-router-dom";
import Login from "./login/Login";  
import Manager from "./Manager/manager";  
import Admin from "./Admin/Admin";
import Add_Algor from "./Admin/Add_Algor"; 
import Calender from "./Manager/Calender";
import Teams from "./Manager/Teams";
import Employer from "./Manager/Employer";

const App = () => {
  return (
    <Router>
      <Routes>
        <Route path="/" element={<Login />} />
        <Route path="/manager" element={<Manager />} />
        <Route path="/Admin" element={<Admin />} />
        <Route path="/Admin/add_algor" element={<Add_Algor />} /> 
        <Route path="/manager/calender" element={<Calender />} /> 
        <Route path="/manager/teams" element={<Teams />} />
        <Route path="/manager/employer" element={<Employer />} />
      </Routes>
    </Router>
  );
};

export default App;