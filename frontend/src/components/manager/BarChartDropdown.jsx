import React, { useState } from "react";
import { Button } from "@mui/material";
import { Chart as ChartJS, CategoryScale, LinearScale, BarElement, Title, Tooltip, Legend } from "chart.js";
import { Bar } from "react-chartjs-2";

ChartJS.register(CategoryScale, LinearScale, BarElement, Title, Tooltip, Legend);

const BarChartDropdown = ({ data, selectedMonth, daysInMonth }) => {
  const [showChart, setShowChart] = useState(false);
  const [globalMode, setGlobalMode] = useState(false);

  // Função para filtrar os dados: se globalMode estiver ativo, usa todos os dias do ano; caso contrário, filtra pelo mês selecionado.
  const getDisplayedData = () => {
    if (globalMode) {
      // Modo global: usa todos os dias do ano
      const totalDays = daysInMonth.reduce((a, b) => a + b, 0);
      return data.map((row) => [row[0], ...row.slice(1, totalDays + 1)]);
    } else {
      // Modo mensal: usa os dados do mês selecionado
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

  // Calcula a carga horária: conta os dias com "M" ou "T" para cada funcionário
  const employeeData = displayedData.slice(1).map((row) => {
    const name = row[0];
    const workingDays = row.slice(1).reduce((acc, cell) => {
      const abbr = abbreviateValue(cell || "");
      return abbr === "M" || abbr === "T" ? acc + 1 : acc;
    }, 0);
    return { name, workingDays };
  });

  const chartData = {
    labels: employeeData.map((item) => item.name),
    datasets: [
      {
        label: globalMode
          ? "Carga Horária Global (Dias de Trabalho)"
          : "Carga Horária (Dias de Trabalho)",
        data: employeeData.map((item) => item.workingDays),
        backgroundColor: "#007bff",
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
          ? "Carga Horária Global por Funcionário"
          : "Carga Horária por Funcionário",
      },
    },
  };

  return (
    <div style={{ marginTop: "1rem", textAlign: "left" }}>
      {/* Se o gráfico estiver oculto, exibe apenas o botão "Ver Carga Horária" */}
      {!showChart ? (
        <Button
          variant="contained"
          onClick={() => {
            setShowChart(true);
            setGlobalMode(false); // inicia em modo mensal
          }}
        >
          Ver Carga Horária
        </Button>
      ) : (
        // Se o gráfico estiver visível, exibe os botões para ocultar e alternar o modo
        <div style={{ display: "flex", gap: "1rem" }}>
          <Button variant="contained" onClick={() => setShowChart(false)}>
            Ocultar Carga Horária
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

export default BarChartDropdown;
