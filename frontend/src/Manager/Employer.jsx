import React, { useState, useEffect } from "react";
import axios from "axios";
import Sidebar_Manager from "../components/Sidebar_Manager";

import {
  Table,
  TableBody,
  TableCell,
  TableContainer,
  TableHead,
  TableRow,
  Paper,
  Typography,
  CircularProgress,
} from "@mui/material";

const Employer = () => {
  const [employees, setEmployees] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  useEffect(() => {
    axios
      .get("http://localhost:8081/api/v1/employees/")
      .then((response) => {
        setEmployees(response.data);
        setLoading(false);
      })
      .catch((error) => {
        console.error("Erro ao buscar employees:", error);
        setError("Erro ao buscar employees.");
        setLoading(false);
      });
  }, []);

  return (
    <div className="admin-container" style={{ display: "flex", minHeight: "100vh" }}>
      <Sidebar_Manager />
      <div className="main-content" style={{ flex: 1, padding: "20px" }}>
        <Typography variant="h5" component="h2" gutterBottom>
          Lista de Employees
        </Typography>

        {loading ? (
          <CircularProgress />
        ) : error ? (
          <Typography color="error">{error}</Typography>
        ) : employees.length > 0 ? (
          <TableContainer component={Paper}>
            <Table>
              <TableHead style={{ backgroundColor: "#4f4f4f" }}>
                <TableRow>
                  <TableCell style={{ color: "#fff" }}>
                    <strong>ID</strong>
                  </TableCell>
                  <TableCell style={{ color: "#fff" }}>
                    <strong>Nome</strong>
                  </TableCell>
                  <TableCell style={{ color: "#fff" }}>
                    <strong>Equipe</strong>
                  </TableCell>
                </TableRow>
              </TableHead>
              <TableBody>
                {employees.map((emp, index) => {
                  const rowStyle = index % 2 === 0
                    ? { backgroundColor: "#f9f9f9" }
                    : { backgroundColor: "#fff" };

                  return (
                    <TableRow key={emp.id} style={rowStyle}>
                      <TableCell>{emp.id}</TableCell>
                      <TableCell>{emp.name}</TableCell>
                      <TableCell>
                        {emp.team ? emp.team.name : "N/A"}
                      </TableCell>
                    </TableRow>
                  );
                })}
              </TableBody>
            </Table>
          </TableContainer>
        ) : (
          <Typography>Nenhum employee encontrado.</Typography>
        )}
      </div>
    </div>
  );
};

export default Employer;
