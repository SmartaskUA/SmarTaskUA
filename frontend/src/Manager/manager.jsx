import React, { useEffect, useState } from "react";
import axios from "axios";
import { useNavigate } from "react-router-dom";
import Sidebar_Manager from "../components/Sidebar_Manager";
import "../styles/Manager.css";
import BaseUrl from "../components/BaseUrl";
import { CircularProgress } from "@mui/material";

const CalendarCard = ({ title, algorithm, status, time, onClick, buttonLabel, className, showLoader, buttonColor, showFailedTag }) => (
  <div className={`calendar-card ${className || ""}`} style={{
    width: "300px",
    height: "165px",
    padding: "20px",
    position: "relative",
    display: "flex",
    flexDirection: "column",
    justifyContent: "space-between",
    border: "1px solid #ddd",
    borderRadius: "8px",
    boxShadow: "0 2px 5px rgba(0,0,0,0.1)"
  }}>
    {showFailedTag && (
      <div style={{
        position: "absolute",
        top: "8px",
        right: "10px",
        backgroundColor: "#dc3545",
        color: "white",
        padding: "2px 8px",
        borderRadius: "5px",
        fontSize: "0.75rem",
        fontWeight: "bold"
      }}>
        FAILED
      </div>
    )}

    <div style={{ display: "flex", flexDirection: "row", alignItems: "flex-start" }}>
      <span
        className="status-dot"
        style={{ marginTop: "4%", backgroundColor: status === "failed" ? "#dc3545" : "#28a745" }}
      />
      <div style={{ marginLeft: "10px" }}>
        <div className="calendar-card-title" style={{ fontSize: "1.3rem", fontWeight: "600", color: "#333" }}>
          {title}
        </div>
        {algorithm && (
          <div className="calendar-card-algorithm" style={{ fontSize: "1rem", color: "#777", marginTop: "5%", marginLeft: "3%" }}>
            {algorithm}
          </div>
        )}
      </div>
    </div>

    {time && <span className="draft-time" style={{ fontSize: "14px" }}>{time}</span>}

    {buttonLabel && (
      <button
        className="open-button"
        style={{
          backgroundColor: buttonColor || "#4CAF50",
          color: "#fff",
          padding: "8px 35%",
          textAlign: "center",
          border: "none",
          borderRadius: "8px",
          fontWeight: "bold",
          fontSize: "1rem",
          cursor: "pointer"
        }}
        onClick={onClick}
      >
        {buttonLabel}
      </button>
    )}

    {showLoader && (
      <div style={{
        position: "absolute",
        top: "50%",
        left: "50%",
        transform: "translate(-50%, -50%)"
      }}>
        <CircularProgress color="warning" />
      </div>
    )}
  </div>
);

const LastProcessedSection = () => {
  const [lastTasks, setLastTasks] = useState([]);
  const navigate = useNavigate();

  useEffect(() => {
    const fetchLastTasks = async () => {
      try {
        const response = await axios.get(`${BaseUrl}/tasks`);
        const tasks = response.data;

        const sorted = tasks
          .filter(task => task.status === "COMPLETED" || task.status === "FAILED")
          .sort((a, b) => new Date(b.updatedAt) - new Date(a.updatedAt))
          .slice(0, 3);

        setLastTasks(sorted);
      } catch (err) {
        console.error("Erro ao buscar últimas tarefas:", err);
      }
    };

    fetchLastTasks();
  }, []);

  const handleOpenCalendar = async (title) => {
    try {
      const response = await axios.get(`${BaseUrl}/schedules/${title}`);
      const calendarId = response.data?.id;
      if (calendarId) {
        navigate(`/manager/calendar/${calendarId}`);
      } else {
        alert("Calendário não encontrado.");
      }
    } catch (error) {
      console.error("Erro ao abrir calendário:", error);
      alert("Erro ao abrir calendário.");
    }
  };

  return (
    <>
      <h3 className="section-title" style={{ marginTop: "20px" }}>Last Processed</h3>
      <div className="calendar-cards-container" style={{ gap: "30px" }}>
        {lastTasks.map((task) => {
          const { status, taskId, scheduleRequest } = task;
          const title = scheduleRequest?.title || "No Title";
          const algorithm = scheduleRequest?.algorithm || "";
          const isCompleted = status === "COMPLETED";
          const isFailed = status === "FAILED";

          return (
            <CalendarCard
              key={taskId}
              title={title}
              algorithm={algorithm}
              status={status.toLowerCase()}
              buttonLabel={isCompleted ? "Open" : "Delete"}
              buttonColor={isCompleted ? "#4CAF50" : "#f44336"}
              className={isFailed ? "failed-card" : ""}
              showFailedTag={isFailed}
              onClick={
                isCompleted
                  ? () => handleOpenCalendar(title)
                  : () => alert(`TODO: Delete task ${taskId}`)
              }
            />
          );
        })}
      </div>
    </>
  );
};

const NewCalendarSection = () => (
  <>
    <h3 className="section-title">New Calendar</h3>
    <div className="cards-row" style={{ gap: "30px" }}>
      <CalendarCard
        title="New Calendar"
        status="blue"
        buttonLabel="Create"
        buttonColor="#007BFF"
        onClick={() => window.location.href = "/manager/createCalendar"}
        className="new-calendar-card"
      />
    </div>
  </>
);

const CalendarsInProcessSection = () => {
  const [processingCalendars, setProcessingCalendars] = useState([]);
  const [errorMessage, setErrorMessage] = useState("");

  useEffect(() => {
    const fetchCalendars = async () => {
      try {
        const response = await axios.get(`${BaseUrl}/tasks`);
        const data = response.data;
        const filtered = data.filter(task =>
          ["in_progress", "pending"].includes(task.status?.toLowerCase())
        );
        setProcessingCalendars(filtered);
        setErrorMessage("");
      } catch (error) {
        console.error("Error fetching tasks:", error);
        setErrorMessage("Failed to load calendars. Please check the API connection.");
      }
    };

    fetchCalendars();
    const interval = setInterval(fetchCalendars, 3000);
    return () => clearInterval(interval);
  }, []);

  return (
    <>
      <h3 className="section-title">Calendars in Process</h3>
      <div className="calendar-cards-container" style={{ gap: "30px" }}>
        {errorMessage ? (
          <p style={{ color: "red" }}>{errorMessage}</p>
        ) : processingCalendars.length > 0 ? (
          processingCalendars.map((calendar) => (
            <CalendarCard
              key={calendar.id}
              title={calendar.scheduleRequest?.title || "Unknown"}
              algorithm={calendar.scheduleRequest?.algorithm}
              status="orange"
              time="In progress..."
              className="in-process"
              showLoader={true}
            />
          ))
        ) : (
          <p>No calendars in progress</p>
        )}
      </div>
    </>
  );
};

const Manager = () => {
  return (
    <div className="admin-container">
      <Sidebar_Manager />
      <div className="main-content" style={{ padding: "40px" }}>
        <NewCalendarSection />
        <CalendarsInProcessSection />
        <LastProcessedSection />
      </div>
    </div>
  );
};

export default Manager;
