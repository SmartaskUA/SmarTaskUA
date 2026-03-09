const MONTH_NAMES = [
  "January",
  "February",
  "March",
  "April",
  "May",
  "June",
  "July",
  "August",
  "September",
  "October",
  "November",
  "December",
];

const WEEKDAY_NAMES = ["Sun", "Mon", "Tue", "Wed", "Thu", "Fri", "Sat"];

const OFF_MARKERS = new Set(["", "0", "OFF", "DO", "FDO"]);
const VACATION_MARKERS = new Set(["F", "VAC", "VACATION"]);
const UNAVAILABLE_MARKERS = new Set(["NOT", "MED"]);
const WARNING_MARKERS = new Set(["UNASSIGNED"]);

const SHIFT_PATTERN = /^([MTN])[_-]([A-Z])$/i;
const LEGACY_HOURLY_PATTERN =
  /^\s*(\d{1,2}(?:\.\d+)?)\s*-\s*(\d{1,2}(?:\.\d+)?)(?:\s*-\s*(\d{1,2}(?:\.\d+)?))?\s*[_-]\s*([A-Za-z][A-Za-z0-9]*)\s*$/;

const formatTeamLabel = (team) => {
  if (team == null) return "";
  if (typeof team === "string") return team.trim();
  if (typeof team === "object") {
    return String(team.name || team.code || team.id || "").trim();
  }
  return String(team).trim();
};

export const buildScheduleColumns = (headerRow = [], fallbackYear = new Date().getFullYear()) => {
  const labels = Array.isArray(headerRow) ? headerRow.slice(1) : [];
  return labels.map((label, index) => {
    const date = parseScheduleDate(label, fallbackYear, index + 1);
    return {
      key: `${date.toISOString().slice(0, 10)}-${index}`,
      raw: label,
      date,
      month: date.getMonth() + 1,
      monthName: MONTH_NAMES[date.getMonth()],
      day: date.getDate(),
      weekday: WEEKDAY_NAMES[date.getDay()],
      dayOfYear: index + 1,
      index,
    };
  });
};

export const buildMonthOptions = (columns = [], fallbackYear = new Date().getFullYear()) => {
  if (!columns.length) {
    return MONTH_NAMES.map((label, index) => ({
      value: index + 1,
      label,
      year: fallbackYear,
      count: new Date(fallbackYear, index + 1, 0).getDate(),
    }));
  }

  const months = new Map();
  columns.forEach((column) => {
    const current = months.get(column.month);
    if (current) {
      current.count += 1;
      return;
    }
    months.set(column.month, {
      value: column.month,
      label: column.monthName,
      year: column.date.getFullYear(),
      count: 1,
    });
  });
  return Array.from(months.values()).sort((a, b) => a.value - b.value);
};

export const inferPreferredMonth = (data = [], columns = []) => {
  if (!columns.length) return 1;
  const rows = Array.isArray(data) ? data.slice(1) : [];
  for (const column of columns) {
    const hasWork = rows.some((row) => isWorkingCell(row?.[column.index + 1]));
    if (hasWork) {
      return column.month;
    }
  }
  return columns[0].month;
};

export const resolveEmployeeDisplay = (employeeId, rowIndex, employees = []) => {
  const normalizedId = String(employeeId ?? "").trim();
  const byId = employees.find((employee) => {
    const candidates = [
      employee?.id,
      employee?._id,
      employee?.employee_id,
      employee?.employeeId,
      employee?.name,
    ];
    return candidates.some((candidate) => String(candidate ?? "").trim() === normalizedId);
  });
  const fallback = byId || employees[rowIndex] || null;
  const name = String(fallback?.name || normalizedId || `Employee ${rowIndex + 1}`).trim();
  const subtitle =
    normalizedId && normalizedId !== name
      ? normalizedId
      : String(fallback?.id || fallback?._id || "").trim();
  const teams = Array.isArray(fallback?.teams)
    ? fallback.teams.map(formatTeamLabel).filter(Boolean)
    : [];
  return {
    id: normalizedId || String(rowIndex + 1),
    name,
    subtitle,
    teams,
  };
};

export const classifyScheduleCell = (value) => {
  const text = String(value ?? "").trim();
  const normalized = text.toUpperCase();

  if (OFF_MARKERS.has(normalized)) {
    return { kind: "off", label: normalized === "DO" ? "Day Off" : normalized === "FDO" ? "Fixed Off" : "Off" };
  }
  if (VACATION_MARKERS.has(normalized)) {
    return { kind: "vacation", label: "Vacation" };
  }
  if (UNAVAILABLE_MARKERS.has(normalized)) {
    return { kind: "unavailable", label: normalized === "MED" ? "Medical" : "Unavailable" };
  }
  if (WARNING_MARKERS.has(normalized)) {
    return { kind: "warning", label: "Unassigned" };
  }

  const shiftMatch = text.match(SHIFT_PATTERN);
  if (shiftMatch) {
    return {
      kind: "shift",
      shift: shiftMatch[1].toUpperCase(),
      team: shiftMatch[2].toUpperCase(),
      raw: text,
    };
  }

  const sisqualSegments = parseTaggedHourlySegments(text);
  if (sisqualSegments.length) {
    return {
      kind: "hourly",
      segments: sisqualSegments,
      raw: text,
    };
  }

  const legacyHourly = parseLegacyHourlyBlock(text);
  if (legacyHourly) {
    return {
      kind: "hourly",
      segments: legacyHourly.segments,
      team: legacyHourly.team,
      raw: text,
    };
  }

  return text ? { kind: "text", label: text, raw: text } : { kind: "off", label: "Off" };
};

export const isWorkingCell = (value) => {
  const kind = classifyScheduleCell(value).kind;
  return kind === "shift" || kind === "hourly" || kind === "text";
};

export const isHolidayColumn = (column, holidayMap = {}) => {
  if (!column?.month || !column?.day) return false;
  return Array.isArray(holidayMap[column.month]) && holidayMap[column.month].includes(column.day);
};

export const getShiftMeta = (shiftCode) => {
  const code = String(shiftCode || "").toUpperCase();
  if (code === "M") {
    return {
      label: "Morning",
      short: "M",
      bg: "#dcfce7",
      border: "#86efac",
      text: "#166534",
    };
  }
  if (code === "T") {
    return {
      label: "Afternoon",
      short: "T",
      bg: "#fef3c7",
      border: "#fcd34d",
      text: "#92400e",
    };
  }
  return {
    label: "Night",
    short: "N",
    bg: "#dbeafe",
    border: "#93c5fd",
    text: "#1d4ed8",
  };
};

export const getTeamColor = (team, teamPalette = {}) => {
  if (team && teamPalette[team]) {
    return teamPalette[team];
  }
  return {
    bg: "#f8fafc",
    border: "#cbd5e1",
    text: "#0f172a",
  };
};

export const buildTeamPalette = (values = []) => {
  const base = [
    { bg: "#e0f2fe", border: "#7dd3fc", text: "#075985" },
    { bg: "#dcfce7", border: "#86efac", text: "#166534" },
    { bg: "#fef3c7", border: "#fcd34d", text: "#92400e" },
    { bg: "#fee2e2", border: "#fca5a5", text: "#991b1b" },
    { bg: "#ede9fe", border: "#c4b5fd", text: "#5b21b6" },
    { bg: "#cffafe", border: "#67e8f9", text: "#155e75" },
  ];
  const palette = {};
  Array.from(new Set(values.filter(Boolean))).forEach((team, index) => {
    palette[team] = base[index % base.length];
  });
  return palette;
};

const parseScheduleDate = (label, year, fallbackDay) => {
  const text = String(label ?? "").trim();
  if (/^\d{4}-\d{2}-\d{2}$/.test(text)) {
    const date = new Date(`${text}T00:00:00`);
    if (!Number.isNaN(date.getTime())) {
      return date;
    }
  }

  const dayMatch = text.match(/(?:Dia|Day)\s*(\d+)/i);
  const dayOfYear = dayMatch ? Number(dayMatch[1]) : fallbackDay;
  const date = new Date(year, 0, 1);
  date.setDate(date.getDate() + Math.max(dayOfYear - 1, 0));
  return date;
};

const parseTaggedHourlySegments = (text) => {
  if (!text.includes("@")) return [];
  const segments = text
    .split("|")
    .map((segment) => segment.trim())
    .filter(Boolean)
    .map((segment) => {
      const match = segment.match(/^([^@]+)@(.+)$/);
      if (!match) return null;
      return {
        time: match[1].trim(),
        team: match[2].trim(),
      };
    })
    .filter(Boolean);
  return segments;
};

const parseLegacyHourlyBlock = (text) => {
  const match = text.match(LEGACY_HOURLY_PATTERN);
  if (!match) return null;
  const team = match[4].toUpperCase();
  const points = [match[1], match[2], match[3]].filter(Boolean).map(formatDecimalHour);
  const segments = [];
  if (points.length >= 2) {
    segments.push({ time: `${points[0]}-${points[1]}`, team });
  }
  if (points.length === 3) {
    segments.push({ time: `${points[1]}-${points[2]}`, team });
  }
  return { team, segments };
};

const formatDecimalHour = (value) => {
  const numeric = Number(value);
  if (!Number.isFinite(numeric)) return String(value);
  const hours = Math.floor(numeric);
  const minutes = Math.round((numeric - hours) * 60);
  return `${String(hours).padStart(2, "0")}:${String(minutes).padStart(2, "0")}`;
};

