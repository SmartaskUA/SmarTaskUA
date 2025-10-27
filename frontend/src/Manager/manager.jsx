import React, { useEffect, useState } from "react";
import axios from "axios";
import { useNavigate } from "react-router-dom";
import Sidebar_Manager from "../components/Sidebar_Manager";
import "../styles/Manager.css";
import BaseUrl from "../components/BaseUrl";
import { CircularProgress } from "@mui/material";

/* =========================
   🧱 Calendar Card Component
   ========================= */
const CalendarCard = ({
  title,
  algorithm,
  status,
  time,
  onClick,
  buttonLabel,
  className,
  showLoader,
  buttonColor,
  showFailedTag,
  showCompletedTag,
}) => {
  const getBorderStyle = () => {
    if (showFailedTag) return "1px solid #dc3545";
    if (status === "orange") return "2px dashed #FFA500";
    return "1px solid #ddd";
  };

  const getDotColor = () => {
    if (status === "orange") return "#FFA500";
    if (status === "blue") return "#007BFF";
    if (status === "failed") return "#dc3545";
    return "#28a745";
  };

  return (
    <div
      className={`calendar-card ${className || ""}`}
      style={{
        width: "300px",
        height: "165px",
        padding: "20px",
        position: "relative",
        display: "flex",
        flexDirection: "column",
        justifyContent: "space-between",
        border: getBorderStyle(),
        borderRadius: "8px",
        boxShadow: "0 2px 5px rgba(0,0,0,0.1)",
      }}
    >
      {/* Tags */}
      {showFailedTag && (
        <div
          style={{
            position: "absolute",
            top: "8px",
            right: "10px",
            backgroundColor: "#dc3545",
            color: "white",
            padding: "2px 8px",
            borderRadius: "5px",
            fontSize: "0.75rem",
            fontWeight: "bold",
          }}
        >
          FAILED
        </div>
      )}

      {showCompletedTag && (
        <div
          style={{
            position: "absolute",
            top: "8px",
            right: "10px",
            backgroundColor: "#28a745",
            color: "white",
            padding: "2px 8px",
            borderRadius: "5px",
            fontSize: "0.75rem",
            fontWeight: "bold",
          }}
        >
          COMPLETED
        </div>
      )}

      {/* Card Header */}
      <div style={{ display: "flex", flexDirection: "row", alignItems: "flex-start" }}>
        <span
          className="status-dot"
          style={{
            marginTop: "4%",
            backgroundColor: getDotColor(),
          }}
        />
        <div style={{ marginLeft: "10px" }}>
          <div
            className="calendar-card-title"
            style={{
              fontSize: "1.3rem",
              fontWeight: "600",
              color: "#333",
            }}
          >
            {title}
          </div>
          {algorithm && (
            <div
              className="calendar-card-algorithm"
              style={{
                fontSize: "1rem",
                color: "#777",
                marginTop: "5%",
                marginLeft: "3%",
              }}
            >
              {algorithm}
            </div>
          )}
        </div>
      </div>

      {time && <span className="draft-time" style={{ fontSize: "14px" }}>{time}</span>}

      {/* Button */}
      {!showFailedTag && buttonLabel && (
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
            cursor: "pointer",
          }}
          onClick={onClick}
        >
          {buttonLabel}
        </button>
      )}

      {/* Loader */}
      {showLoader && (
        <div
          style={{
            position: "absolute",
            top: "60%",
            left: "50%",
            transform: "translate(-50%, -50%)",
          }}
        >
          <CircularProgress color="warning" />
        </div>
      )}
    </div>
  );
};

/* ===============================
   🧩 Last Processed Section (3s poll)
   =============================== */
const LastProcessedSection = ({ refreshTrigger }) => {
  const [lastTasks, setLastTasks] = useState([]);
  const navigate = useNavigate();

  useEffect(() => {
    let isMounted = true;
    let inFlight = false;
    const controller = new AbortController();

    const fetchLastTasks = async () => {
      if (inFlight) return;
      inFlight = true;
      try {
        const response = await axios.get(`${BaseUrl}/tasks`, { signal: controller.signal });
        const tasks = response.data;

        const recent = tasks
          .filter((t) => t.status === "COMPLETED" || t.status === "FAILED")
          .sort((a, b) => new Date(b.updatedAt) - new Date(a.updatedAt))
          .slice(0, 6);

        const validTasks = await Promise.all(
          recent.map(async (task) => {
            if (task.status === "FAILED") return task;
            const title = task.scheduleRequest?.title;
            try {
              const res = await axios.get(`${BaseUrl}/schedules/${title}`, { signal: controller.signal });
              return res.data?.id ? task : null;
            } catch {
              return null;
            }
          })
        );

        if (isMounted) setLastTasks(validTasks.filter(Boolean).slice(0, 3));
      } catch (err) {
        if (err.name !== "CanceledError") {
          console.error("Erro ao buscar últimas tarefas:", err);
        }
      } finally {
        inFlight = false;
      }
    };

    fetchLastTasks();
    const id = setInterval(fetchLastTasks, 3000);

    return () => {
      isMounted = false;
      controller.abort();
      clearInterval(id);
    };
  }, [refreshTrigger]);

  const handleOpenCalendar = async (title) => {
    try {
      const response = await axios.get(`${BaseUrl}/schedules/${title}`);
      const calendarId = response.data?.id;
      if (calendarId) navigate(`/manager/calendar/${calendarId}`);
      else alert("Calendário não encontrado.");
    } catch (error) {
      console.error("Erro ao abrir calendário:", error);
      alert("Erro ao abrir calendário.");
    }
  };

  return (
    <>
      <h3 className="section-title" style={{ marginTop: "20px" }}>
        Latest Results
      </h3>
      <div className="calendar-cards-container" style={{ gap: "30px" }}>
        {lastTasks.length === 0 ? (
          <p style={{ color: "#777", fontStyle: "italic" }}>No processed calendars found.</p>
        ) : (
          lastTasks.map((task) => {
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
                buttonLabel={isCompleted ? "Open" : null}
                buttonColor={isCompleted ? "#4CAF50" : null}
                className={isFailed ? "failed-card" : ""}
                showFailedTag={isFailed}
                showCompletedTag={isCompleted}
                onClick={isCompleted ? () => handleOpenCalendar(title) : null}
              />
            );
          })
        )}
      </div>
    </>
  );
};

/* ============================
   🧠 Calendars In Progress
   ============================ */
const CalendarsInProcessSection = ({ setRefreshTrigger }) => {
  const [processingCalendars, setProcessingCalendars] = useState([]);
  const [errorMessage, setErrorMessage] = useState("");

  useEffect(() => {
    let isMounted = true;

    const fetchCalendars = async () => {
      try {
        const response = await axios.get(`${BaseUrl}/tasks`);
        const data = response.data;

        const stillProcessing = data.filter((task) => {
          const s = task.status?.toLowerCase();
          return s === "in_progress" || s === "pending";
        });

        if (!isMounted) return;

        // detect finished ones
        const justFinished = processingCalendars.filter(
          (old) => !stillProcessing.find((newT) => newT.taskId === old.taskId)
        );

        if (justFinished.length > 0) {
          setRefreshTrigger((prev) => prev + 1);
        }

        // only update if different
        const same =
          JSON.stringify(stillProcessing.map((t) => t.taskId).sort()) ===
          JSON.stringify(processingCalendars.map((t) => t.taskId).sort());

        if (!same) {
          setProcessingCalendars(stillProcessing);
        }

        setErrorMessage("");
      } catch (err) {
        if (isMounted) {
          console.error("Erro ao atualizar tarefas em progresso:", err);
          setErrorMessage("Erro ao atualizar tarefas em progresso.");
        }
      }
    };

    fetchCalendars();
    const interval = setInterval(fetchCalendars, 3000);

    return () => {
      isMounted = false;
      clearInterval(interval);
    };
  }, [setRefreshTrigger]);

  return (
    <>
      <h3 className="section-title">Calendars in Progress</h3>
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
          <p style={{ color: "#777", fontStyle: "italic" }}>No calendars in progress</p>
        )}
      </div>
    </>
  );
};

/* ===============================
   🏠 New Calendar Section
   =============================== */
const NewCalendarSection = () => (
  <>
    <h3 className="section-title">Home</h3>
    <div className="cards-row" style={{ gap: "30px" }}>
      <CalendarCard
        title="New Schedule"
        status="blue"
        buttonLabel="Create"
        buttonColor="#007BFF"
        onClick={() => (window.location.href = "/manager/createCalendar")}
        className="new-calendar-card"
      />
    </div>
  </>
);

/* ==========================
   🧭 Manager Main Component
   ========================== */
const Manager = () => {
  const [refreshTrigger, setRefreshTrigger] = useState(0);

  return (
    <div className="admin-container">
      <Sidebar_Manager />
      <div className="main-content" style={{ padding: "40px" }}>
        <NewCalendarSection />
        <CalendarsInProcessSection setRefreshTrigger={setRefreshTrigger} />
        <LastProcessedSection refreshTrigger={refreshTrigger} />
      </div>
    </div>
  );
};

export default Manager;
