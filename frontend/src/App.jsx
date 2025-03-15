import React from "react";
import { BrowserRouter as Router, Route, Routes } from "react-router-dom";
import Login from "./login/Login";  
import Manager from "./Manager/manager";  
import Admin from "./Admin/Admin";
import Add_Algor from "./Admin/Add_Algor"; 
import List_Calender from "./Manager/ListCalender";
import Teams from "./Manager/Teams";
import Employer from "./Manager/Employer";
import Calender from "./Manager/Calender";

const App = () => {
  return (
    <Router>
      <Routes>
        <Route path="/" element={<Login />} />
        <Route path="/manager" element={<Manager />} />
        <Route path="/admin" element={<Admin />} />
        <Route path="/admin/add_algor" element={<Add_Algor />} /> 
        <Route path="/manager/listcalender" element={<List_Calender />} /> 
        <Route path="/manager/teams" element={<Teams />} />
        <Route path="/manager/employer" element={<Employer />} />
        <Route path="/manager/calender" element={<Calender />} /> 
      </Routes>
    </Router>
  );
};

export default App;
