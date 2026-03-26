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
 * MatrixLegend - Shows color-coded legend for matrix values
 *
 * Simplified to show only 4 marking types:
 * - A: Auto-allocate
 * - Specific hours (from contract)
 * - VAC: Vacation
 * - NOT: Not available
 */
const MatrixLegend = () => {
  const legendItems = [
    { code: 'A', description: 'Auto-allocate from contract', color: '#e8f5e9' },
    { code: 'Xh', description: 'Specific hours (from contract)', color: '#e3f2fd' },
    { code: 'VAC', description: 'Vacation', color: '#fff9c4' },
    { code: 'NOT', description: 'Not available', color: '#ffebee' }
  ];

  return (
    <Paper elevation={0} sx={{ p: 2, bgcolor: '#fafafa', border: '1px solid #e0e0e0' }}>
      <Typography variant="subtitle2" gutterBottom fontWeight={600}>
        Legend
      </Typography>
      <Box sx={{ display: 'flex', flexWrap: 'wrap', gap: 0.5 }}>
        {legendItems.map((item) => (
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
