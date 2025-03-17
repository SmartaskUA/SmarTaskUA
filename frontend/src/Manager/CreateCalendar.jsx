import React, { useState } from "react";
import Sidebar_Manager from "../components/Sidebar_Manager";
import "./CreateCalendar.css";

const CreateCalendar = () => {
  const [date, setDate] = useState("");
  const [durationH, setDurationH] = useState("");
  const [durationM, setDurationM] = useState("");

  return (
    <div className="admin-container">
      <Sidebar_Manager />
      <div className="calendar-wrapper">
        <div className="calendar-form-container">
          <h2>Calendar</h2>

          <div className="form-group">
            <label>Team:</label>
            <input type="text" placeholder="Digite o tema" />
          </div>

          <div className="form-group">
            <label>Data Inicio:</label>
            <input type="date" value={date} onChange={(e) => setDate(e.target.value)} />

            <label>Data Fim:</label>
            <input type="date" value={date} onChange={(e) => setDate(e.target.value)} />
          </div>

          <div className="duration-container">
            <div className="form-group">
              <label>Duração max (h):</label>
              <input type="number" value={durationH} onChange={(e) => setDurationH(e.target.value)} />
          
              <label>Duração (min):</label>
              <input type="number" value={durationM} onChange={(e) => setDurationM(e.target.value)} />
            </div>
          </div>

          <div className="action-buttons">
            <button className="save-btn">Gravar</button>
            <button className="test-btn">Teste</button>
            <button className="remove-btn">Remover</button>
          </div>
        </div>
        <div className="algorithm-buttons">
          <button className="algoritmo-btn">Algoritmo 1</button>
          <button className="algoritmo-btn">Algoritmo</button>
          <button className="algoritmo-btn">Voalgortiltar</button>
        </div>
      </div>
    </div>
  );
};

export default CreateCalendar;
