import React, { useEffect, useState } from "react";
import axios from "axios";
import { Link } from "react-router-dom";
import Sidebar_Manager from "../components/Sidebar_Manager";
import "../styles/Manager.css";
import BaseUrl from "../components/BaseUrl";

const CalendarCard = ({ title, status, time, link, buttonLabel, className, onClick }) => (
  <div className={`calendar-card ${className}`} style={{ width: "300px", height: "160px", padding: "20px" }}>
    <div className="calendar-card-header">
      <span className={`status-dot ${status?.toLowerCase() || 'unknown'}`} />
      <span className="calendar-card-title" style={{ fontSize: "18px" }}>{title}</span>
    </div>
    {time && <span className="draft-time" style={{ fontSize: "14px" }}>{time}</span>}
    {link && (
      <Link to={link} className={`open-button btn-${status?.toLowerCase() || 'default'}`} style={{ fontSize: "16px", padding: "10px 20px" }} onClick={onClick}>
        {buttonLabel}
      </Link>
    )}
  </div>
);

const LastSeenSection = () => (
  <>
    <h3 className="section-title">Last Seen</h3>
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

        const data = Array.isArray(response.data) ? response.data : Object.values(response.data);
        const inProcess = data.filter(task => task.status && task.status.toLowerCase() === "in_progress");
        setProcessingCalendars(inProcess);
        setErrorMessage("");
      } catch (error) {
        setErrorMessage("Failed to load calendars. Please check the API connection.");
      }
    };

    fetchCalendars();
    const interval = setInterval(fetchCalendars, 3000);
    return () => clearInterval(interval);
  }, []);

  const handleCalendarClick = (calendarId) => {
    setProcessingCalendars(prevCalendars => prevCalendars.filter(calendar => calendar.id !== calendarId));
  };

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
              status="orange" 
              time="In progress..." 
              className="in-process" 
              link={`/manager/calendar/${calendar.id}`} 
              buttonLabel="View Details"
              onClick={() => handleCalendarClick(calendar.id)}
            />
          ))
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
