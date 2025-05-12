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
import GenerateVacations from "./Manager/GenerateVacations";
import ImportMinimums from "./Manager/ImportMinimums";
import { AuthProvider } from "./context/AuthContext";
import NotFound from "./components/NotFound";
import CompareCalendar from "./Manager/CompareCalendar";

const App = () => {
  return (
    <AuthProvider>
      <Router>
        <Routes>
          <Route path="/" element={<Login />} />
          <Route path="/admin" element={<Admin />} />
          <Route path="/admin/add_algor" element={<Add_Algor />} />
          <Route path="/manager" element={<Manager />} />
          <Route path="/manager/listcalendar" element={<List_Calendar />} />
          <Route path="/manager/teams" element={<Teams />} />
          <Route path="/manager/employer" element={<Employer />} />
          <Route path="/manager/calendar/:calendarId" element={<Calendar />} />
          <Route path="/manager/createCalendar" element={<CreateCalendar />} />
          <Route path="/manager/compareCalendar" element={<CompareCalendar />} />
          <Route path="/manager/generatevacations" element={<GenerateVacations />} />
          <Route path="/manager/importminimus" element={<ImportMinimums />} />
          <Route path="/manager/teams" element={<Teams />} />

          <Route path="/manager/*" element={<NotFound />} />
          <Route path="/admin/*" element={<NotFound />} />
          <Route path="*" element={<NotFound />} />
        </Routes>
      </Router>
    </AuthProvider>
  );
};

export default App;
