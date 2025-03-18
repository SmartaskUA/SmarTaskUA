import React from "react";
import { BrowserRouter as Router, Route, Routes } from "react-router-dom";
import Login from "./login/Login";  
import Manager from "./Manager/manager";  
import Admin from "./Admin/Admin";
import Add_Algor from "./Admin/Add_Algor"; 
import List_Calendar from "./Manager/ListCalendar";
import Teams from "./Manager/Teams";
import Employer from "./Manager/Employer";
import Calendar from "./Manager/Calender";  
import CreateCalendar from "./Manager/CreateCalendar";


const App = () => {
  return (
    <Router>
      <Routes>
        <Route path="/" element={<Login />} />
        <Route path="/manager" element={<Manager />} />
        <Route path="/admin" element={<Admin />} />
        <Route path="/admin/add_algor" element={<Add_Algor />} /> 
        <Route path="/manager/listcalendar" element={<List_Calendar />} /> 
        <Route path="/manager/teams" element={<Teams />} />
        <Route path="/manager/employer" element={<Employer />} />
        <Route path="/manager/calendar/:calendarId" element={<Calendar />} />
        <Route path="/manager/createCalendar" element={<CreateCalendar />} />

      </Routes>
    </Router>
  );
};

export default App;
