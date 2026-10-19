import React from 'react';
import { Box, Typography, Tooltip } from '@mui/material';
import { PX_PER_MINUTE } from './TimeAxis';
import { formatNumber, tryParseRange } from '../../v4/core';
import { pairLabel } from '../../v4/state';
import { getDarkerColor, getTeamColor } from '../../utils/helpers/colorHelpers';

const fmt = (v) => formatNumber(Number(v) || 0);

/**
 * One weekly-template block inside its dimension's lane. A block that crosses
 * midnight is drawn to 24:00 here, and its continuation on the next day's column.
 */
const DemandBlock = ({ block, onEdit, continuation = false, overlapping = false }) => {
  const w = tryParseRange(block.start, block.end);
  if (!w) return null;
  const [start, end] = continuation ? [0, w[1] - 1440] : [w[0], Math.min(w[1], 1440)];
  const color = getTeamColor(pairLabel(block.tableName, block.tableValue));
  const extras = [Number(block.ideal) ? `ideal ${fmt(block.ideal)}` : '', Number(block.estimated) ? `est. ${fmt(block.estimated)}` : '']
    .filter(Boolean).join(' · ');
  const tip = `${pairLabel(block.tableName, block.tableValue)} ${block.start}–${block.end}: minimum ${fmt(block.minimum)}${extras ? ` (${extras})` : ''}`
    + (overlapping ? ' — overlaps another window of this dimension' : '');

  return (
    <Tooltip title={tip} placement="right">
      <Box
        role="button"
        tabIndex={0}
        aria-label={tip}
        onClick={(e) => { e.stopPropagation(); onEdit(block); }}
        onKeyDown={(e) => { if (e.key === 'Enter' || e.key === ' ') { e.preventDefault(); e.stopPropagation(); onEdit(block); } }}
        sx={{
          position: 'absolute',
          top: start * PX_PER_MINUTE,
          height: Math.max((end - start) * PX_PER_MINUTE, 14),
          left: 2,
          right: 2,
          bgcolor: color,
          opacity: continuation ? 0.6 : 0.92,
          border: `2px ${continuation ? 'dashed' : 'solid'} ${overlapping ? '#d32f2f' : getDarkerColor(color)}`,
          borderRadius: 1,
          color: '#fff',
          px: 0.5,
          overflow: 'hidden',
          cursor: 'pointer',
          zIndex: 2,
          '&:hover': { opacity: 1, boxShadow: 3, zIndex: 3 }
        }}
      >
        <Typography sx={{ fontSize: 11, fontWeight: 700, lineHeight: 1.3 }}>
          {fmt(block.minimum)}{extras ? '*' : ''}
        </Typography>
        <Typography sx={{ fontSize: 10, lineHeight: 1.2, fontFamily: 'monospace' }}>
          {continuation ? `…–${block.end}` : `${block.start}–${block.end}`}
        </Typography>
      </Box>
    </Tooltip>
  );
};

export default DemandBlock;
