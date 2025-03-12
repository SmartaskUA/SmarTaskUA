import React from "react";
import { BrowserRouter as Router, Route, Routes } from "react-router-dom";
import Login from "./login/Login";  
import Manager from "./Manager/manager";  
import Admin from "./Admin/admin";


const App = () => {
  return (
    <Router>
      <Routes>
        <Route path="/" element={<Login />} />
        <Route path="/manager" element={<Manager />} />
        <Route path="/admin" element={<Admin />} />

      </Routes>
    </Router>
  );
};

export default App;