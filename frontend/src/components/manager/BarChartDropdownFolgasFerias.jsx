import React, { useState } from "react";
import { Button } from "@mui/material";
import { Chart as ChartJS, CategoryScale, LinearScale, BarElement, Title, Tooltip, Legend } from "chart.js";
import { Bar } from "react-chartjs-2";

ChartJS.register(CategoryScale, LinearScale, BarElement, Title, Tooltip, Legend);

const BarChartDropdownFolgasFerias = ({ data, selectedMonth, daysInMonth }) => {
  const [showChart, setShowChart] = useState(false);
  const [globalMode, setGlobalMode] = useState(false);

  // Filtra os dados: se globalMode estiver ativo, utiliza todos os dias do ano; caso contrário, utiliza o mês selecionado.
  const getDisplayedData = () => {
    if (globalMode) {
      const totalDays = daysInMonth.reduce((a, b) => a + b, 0);
      return data.map((row) => [row[0], ...row.slice(1, totalDays + 1)]);
    } else {
      const startDay = daysInMonth.slice(0, selectedMonth - 1).reduce((a, b) => a + b, 0) + 1;
      const endDay = startDay + daysInMonth[selectedMonth - 1] - 1;
      return data.map((row) => [row[0], ...row.slice(startDay, endDay + 1)]);
    }
  };

  const displayedData = getDisplayedData();

  // Abrevia os valores conforme o CSV
  const abbreviateValue = (value) => {
    if (!value) return "";
    switch (value.toLowerCase()) {
      case "folga":
        return "F";
      case "férias":
        return "Fe";
      case "manhã":
        return "M";
      case "tarde":
        return "T";
      default:
        return value;
    }
  };

  // Calcula para cada funcionário o total de dias de Folgas + Férias
  const employeeData = displayedData.slice(1).map((row) => {
    const name = row[0];
    const totalFolgasFerias = row.slice(1).reduce((acc, cell) => {
      const abbr = abbreviateValue(cell || "");
      return abbr === "F" || abbr === "Fe" ? acc + 1 : acc;
    }, 0);
    return { name, totalFolgasFerias };
  });

  const chartData = {
    labels: employeeData.map((item) => item.name),
    datasets: [
      {
        label: globalMode ? "Folgas + Férias Global (Dias)" : "Folgas + Férias (Dias)",
        data: employeeData.map((item) => item.totalFolgasFerias),
        backgroundColor: "#FF5733",
      },
    ],
  };

  const chartOptions = {
    indexAxis: "y",
    responsive: true,
    plugins: {
      legend: { position: "top" },
      title: {
        display: true,
        text: globalMode
          ? "Folgas + Férias Global por Funcionário"
          : "Folgas + Férias por Funcionário",
      },
    },
  };

  return (
    <div style={{ marginTop: "1rem", textAlign: "left" }}>
      {!showChart ? (
        <Button
          variant="contained"
          onClick={() => {
            setShowChart(true);
            setGlobalMode(false); // inicia em modo mensal
          }}
        >
          Ver Folgas + Férias
        </Button>
      ) : (
        <div style={{ display: "flex", gap: "1rem" }}>
          <Button variant="contained" onClick={() => setShowChart(false)}>
            Ocultar Folgas + Férias
          </Button>
          <Button
            variant="contained"
            onClick={() => setGlobalMode(!globalMode)}
          >
            {globalMode ? "Ver Mensal" : "Global"}
          </Button>
        </div>
      )}

      {showChart && (
        <div
          style={{
            marginTop: "1rem",
            padding: "1rem",
            backgroundColor: "#fff",
            borderRadius: "10px",
            width: "70%",
            marginLeft: "auto",
            marginRight: "auto",
          }}
        >
          <Bar data={chartData} options={chartOptions} />
        </div>
      )}
    </div>
  );
};

export default BarChartDropdownFolgasFerias;
