import React from "react";
import ShiftCalendarView from "./ShiftCalendarView";
import HourlyCalendarView from "./HourlyCalendarView";

const CalendarTable = ({
  data,
  monthColumns,
  holidayMap,
  scheduleType,
  employees,
}) => {
  const normalizedType = String(scheduleType || "").toLowerCase();
  const isHourly = normalizedType === "horas" || normalizedType === "hours";

  if (isHourly) {
    return (
      <HourlyCalendarView
        data={data}
        monthColumns={monthColumns}
        employees={employees}
      />
    );
  }

  return (
    <ShiftCalendarView
      data={data}
      monthColumns={monthColumns}
      holidayMap={holidayMap}
      employees={employees}
    />
  );
};

export default CalendarTable;
