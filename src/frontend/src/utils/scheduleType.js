export const inferScheduleType = (metadata) => {
  if (!metadata) return "";
  const shifts = Number(metadata.shifts);
  if (Number.isFinite(shifts)) {
    if (shifts <= 3) return "Turno";
    if (shifts > 3) return "Horas";
  }
  const algorithm = String(metadata.algorithmType || "").toLowerCase();
  if (algorithm.includes("hour") || algorithm.includes("half")) return "Horas";
  return "";
};

export const inferHourGranularity = (metadata) => {
  if (!metadata) return "";
  const algorithm = String(metadata.algorithmType || "").toLowerCase();
  if (algorithm.includes("half") || algorithm.includes("30")) return "30min";
  const minsData = metadata.minimunsTemplateData;
  if (Array.isArray(minsData)) {
    for (const row of minsData) {
      const label = row?.[1];
      if (label && String(label).includes(":")) {
        return "30min";
      }
    }
  }
  return "hour";
};
