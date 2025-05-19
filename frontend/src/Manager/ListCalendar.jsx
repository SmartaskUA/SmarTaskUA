import React, { useEffect, useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import Sidebar_Manager from "../components/Sidebar_Manager";
import baseurl from "../components/BaseUrl";
import axios from "axios";
import "../styles/Manager.css";
import NotificationSnackbar from "../components/manager/NotificationSnackbar";
import EmptySVG from "../assets/images/Empty-amico.svg";
import {
  Autocomplete,
  TextField,
  CircularProgress,
  Button,
  Snackbar,
  Alert,
  Dialog,
  DialogActions,
  DialogContent,
  DialogContentText,
  DialogTitle,
  IconButton,
} from "@mui/material";
import { Close } from "@mui/icons-material";

const ListCalendar = () => {
  const [calendars, setCalendars] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [title, setTitle] = useState("");
  const [suggestions, setSuggestions] = useState([]);
  const [isLoadingSuggestions, setIsLoadingSuggestions] = useState(false);
  const [successOpen, setSuccessOpen] = useState(false);
  const [errorOpen, setErrorOpen] = useState(false);
  const [calendarToDelete, setCalendarToDelete] = useState(null);
  const [confirmDialogOpen, setConfirmDialogOpen] = useState(false);
  const [confirmDeleteAllOpen, setConfirmDeleteAllOpen] = useState(false); 
  const [hoveredCardId, setHoveredCardId] = useState(null);

  const navigate = useNavigate();

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

  useEffect(() => {
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
      const calendarMatch = calendars.find(
        (calendar) => calendar.title.toLowerCase() === title.toLowerCase()
      );
      if (!calendarMatch) return alert("Calendar does not exist.");
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

  const handleOpenConfirmDeleteAll = () => {
    setConfirmDeleteAllOpen(true);
  };

  const handleCancelDeleteAll = () => {
    setConfirmDeleteAllOpen(false);
  };

  const handleConfirmDeleteAll = async () => {
    setConfirmDeleteAllOpen(false);
    try {
      await axios.delete(`${baseurl}/clearnreset/clean-schedules`);
      setSuccessOpen(true);
      fetchCalendars();
    } catch (err) {
      console.error("Erro ao apagar todos os schedules:", err);
      alert("Erro ao apagar schedules: " + (err.response?.data?.error || err.message));
      setErrorOpen(true);
    }
  };

  const confirmDeleteCalendar = (calendar) => {
    setCalendarToDelete(calendar);
    setConfirmDialogOpen(true);
  };

  const handleConfirmDelete = async () => {
    try {
      await axios.delete(`${baseurl}/schedules/delete/id/${calendarToDelete.id}`);
      setSuccessOpen(true);
      setConfirmDialogOpen(false);
      setCalendarToDelete(null);
      fetchCalendars();
    } catch (err) {
      console.error("Erro ao apagar calendário:", err);
      setErrorOpen(true);
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
        <div className="header" style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
          <h2 className="heading" style={{ marginRight: "201px", marginLeft: "1%" }}>
            List Schedules
          </h2>

          <Button style={{marginLeft: "40%", height: "100%"}} 
            variant="contained"
            color="error"
            onClick={handleOpenConfirmDeleteAll}
          >
            Delete All Schedules
          </Button>

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
        {calendars.length === 0 && !loading && !error && (
              <div style={{
                display: "flex",
                flexDirection: "column",
                alignItems: "center",
                justifyContent: "center",
                height: "80%", 
                marginTop: "50px",
              }}
            >
              <img
                src={EmptySVG}
                alt="No schedules"
                style={{ width: 400, height: 400, marginBottom: 20 }}
              />
                <div style={{ fontSize: 18, color: "#666" }}>No schedules created yet</div>
              </div>
            )}


        <div className="calendar-cards-container">
          {(suggestions.length > 0 ? suggestions : calendars).map((calendar) => (
            <div
              key={calendar.id}
              className="calendar-card"
              onMouseEnter={() => setHoveredCardId(calendar.id)}
              onMouseLeave={() => setHoveredCardId(null)}
              style={{
                width: "300px",
                height: "165px",
                padding: "20px",
                display: "flex",
                flexDirection: "column",
                justifyContent: "space-between",
                border: "1px solid #ddd",
                borderRadius: "8px",
                margin: "0.65%",
                boxShadow: "0 2px 5px rgba(0,0,0,0.1)",
                position: "relative",
              }}
            >
              <IconButton
                size="small"
                onClick={() => confirmDeleteCalendar(calendar)}
                sx={{
                  position: "absolute",
                  top: 6,
                  right: 6,
                  backgroundColor:
                    hoveredCardId === calendar.id ? "#ff5252" : "#e0e0e0",
                  color: hoveredCardId === calendar.id ? "#fff" : "#555",
                  "&:hover": {
                    backgroundColor: "#ff1744",
                  },
                  width: "20px",
                  height: "20px",
                  padding: "2px",
                }}
              >
                <Close fontSize="10px" />
              </IconButton>

              <div style={{ display: "flex", flexDirection: "row", alignItems: "flex-start" }}>
                <span className="status-dot" style={{ marginTop: "4%" }} />
                <div style={{ marginLeft: "10px" }}>
                  <div
                    className="calendar-card-title"
                    style={{ fontSize: "1.3rem", fontWeight: "600", color: "#333" }}
                  >
                    {calendar.title}
                  </div>
                  <div
                    className="calendar-card-algorithm"
                    style={{ fontSize: "1rem", color: "#777", marginTop: "5%", marginLeft: "3%" }}
                  >
                    {calendar.algorithm || "No algorithm specified"}
                  </div>
                </div>
              </div>

              <div style={{ display: "flex", justifyContent: "center" }}>
                <Link
                  to={`/manager/calendar/${calendar.id}`}
                  className="open-button"
                  style={{
                    backgroundColor: "#4CAF50",
                    color: "#fff",
                    padding: "8px 35%",
                    textAlign: "center",
                    textDecoration: "none",
                    borderRadius: "8px",
                    fontWeight: "bold",
                    fontSize: "1rem",
                  }}
                >
                  Open
                </Link>
              </div>
            </div>
          ))}
        </div>

        <Dialog open={confirmDialogOpen} onClose={() => setConfirmDialogOpen(false)}>
          <DialogTitle>Confirm Deletion</DialogTitle>
          <DialogContent>
            <DialogContentText>
              Are you sure you want to delete the calendar "{calendarToDelete?.title}"?
            </DialogContentText>
          </DialogContent>
          <DialogActions>
            <Button onClick={() => setConfirmDialogOpen(false)} color="primary">
              Cancel
            </Button>
            <Button onClick={handleConfirmDelete} color="error">
              Delete
            </Button>
          </DialogActions>
        </Dialog>

        <Dialog open={confirmDeleteAllOpen} onClose={handleCancelDeleteAll}>
          <DialogTitle>Confirm Deletion</DialogTitle>
          <DialogContent>
            <DialogContentText>
              Are you sure you want to delete all schedules?
            </DialogContentText>
          </DialogContent>
          <DialogActions>
            <Button onClick={handleCancelDeleteAll} color="primary">
              Cancel
            </Button>
            <Button onClick={handleConfirmDeleteAll} color="error">
              Delete All
            </Button>
          </DialogActions>
        </Dialog>

        <NotificationSnackbar
          open={successOpen}
          severity="success"
          message="Task Requested Successfully!"
          onClose={() => setSuccessOpen(false)}
        />

        <NotificationSnackbar
          open={errorOpen}
          severity="error"
          message="Failed to create calendar. Try again."
          onClose={() => setErrorOpen(false)}
        />
      </div>
    </div>
  );
};

export default ListCalendar;
