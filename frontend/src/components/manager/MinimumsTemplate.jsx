import React from "react";
import { Table, TableBody, TableCell, TableHead, TableRow, Typography } from "@mui/material";

const MinimumsTemplate = ({ name, data }) => {
  if (!data || Object.keys(data).length === 0) return null;

  const days = Object.keys(Object.values(data)[0]?.M || {});
  const teams = Object.keys(data);

  return (
    <div style={{ marginTop: 20 }}>
      <Typography variant="h6" gutterBottom>
        Template: {name}
      </Typography>
      <Table size="small">
        <TableHead>
          <TableRow>
            {teams.map((team) => (
              <TableCell align="center" colSpan={2} key={team}><strong>{team}</strong></TableCell>
            ))}
          </TableRow>
          <TableRow>
            {teams.map(() => (
              <>
                <TableCell align="center">Min</TableCell>
                <TableCell align="center">Ideal</TableCell>
              </>
            ))}
          </TableRow>
          <TableRow>
            {teams.map(() =>
              days.map((day) => (
                <>
                  <TableCell align="center">{day}</TableCell>
                  <TableCell align="center">{day}</TableCell>
                </>
              ))
            )}
          </TableRow>
        </TableHead>
        <TableBody>
          {days.map((day) => (
            <TableRow key={day}>
              {teams.map((team) => (
                <>
                  <TableCell align="center">{data[team]?.M?.[day]}</TableCell>
                  <TableCell align="center">{data[team]?.T?.[day]}</TableCell>
                </>
              ))}
            </TableRow>
          ))}
        </TableBody>
      </Table>
    </div>
  );
};

export default MinimumsTemplate;
