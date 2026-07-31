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

  const isFailedCalendar = (calendar) => calendar.itemType === "failed-task";
  const isInProgressCalendar = (calendar) => calendar.itemType === "in-progress-task";

  const normalizeFailedTask = (task) => ({
    id: task.taskId,
    taskId: task.taskId,
    itemType: "failed-task",
    title: task.scheduleRequest?.title || "Failed schedule",
    algorithm: task.scheduleRequest?.algorithm || "No algorithm specified",
    status: task.status,
    updatedAt: task.updatedAt,
    failureSummary: task.failureSummary,
    hasReport: Boolean(task.reportArtifacts?.pdf),
  });

  const normalizeInProgressTask = (task) => ({
    id: task.taskId,
    taskId: task.taskId,
    itemType: "in-progress-task",
    title: task.scheduleRequest?.title || "Untitled schedule",
    algorithm: task.scheduleRequest?.algorithm || "No algorithm specified",
    status: task.status,
    updatedAt: task.updatedAt,
  });

  const handleDownloadReport = (taskId) => {
    window.open(`${baseurl}/tasks/${taskId}/report/pdf`, "_blank", "noopener,noreferrer");
  };

  const fetchCalendars = async () => {
    try {
      const [schedulesResponse, tasksResponse] = await Promise.all([
        axios.get(`${baseurl}/schedules/fetch`),
        axios.get(`${baseurl}/tasks`),
      ]);

      if (schedulesResponse.data) {
        const schedules = schedulesResponse.data.map((schedule) => ({
          ...schedule,
          itemType: "schedule",
        }));
        const completedTitles = new Set(schedules.map((schedule) => schedule.title));

        const failedTasks = (tasksResponse.data || [])
          .filter((task) => task.status === "FAILED" || task.status === "FAILED_VALIDATION")
          .map(normalizeFailedTask);

        const inProgressTasks = (tasksResponse.data || [])
          .filter((task) => task.status === "PENDING" || task.status === "IN_PROGRESS")
          .filter((task) => !completedTitles.has(task.scheduleRequest?.title))
          .map(normalizeInProgressTask);

        setCalendars([...failedTasks, ...inProgressTasks, ...schedules]);
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
      if (isFailedCalendar(calendarMatch)) return alert("This schedule failed and has no calendar to open.");
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
                minHeight: isFailedCalendar(calendar) ? "220px" : "165px",
                padding: "20px",
                display: "flex",
                flexDirection: "column",
                justifyContent: "flex-start",
                gap: "16px",
                border: isFailedCalendar(calendar)
                  ? "1px solid #dc3545"
                  : isInProgressCalendar(calendar)
                  ? "1px solid #006FD5"
                  : "1px solid #ddd",
                borderRadius: "8px",
                margin: "0.65%",
                boxShadow: "0 2px 5px rgba(0,0,0,0.1)",
                position: "relative",
                boxSizing: "border-box",
              }}
            >
              {!isFailedCalendar(calendar) && !isInProgressCalendar(calendar) && (
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
              )}

              <div className="calendar-card-header manager-result-card-header">
                <span
                  className="status-dot"
                  style={{
                    marginTop: "8px",
                    backgroundColor: isFailedCalendar(calendar)
                      ? "#dc3545"
                      : isInProgressCalendar(calendar)
                      ? "#006FD5"
                      : undefined,
                  }}
                />
                <div className="calendar-card-main">
                  <div
                    className="calendar-card-title"
                    style={{ fontSize: "1.05rem", fontWeight: "600", color: "#333" }}
                  >
                    {calendar.title}
                  </div>
                  <div
                    className="calendar-card-algorithm"
                    style={{ fontSize: "0.78rem", color: "#777", marginTop: "8px" }}
                  >
                    {calendar.algorithm || "No algorithm specified"}
                  </div>
                </div>
                {isFailedCalendar(calendar) && (
                  <div className="calendar-card-tag calendar-card-tag-failed">
                    {calendar.status === "FAILED_VALIDATION" ? "VALIDATION" : "FAILED"}
                  </div>
                )}
              </div>

              {isInProgressCalendar(calendar) && (
                <div
                  style={{
                    display: "flex",
                    alignItems: "center",
                    gap: "8px",
                    color: "#006FD5",
                    fontSize: "0.85rem",
                  }}
                >
                  <CircularProgress size={16} thickness={5} sx={{ color: "#006FD5" }} />
                  {calendar.status === "IN_PROGRESS" ? "Calculating schedule..." : "Queued..."}
                </div>
              )}

              {isFailedCalendar(calendar) && calendar.failureSummary && (
                <div
                  style={{
                    color: "#5f2120",
                    backgroundColor: "#fdecea",
                    borderRadius: "6px",
                    padding: "8px 10px",
                    fontSize: "0.78rem",
                    lineHeight: "1.3",
                    maxHeight: "64px",
                    overflow: "hidden",
                  }}
                  title={calendar.failureSummary}
                >
                  {calendar.failureSummary}
                </div>
              )}

              {!isInProgressCalendar(calendar) && (
                <div style={{ display: "flex", justifyContent: "center" }}>
                  {isFailedCalendar(calendar) ? (
                    calendar.hasReport && (
                      <button
                        className="open-button"
                        style={{
                          backgroundColor: "#dc3545",
                          color: "#fff",
                          padding: "8px 18px",
                          textAlign: "center",
                          border: "none",
                          borderRadius: "8px",
                          fontWeight: "bold",
                          fontSize: "0.95rem",
                          cursor: "pointer",
                          width: "100%",
                        }}
                        onClick={() => handleDownloadReport(calendar.taskId)}
                      >
                        Download PDF
                      </button>
                    )
                  ) : (
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
                  )}
                </div>
              )}
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
