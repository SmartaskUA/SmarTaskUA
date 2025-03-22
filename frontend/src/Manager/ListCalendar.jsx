import React, { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import Sidebar_Manager from "../components/Sidebar_Manager";
import BaseUrl from "../components/BaseUrl";
import axios from "axios";
import "../styles/Manager.css";

const ListCalendar = () => {
  const [calendars, setCalendars] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [search, setSearch] = useState("");

  useEffect(() => {
    const fetchCalendars = async () => {
      try {
        const baseUrl = BaseUrl();
        console.log("Base URL: ", baseUrl);

        const response = await axios.get(`${baseUrl}schedules/fetch`);
        console.log("Resposta da API:", response);

        if (response.data) {
          setCalendars(response.data);
        } else {
          setError("Nenhum dado encontrado.");
        }
      } catch (error) {
        setError("Erro ao buscar calendários. Tente novamente.");
        console.error("Erro ao buscar calendários:", error);
      } finally {
        setLoading(false);
      }
    };

    fetchCalendars();
  }, []);

  const handleSearch = async (e) => {
    setSearch(e.target.value);
    if (e.target.value.length > 0) {
      try {
        const baseUrl = BaseUrl();
        const response = await axios.get(`${baseUrl}schedules/${e.target.value}`);
        if (response.data) {
          setCalendars([response.data]);
        } else {
          setCalendars([]);
        }
      } catch (error) {
        console.error("Erro ao buscar calendário:", error);
        setCalendars([]);
      }
    } else {
      try {
        const baseUrl = BaseUrl();
        const response = await axios.get(`${baseUrl}schedules/fetch`);
        if (response.data) {
          setCalendars(response.data);
        } else {
          setCalendars([]);
        }
      } catch (error) {
        console.error("Erro ao buscar calendários:", error);
        setCalendars([]);
      }
    }
  };

  if (loading) {
    return (
      <div className="admin-container">
        <Sidebar_Manager />
        <div className="main-content">
          <h2 className="heading">Carregando...</h2>
        </div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="admin-container">
        <Sidebar_Manager />
        <div className="main-content">
          <h2 className="heading">{error}</h2>
        </div>
      </div>
    );
  }

  return (
    <div className="admin-container">
      <Sidebar_Manager />
      <div className="main-content">
        <div className="header">
          <h2 className="heading">List Calendar</h2>
          <input
            type="text"
            placeholder="Pesquisar por nome"
            value={search}
            onChange={handleSearch}
            className="search-input"
          />
        </div>

        <div className="calendar-cards-container">
          {calendars.length > 0 ? (
            calendars.map((calendar) => (
              <div key={calendar.id} className="calendar-card">
                <div className="calendar-card-header">

                  <span className="status-dot" />

                  <span className="calendar-card-title">
                    {calendar.title}
                    {calendar.algorithm ? `, ${calendar.algorithm}` : ""}
                  </span>
                </div>

                <Link to={`/manager/calendar/${calendar.id}`} className="open-button">
                  Open
                </Link>
              </div>
            ))
          ) : (
            <p>Nenhum calendário encontrado.</p>
          )}
        </div>
      </div>
    </div>
  );
};

export default ListCalendar;
