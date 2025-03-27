import React from "react";
import { Link } from "react-router-dom";
import Sidebar_Manager from "../components/Sidebar_Manager";
import "../styles/Manager.css";

const CalendarCard = ({ title, status, time, link, buttonLabel, className }) => (
  <div className={`calendar-card ${className}`} style={{ width: "300px", height: "160px", padding: "20px" }}>
    <div className="calendar-card-header">
      <span className={`status-dot ${status}`} />
      <span className="calendar-card-title" style={{ fontSize: "18px" }}>{title}</span>
    </div>
    {time && <span className="draft-time" style={{ fontSize: "14px" }}>{time}</span>}
    {link && (
      <Link to={link} className={`open-button btn-${status}`} style={{ fontSize: "16px", padding: "10px 20px" }}>
        {buttonLabel}
      </Link>
    )}
  </div>
);

const LastSeenCard = ({ title, link }) => (
  <CalendarCard title={title} status="green" link={link} buttonLabel="Open" className="completed-card" />
);

const LastSeenSection = () => (
  <>
    <h3 className="section-title">Last Seen</h3>
    <div className="calendar-cards-container" style={{ gap: "30px" }}>
      <LastSeenCard title="January, Algorithm X" link="/manager/calendar/abc123" />
      <LastSeenCard title="September, Algorithm Z" link="/manager/calendar/xyz456" />
      <LastSeenCard title="Another Calendar" link="/manager/calendar/def789" />
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

const CalendarsInProcessSection = () => (
  <>
    <h3 className="section-title">Calendars in Process</h3>
    <div className="calendar-cards-container" style={{ gap: "30px" }}>
      <CalendarCard title="Processing 1" status="orange" time="In progress..." className="in-process" />
      <CalendarCard title="Processing 2" status="orange" time="In progress..." className="in-process" />
    </div>
  </>
);

const ManagerHome = () => {
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

export default ManagerHome;
