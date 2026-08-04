import React from 'react';
import { Box, Chip, Typography, Paper } from '@mui/material';
import { styled } from '@mui/material/styles';

const LegendChip = styled(Chip)(({ bgcolor }) => ({
  margin: '4px',
  backgroundColor: bgcolor,
  '& .MuiChip-label': {
    fontWeight: 600,
    fontSize: '13px'
  }
}));

/**
 * MatrixLegend - Color-coded legend for all schedule matrix values
 */
const MatrixLegend = () => {
  const standardItems = [
    { code: 'A',   description: 'Auto-allocate from contract', color: '#e8f5e9' },
    { code: 'Xh',  description: 'Specific hours (e.g. 8h)',    color: '#e3f2fd' },
    { code: 'VAC', description: 'Vacation',                    color: '#fff9c4' },
    { code: 'NOT', description: 'Not available',               color: '#ffebee' }
  ];

  const timeConstraintItems = [
    { code: 'EQUALS',  description: 'Must work exact time window', color: '#e1bee7' },
    { code: 'INCLUDE', description: 'Must cover time range min.',  color: '#ffe0b2' },
    { code: 'EXCEPT',  description: 'Unavailable in window',       color: '#f8bbd0' }
  ];

  return (
    <Paper elevation={0} sx={{ p: 2, bgcolor: '#fafafa', border: '1px solid #e0e0e0' }}>
      <Typography variant="subtitle2" gutterBottom fontWeight={600}>
        Legend
      </Typography>

      <Box sx={{ display: 'flex', flexWrap: 'wrap', gap: 0.5, mb: 1 }}>
        {standardItems.map((item) => (
          <LegendChip
            key={item.code}
            label={`${item.code}: ${item.description}`}
            size="small"
            bgcolor={item.color}
          />
        ))}
      </Box>

      <Typography variant="caption" color="text.secondary" sx={{ display: 'block', mb: 0.5 }}> </Typography>
      <Box sx={{ display: 'flex', flexWrap: 'wrap', gap: 0.5 }}>
        {timeConstraintItems.map((item) => (
          <LegendChip
            key={item.code}
            label={`${item.code}: ${item.description}`}
            size="small"
            bgcolor={item.color}
          />
        ))}
      </Box>
    </Paper>
  );
};

export default MatrixLegend;
