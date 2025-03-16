import React, { useState } from "react";
import Sidebar_Manager from "../components/Sidebar_Manager";
import "./CreateCalendar.css";

const CreateCalendar = () => {
  const [date, setDate] = useState("");
  const [time, setTime] = useState("");
  const [durationH, setDurationH] = useState("");
  const [durationM, setDurationM] = useState("");

  return (
    <div className="admin-container">
      <Sidebar_Manager />
      <div className="main-content">
        <h2>Calendar</h2>

        <div className="form-group">
          <label>Team:</label>
          <input type="text" placeholder="Digite o tema" />
        </div>

        <div className="form-group">
          <label>Local:</label>
          <select>
            <option value="">LOC.001 - TYPY</option>
          </select>
        </div>

        <div className="form-group">
          <label>Data:</label>
          <input type="date" value={date} onChange={(e) => setDate(e.target.value)} />
        </div>

        <div className="form-group">
          <label>Hora:</label>
          <input type="time" value={time} onChange={(e) => setTime(e.target.value)} />
        </div>

        <div className="form-group checkbox-group">
          <label><input type="checkbox" /> Media</label>
          <label><input type="checkbox" /> Text</label>
        </div>
        <div className="duration-container">
          <div className="form-group">
            <label>Duração (h):</label>
            <input type="number" value={durationH} onChange={(e) => setDurationH(e.target.value)} />
          </div>
          <div className="form-group">
            <label>Duração (min):</label>
            <input type="number" value={durationM} onChange={(e) => setDurationM(e.target.value)} />
          </div>
        </div>

        <div className="button-group">
          <button className="algoritmo-btn">Algoritmo 1</button>
          <button className="algoritmo-btn">Algoritmo</button>
          <button className="algoritmo-btn">Voalgortiltar</button>
        </div>

        <div className="action-buttons">
          <button className="save-btn">Gravar</button>
          <button className="test-btn">Teste</button>
          <button className="remove-btn">Remover</button>
        </div>
      </div>
    </div>
  );
};

export default CreateCalendar;