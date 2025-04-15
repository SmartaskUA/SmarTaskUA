import React, { useEffect, useState } from "react";
import axios from "axios";
import { Link } from "react-router-dom";
import Sidebar_Manager from "../components/Sidebar_Manager";
import "../styles/Manager.css";
import BaseUrl from "../components/BaseUrl";
import { CircularProgress } from "@mui/material"; 

const CalendarCard = ({ title, status, time, link, buttonLabel, className, onClick, showLoader }) => (
  <div className={`calendar-card ${className}`} style={{ width: "300px", height: "160px", padding: "20px", position: "relative" }}>
    <div className="calendar-card-header">
      <span className={`status-dot ${status?.toLowerCase() || 'unknown'}`} />
      <span className="calendar-card-title" style={{ fontSize: "18px" }}>{title}</span>
    </div>
    {time && <span className="draft-time" style={{ fontSize: "14px" }}>{time}</span>}
    {link && buttonLabel && (
      <Link to={link} className={`open-button btn-${status?.toLowerCase() || 'default'}`} style={{ fontSize: "16px", padding: "10px 20px" }} onClick={onClick}>
        {buttonLabel}
      </Link>
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

const LastSeenSection = () => (
  <>
    <h3 className="section-title" style={{ marginTop: "20px"}}>Last Seen</h3>
    <div className="calendar-cards-container" style={{ gap: "30px" }}>
      <CalendarCard title="January, Algorithm X" status="green" link="/manager/calendar/abc123" buttonLabel="Open" className="completed-card" />
      <CalendarCard title="September, Algorithm Z" status="green" link="/manager/calendar/xyz456" buttonLabel="Open" className="completed-card" />
      <CalendarCard title="Another Calendar" status="green" link="/manager/calendar/def789" buttonLabel="Open" className="completed-card" />
    </div>
  </>
);

const NewCalendarSection = () => (
  <>
    <h3 className="section-title">New Calendar & Drafts</h3>
    <div className="cards-row" style={{ gap: "30px" }}>
      <CalendarCard title="New Calendar" status="blue" link="/manager/createCalendar" buttonLabel="Create" className="new-calendar-card" />
      <CalendarCard title="Draft Schedule 1" status="orange" time="10min ago" className="draft-card" />
      <CalendarCard title="Draft Schedule 2" status="orange" time="10min ago" className="draft-card" />
      <CalendarCard title="Draft Schedule 3" status="orange" time="15min ago" className="draft-card" />
    </div>
  </>
);

const CalendarsInProcessSection = () => {
  const [processingCalendars, setProcessingCalendars] = useState([]);
  const [errorMessage, setErrorMessage] = useState("");

  useEffect(() => {
    const fetchCalendars = async () => {
      try {
        const response = await axios.get(`${BaseUrl}/tasks`, {
          headers: { "Accept": "application/json" },
        });
        const rawData = response.data;
        let data = Array.isArray(rawData) ? rawData : Object.values(rawData);
        const filtered = data.filter(task => {
          const status = task.status ? task.status.toLowerCase() : "";
          return status === "in_progress" || status === "done";
        });
        setProcessingCalendars(filtered);
        setErrorMessage("");
      } catch (error) {
        setErrorMessage("Failed to load calendars. Please check the API connection.");
        console.error("Error fetching tasks:", error);
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
          processingCalendars.map((calendar) => {
            const status = calendar.status ? calendar.status.toLowerCase() : "";
            if (status === "in_progress") {
              return (
                <CalendarCard 
                  key={calendar.id} 
                  title={calendar.scheduleRequest?.title || "Unknown"} 
                  status="orange" 
                  time="In progress..." 
                  className="in-process"
                  showLoader={true}
                />
              );
            } else if (status === "done") {
              return (
                <CalendarCard 
                  key={calendar.id} 
                  title={calendar.scheduleRequest?.title || "Unknown"} 
                  status="green" 
                  time="Done" 
                  link={`/manager/calendar/${calendar.taskId}`} 
                  buttonLabel="Open"
                  className="done" 
                  showLoader={false}
                />
              );
            } else {
              return null;
            }
          })
        ) : (
          <p>No calendars in process</p>
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
        <LastSeenSection />
      </div>
    </div>
  );
};

export default Manager;
