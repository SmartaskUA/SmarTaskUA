import React, { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import Sidebar_Manager from "../components/Sidebar_Manager";
import BaseUrl from "../components/BaseUrl";
import axios from "axios";
import "../styles/Manager.css";
import { Autocomplete, TextField, CircularProgress } from "@mui/material";

const ListCalendar = () => {
  const [calendars, setCalendars] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [search, setSearch] = useState("");
  const [suggestions, setSuggestions] = useState([]);
  const [isLoadingSuggestions, setIsLoadingSuggestions] = useState(false);

  useEffect(() => {
    const fetchCalendars = async () => {
      try {
        const baseUrl = BaseUrl();
        const response = await axios.get(`${baseUrl}schedules/fetch`);
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

  const handleSearch = (event, value) => {
    setSearch(value);

    if (value.length > 0) {
      setIsLoadingSuggestions(true);
      const filteredCalendars = calendars.filter(calendar =>
        calendar.title.toLowerCase().includes(value.toLowerCase())
      );
      setSuggestions(filteredCalendars);
      setIsLoadingSuggestions(false);
    } else {
      setSuggestions([]);
    }
  };

  const handleSuggestionClick = (calendar) => {
    setSearch(calendar.title);
    setSuggestions([]);
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
        <div className="header" style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
          <h2 className="heading" style={{ marginRight: "201px" }}>List Calendar</h2>
          <Autocomplete 
            style={{ width: "250px", marginRight: "5%" }} 
            freeSolo
            options={suggestions.length > 0 ? suggestions : calendars}
            getOptionLabel={(option) => option.title}
            inputValue={search}  
            onInputChange={handleSearch}  
            renderInput={(params) => (
              <TextField
                {...params}
                label="Pesquisar por nome"
                variant="outlined"
                InputProps={{
                  ...params.InputProps,
                  endAdornment: isLoadingSuggestions ? (
                    <CircularProgress color="inherit" size={20} />
                  ) : null,
                }}
              />
            )}
            onChange={(event, newValue) => {
              handleSuggestionClick(newValue);
            }}
            renderOption={(props, option) => (
              <li {...props} key={option.id}>
                {option.title}
              </li>
            )}
          />
        </div>

        <div className="calendar-cards-container">
          {(suggestions.length > 0 ? suggestions : calendars).length > 0 ? (
            (suggestions.length > 0 ? suggestions : calendars).map((calendar) => (
              <div key={calendar.id} className="calendar-card">
                <div className="calendar-card-header">
                  <span className="status-dot" />
                  <span className="calendar-card-title">
                    {calendar.title}
                    {calendar.algorithm ? `, ${calendar.algorithm}` : ""}
                  </span>
                </div>

                <Link to={`/manager/calendar/${calendar.id}`} className="open-button" style={{  backgroundColor: "#4CAF50",}}>
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
