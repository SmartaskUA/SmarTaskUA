import React, { useState } from "react";
import axios from "axios";
import baseurl from "../components/BaseUrl"; 
import Sidebar_Manager from "../components/Sidebar_Manager";
import "../styles/Manager.css";

const CreateCalendar = () => {
  const [dateStart, setDateStart] = useState("");
  const [dateEnd, setDateEnd] = useState("");
  const [team, setTeam] = useState("");
  const [durationH, setDurationH] = useState("");
  const [durationM, setDurationM] = useState("");

  const handleSave = async () => {
    const data = {
      team,
      dateStart,
      dateEnd,
      duration: `${durationH}h ${durationM}m`,
    };

    try {
      const response = await axios.post(`${baseurl}/schedules/generate`, data);
      alert("Dados enviados com sucesso!");
      console.log(response.data);
    } catch (error) {
      console.error("Erro ao enviar os dados:", error);
      alert("Erro ao enviar os dados.");
    }
  };

  return (
    <div className="admin-container">
      <Sidebar_Manager />
      <div className="calendar-wrapper">
        <div className="calendar-form-container">
          <h2>Calendar</h2>

          <div className="form-group">
            <label>Team:</label>
            <input type="text" value={team} onChange={(e) => setTeam(e.target.value)} placeholder="Digite o tema" />
          </div>

          <div className="form-group">
            <label>Data Início:</label>
            <input type="date" value={dateStart} onChange={(e) => setDateStart(e.target.value)} />

            <label>Data Fim:</label>
            <input type="date" value={dateEnd} onChange={(e) => setDateEnd(e.target.value)} />
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
            <button className="save-btn" onClick={handleSave}>Gravar</button>
            <button className="test-btn">Teste</button>
            <button className="remove-btn">Remover</button>
          </div>
        </div>
        
        <div className="algorithm-buttons">
          <button className="algoritmo-btn">Algoritmo 1</button>
          <button className="algoritmo-btn">Algoritmo 2</button>
          <button className="algoritmo-btn">Algoritmo 3</button>
        </div>
      </div>
    </div>
  );
};

export default CreateCalendar;
