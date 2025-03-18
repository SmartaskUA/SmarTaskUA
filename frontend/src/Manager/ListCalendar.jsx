import React, { useEffect, useState } from "react";
import { Link } from "react-router-dom";  
import Sidebar_Manager from "../components/Sidebar_Manager"; 
import BaseUrl from "../components/BaseUrl";

const ListCalendar = () => {
  const [schedules, setSchedules] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  useEffect(() => {
    const fetchSchedules = async () => {
      try {
        const response = await fetch(`${BaseUrl}/schedules/fetch`);
        if (!response.ok) {
          throw new Error("Erro ao buscar os calendários");
        }
        const data = await response.json();
        setSchedules(data);
      } catch (error) {
        setError(error.message);
      } finally {
        setLoading(false);
      }
    };

    fetchSchedules();
  }, []);

  return (
    <div className="admin-container">
      <Sidebar_Manager />
      <div className="main-content">
        <h2 className="heading">List Calendar</h2>

        {loading && <p>Carregando...</p>}
        {error && <p style={{ color: "red" }}>{error}</p>}

        {!loading && !error && schedules.length === 0 && <p>Nenhum calendário encontrado.</p>}

        {!loading && !error && schedules.map((schedule) => (
          <Link 
            key={schedule.id} 
            to={`/manager/calendar/${schedule.id}`} 
            className="btn"
          >
            {`Calendário ${schedule.id}`}
          </Link>
        ))}
      </div> 
    </div>
  );
};

export default ListCalendar;
