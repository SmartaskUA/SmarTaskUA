import React, { useEffect, useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import Sidebar_Manager from "../components/Sidebar_Manager";
import baseurl from "../components/BaseUrl";
import axios from "axios";
import "../styles/Manager.css";
import { Autocomplete, TextField, CircularProgress } from "@mui/material";

const ListCalendar = () => {
  const [calendars, setCalendars] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [title, setTitle] = useState("");
  const [suggestions, setSuggestions] = useState([]);
  const [isLoadingSuggestions, setIsLoadingSuggestions] = useState(false);

  const navigate = useNavigate();

  useEffect(() => {
    const fetchCalendars = async () => {
      try {
        const response = await axios.get(`${baseurl}/schedules/fetch`);
        if (response.data) {
          setCalendars(response.data);
          setError(null);
        } else {
          setError("No data found.");
        }
      } catch (error) {
        setError("Error fetching calendars. Please try again.");
        console.error("Error fetching calendars:", error);
      } finally {
        setLoading(false);
      }
    };

    fetchCalendars();
    const interval = setInterval(fetchCalendars, 3000);

    return () => clearInterval(interval);
  }, []);


  const handleSearchInputChange = (event, newValue) => {
    setTitle(newValue);
    if (newValue.length > 0) {
      const filtered = calendars.filter((calendar) =>
        calendar.title.toLowerCase().includes(newValue.toLowerCase())
      );
      setSuggestions(filtered);
    } else {
      setSuggestions([]);
    }
  };

  const handleSearchSubmit = async (event) => {
    if (event.key === "Enter" && title.trim().length > 0) {
      event.preventDefault();

      // Check if the entered title exists exactly in the list of calendars
      const calendarMatch = calendars.find(
        (calendar) => calendar.title.toLowerCase() === title.toLowerCase()
      );

      if (!calendarMatch) {
        alert("Calendar does not exist.");
        return;
      }

      try {
        const response = await axios.get(`${baseurl}/schedules/${calendarMatch.title}`);
        if (response.data) {
          navigate(`/manager/calendar/${response.data.id}`);
        } else {
          alert("Calendar not found.");
        }
      } catch (error) {
        console.error("Error fetching the calendar by title:", error);
        alert("Error fetching the calendar.");
      }
    }
  };

  if (loading) {
    return (
      <div className="admin-container">
        <Sidebar_Manager />
        <div className="main-content">
          <h2 className="heading">Loading...</h2>
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
        <div
          className="header"
          style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}
        >
          <h2 className="heading" style={{ marginRight: "201px" }}>
            List Calendar
          </h2>
          <Autocomplete
            style={{ width: "250px", marginRight: "5%" }}
            freeSolo
            options={suggestions.length > 0 ? suggestions : calendars}
            getOptionLabel={(option) =>
              typeof option === "string" ? option : option.title
            }
            inputValue={title}
            onInputChange={handleSearchInputChange}
            onChange={(event, newValue) => {
              if (typeof newValue === "string") {
                setTitle(newValue);
              } else if (newValue) {
                setTitle(newValue.title);
              }
            }}
            renderInput={(params) => (
              <TextField
                {...params}
                label="Search by name"
                variant="outlined"
                onKeyDown={handleSearchSubmit}
                InputProps={{
                  ...params.InputProps,
                  endAdornment: isLoadingSuggestions ? (
                    <CircularProgress color="inherit" size={20} />
                  ) : null,
                }}
              />
            )}
            renderOption={(props, option) => (
              <li {...props} key={typeof option === "string" ? option : option.id}>
                {typeof option === "string" ? option : option.title}
              </li>
            )}
          />
        </div>

        <div className="calendar-cards-container">
          {(suggestions.length > 0 ? suggestions : calendars).length > 0 ? (
            (suggestions.length > 0 ? suggestions : calendars).map((calendar) => (
              <div
                key={calendar.id}
                className="calendar-card"
                style={{ width: "300px", height: "150px", padding: "20px" }}
              >
                <div className="calendar-card-header">
                  <span className="status-dot" />
                  <span className="calendar-card-title">
                    {calendar.title}
                    {calendar.algorithm ? `, ${calendar.algorithm}` : ""}
                  </span>
                </div>
                <Link
                  to={`/manager/calendar/${calendar.id}`}
                  className="open-button"
                  style={{ backgroundColor: "#4CAF50" }}
                >
                  Open
                </Link>
              </div>
            ))
          ) : (
            <p>No calendar found.</p>
          )}
        </div>
      </div>
    </div>
  );
};

export default ListCalendar;
