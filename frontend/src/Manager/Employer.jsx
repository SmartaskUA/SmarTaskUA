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
  Typography,
  CircularProgress,
  Box,
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
        <Box mb={4}>
          <h2>Lista de Employees</h2>
        </Box>

        {loading ? (
          <Box display="flex" justifyContent="center" alignItems="center" minHeight="60vh">
            <CircularProgress size={60} />
          </Box>
        ) : error ? (
          <Box display="flex" justifyContent="center" alignItems="center" minHeight="60vh">
            <Typography variant="h6" color="error" align="center">
              {error}
            </Typography>
          </Box>
        ) : employees.length > 0 ? (
          <TableContainer style={{ borderRadius: 8 }}>
            <Table>
              <TableHead style={{ backgroundColor: "#1976d2", color: "#fff" }}>
                <TableRow>
                  <TableCell style={{ color: "#fff", fontWeight: "bold" }}>ID</TableCell>
                  <TableCell style={{ color: "#fff", fontWeight: "bold" }}>Nome</TableCell>
                  <TableCell style={{ color: "#fff", fontWeight: "bold" }}>Equipe</TableCell>
                </TableRow>
              </TableHead>
              <TableBody>
                {employees.map((emp, index) => {
                  const rowStyle = index % 2 === 0
                    ? { backgroundColor: "#f2f2f2" }
                    : { backgroundColor: "#ffffff" };

                  return (
                    <TableRow key={emp.id} style={rowStyle}>
                      <TableCell>{emp.id}</TableCell>
                      <TableCell>{emp.name}</TableCell>
                      <TableCell>{emp.team ? emp.team.name : "N/A"}</TableCell>
                    </TableRow>
                  );
                })}
              </TableBody>
            </Table>
          </TableContainer>
        ) : (
          <Box display="flex" justifyContent="center" alignItems="center" minHeight="60vh">
            <Typography variant="h6">Nenhum employee encontrado.</Typography>
          </Box>
        )}
      </div>
    </div>
  );
};

export default Employer;
