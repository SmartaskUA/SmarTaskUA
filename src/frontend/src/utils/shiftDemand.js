// Shift-based problem bundles (schema 2.x) ship a demand.csv with rows
// date,shift,team,minimum,ideal[,estimated]. The schedule page shows those the
// same way as a minimums template (team / Minimum|Ideal / shift / one value per
// day of the year), so they are converted to that row format here.

const MS_PER_DAY = 24 * 60 * 60 * 1000;

const isLeapYear = (year) => (year % 4 === 0 && year % 100 !== 0) || year % 400 === 0;

/** Zero-based day of the year for a "YYYY-MM-DD" date, or null when it is outside `year`. */
const dayOfYearIndex = (dateText, year) => {
  const match = String(dateText || "").trim().match(/^(\d{4})-(\d{2})-(\d{2})/);
  if (!match) return null;
  const [, y, m, d] = match.map(Number);
  if (y !== year) return null;
  return Math.round((Date.UTC(y, m - 1, d) - Date.UTC(y, 0, 1)) / MS_PER_DAY);
};

/** True for demand rows keyed by shift (not by workPeriod, which the hourly demand view handles). */
export const isShiftDemandData = (rows) =>
  Array.isArray(rows) &&
  rows.some((row) => String(row?.shift || "").trim() && !String(row?.workPeriod || "").trim());

const toCell = (value) => {
  const text = String(value ?? "").trim();
  return text === "" || !Number.isFinite(Number(text)) ? "" : Number(text);
};

/**
 * Converts shift demand rows into minimums-template rows:
 *   ["Team A", "Minimum", "M", v1, ..., v365]
 *   ["",       "Minimum", "T", ...]
 *   ["",       "Ideal",   "M", ...]
 * Days without a demand row stay empty (shown as "—").
 */
export const shiftDemandToTemplate = (rows, year) => {
  if (!isShiftDemandData(rows)) return [];
  const daysInYear = isLeapYear(year) ? 366 : 365;
  const hasIdeals = rows.some((row) => String(row?.ideal ?? "").trim() !== "");

  // team -> shift -> { min: [], ideal: [] }, keeping first-seen order.
  const teams = new Map();
  rows.forEach((row) => {
    const team = String(row?.team || "").trim();
    const shift = String(row?.shift || "").trim().toUpperCase();
    const day = dayOfYearIndex(row?.date, year);
    if (!team || !shift || day === null) return;
    if (!teams.has(team)) teams.set(team, new Map());
    const shifts = teams.get(team);
    if (!shifts.has(shift)) {
      shifts.set(shift, {
        min: Array(daysInYear).fill(""),
        ideal: Array(daysInYear).fill(""),
      });
    }
    const entry = shifts.get(shift);
    entry.min[day] = toCell(row.minimum);
    entry.ideal[day] = toCell(row.ideal);
  });

  const template = [];
  teams.forEach((shifts, team) => {
    let first = true;
    const pushRows = (type, key) => {
      shifts.forEach((entry, shift) => {
        template.push([first ? `Team ${team}` : "", type, shift, ...entry[key]]);
        first = false;
      });
    };
    pushRows("Minimum", "min");
    if (hasIdeals) pushRows("Ideal", "ideal");
  });
  return template;
};

/**
 * Total staff missing against the template over the whole year, for "min" or
 * "ideal" rows: sum over (day, shift, team) of max(0, required - assigned).
 * Schedule cells are "<shift>_<team>" (e.g. "M_A"); column i+1 is day i.
 */
export const countMissingFromTemplate = (template, scheduleData, type) => {
  if (!template.length || !Array.isArray(scheduleData) || scheduleData.length < 2) return null;
  const assigned = new Map();
  scheduleData.slice(1).forEach((row) => {
    if (!Array.isArray(row)) return;
    row.slice(1).forEach((cell, day) => {
      const match = String(cell || "").trim().match(/^([A-Za-z])\s*[_-]\s*([A-Za-z0-9]+)$/);
      if (!match) return;
      const key = `${day}|${match[1].toUpperCase()}|${match[2].toUpperCase()}`;
      assigned.set(key, (assigned.get(key) || 0) + 1);
    });
  });

  const wantedType = type === "ideal" ? "Ideal" : "Minimum";
  let currentTeam = null;
  let missing = 0;
  template.forEach((row) => {
    if (row[0]) currentTeam = String(row[0]).replace(/^Team\s+/, "").toUpperCase();
    if (row[1] !== wantedType) return;
    const shift = row[2];
    row.slice(3).forEach((required, day) => {
      if (required === "" || required < 0) return;
      const have = assigned.get(`${day}|${shift}|${currentTeam}`) || 0;
      missing += Math.max(0, required - have);
    });
  });
  return missing;
};
