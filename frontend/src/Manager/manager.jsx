import React from "react";
import { Link } from "react-router-dom";
import Sidebar_Manager from "../components/Sidebar_Manager";
import "../styles/Manager.css"; // Certifique-se de importar o CSS para os estilos

const ManagerHome = () => {
  return (
    <div className="admin-container">
      <Sidebar_Manager />
      
      {/* Main Content da Home Page */}
      <div className="main-content" style={{ padding: "20px" }}>
        
        {/* Linha 1 - 4 Cards (exemplo de "New Calendar" + 3 rascunhos) */}
        <div className="cards-row">
          {/* Card 1: New Calendar */}
          <div className="calendar-card new-calendar-card">
            <div className="calendar-card-header">
              <span className="status-dot green" />
              <span className="calendar-card-title">New Calendar</span>
            </div>
            <Link to="/manager/createCalendar" className="open-button btn-blue">
              Create
            </Link>
          </div>

          {/* Card 2: Draft Schedule 1 */}
          <div className="calendar-card draft-card">
            <div className="calendar-card-header">
              <span className="status-dot orange" />
              <span className="calendar-card-title">Draft Schedule 1</span>
            </div>
            <span className="draft-time">10min ago</span>
          </div>

          {/* Card 3: Draft Schedule 2 */}
          <div className="calendar-card draft-card">
            <div className="calendar-card-header">
              <span className="status-dot orange" />
              <span className="calendar-card-title">Draft Schedule 2</span>
            </div>
            <span className="draft-time">10min ago</span>
          </div>

          {/* Card 4: Draft Schedule 3 */}
          <div className="calendar-card draft-card">
            <div className="calendar-card-header">
              <span className="status-dot orange" />
              <span className="calendar-card-title">Draft Schedule 3</span>
            </div>
            <span className="draft-time">15min ago</span>
          </div>
        </div>

        {/* Linha 2 - Calendars in process (exemplo de cartões "em progresso") */}
        <h3 className="section-title">Calendars in Process</h3>
        <div className="calendar-cards-container">
          {/* Exemplo 1 */}
          <div className="calendar-card in-process">
            <div className="calendar-card-header">
              <span className="status-dot orange" />
              <span className="calendar-card-title">Processing 1</span>
            </div>
            <span className="draft-time">In progress...</span>
          </div>
          {/* Exemplo 2 */}
          <div className="calendar-card in-process">
            <div className="calendar-card-header">
              <span className="status-dot orange" />
              <span className="calendar-card-title">Processing 2</span>
            </div>
            <span className="draft-time">In progress...</span>
          </div>
        </div>

        {/* Linha 3 - Last Seen (exemplo de cartões concluídos mas ainda não abertos) */}
        <h3 className="section-title">Last Seen</h3>
        <div className="calendar-cards-container">
          <div className="calendar-card completed-card">
            <div className="calendar-card-header">
              <span className="status-dot green" />
              <span className="calendar-card-title">January, Algorithm X</span>
            </div>
            <Link to="/manager/calendar/abc123" className="open-button btn-green">
              Open
            </Link>
          </div>

          <div className="calendar-card completed-card">
            <div className="calendar-card-header">
              <span className="status-dot green" />
              <span className="calendar-card-title">September, Algorithm Z</span>
            </div>
            <Link to="/manager/calendar/xyz456" className="open-button btn-green">
              Open
            </Link>
          </div>

          <div className="calendar-card completed-card">
            <div className="calendar-card-header">
              <span className="status-dot green" />
              <span className="calendar-card-title">Another Calendar</span>
            </div>
            <Link to="/manager/calendar/def789" className="open-button btn-green">
              Open
            </Link>
          </div>
        </div>

      </div>
    </div>
  );
};

export default ManagerHome;
