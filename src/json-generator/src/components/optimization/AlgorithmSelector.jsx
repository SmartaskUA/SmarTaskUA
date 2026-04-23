import React from 'react';
import {
  Box,
  RadioGroup,
  FormControlLabel,
  Radio,
  Typography,
  Paper,
  Chip
} from '@mui/material';
import { Recommend as RecommendIcon } from '@mui/icons-material';

/**
 * Algorithm Metadata
 */
const ALGORITHMS = {
  ILP: {
    name: 'Integer Linear Programming (ILP)',
    description: 'Best solution quality. Guarantees optimal results but may be slower for very large problems (100+ employees, 365 days). Recommended for most use cases.',
    recommended: true,
    bestFor: 'Optimal solutions, medium-sized problems',
    complexity: 'High quality, medium-to-slow speed'
  },
  CSPv2: {
    name: 'Constraint Satisfaction v2 (CSPv2)',
    description: 'Good balance between speed and quality. Handles complex constraint combinations well. Suitable for problems with many hard constraints.',
    recommended: false,
    bestFor: 'Complex constraints, balanced performance',
    complexity: 'Good quality, medium speed'
  },
  Heuristic: {
    name: 'Heuristic Search',
    description: 'Very fast, produces approximate solutions. Best for rapid prototyping or very large problems where speed is critical. May not satisfy all soft constraints.',
    recommended: false,
    bestFor: 'Large problems, rapid prototyping',
    complexity: 'Approximate solutions, very fast'
  },
  Hybrid: {
    name: 'Hybrid (ILP + Heuristics)',
    description: 'Combines ILP with heuristic pre-processing for faster convergence. Good for large problems requiring high-quality solutions.',
    recommended: false,
    bestFor: 'Large problems needing quality solutions',
    complexity: 'High quality, good speed'
  }
};

/**
 * AlgorithmSelector Component
 *
 * Radio group for selecting the scheduling algorithm with detailed descriptions
 */
const AlgorithmSelector = ({ value, onChange }) => {
  const handleChange = (event) => {
    onChange(event.target.value);
  };

  return (
    <Box>
      <Typography variant="h6" gutterBottom fontWeight={600}>
        Solver Algorithm
      </Typography>
      <Typography variant="body2" color="text.secondary" sx={{ mb: 2 }}>
        Choose the algorithm that will generate your schedule. Different algorithms offer trade-offs between
        speed and solution quality.
      </Typography>

      <RadioGroup value={value} onChange={handleChange}>
        {Object.entries(ALGORITHMS).map(([key, algo]) => (
          <Paper
            key={key}
            sx={{
              p: 2,
              mb: 2,
              border: 1,
              borderColor: value === key ? 'primary.main' : 'divider',
              backgroundColor: value === key ? 'action.selected' : 'background.paper',
              transition: 'all 0.2s',
              cursor: 'pointer',
              '&:hover': {
                borderColor: 'primary.light',
                backgroundColor: 'action.hover'
              }
            }}
            onClick={() => onChange(key)}
          >
            <FormControlLabel
              value={key}
              control={<Radio />}
              label={
                <Box sx={{ ml: 1, width: '100%' }}>
                  {/* Title with recommended badge */}
                  <Box sx={{ display: 'flex', alignItems: 'center', gap: 1, mb: 0.5 }}>
                    <Typography variant="subtitle1" fontWeight={600}>
                      {algo.name}
                    </Typography>
                    {algo.recommended && (
                      <Chip
                        icon={<RecommendIcon />}
                        label="Recommended"
                        size="small"
                        color="primary"
                        variant="outlined"
                      />
                    )}
                  </Box>

                  {/* Description */}
                  <Typography variant="body2" color="text.secondary" sx={{ mb: 1 }}>
                    {algo.description}
                  </Typography>

                  {/* Metadata chips */}
                  <Box sx={{ display: 'flex', gap: 1, flexWrap: 'wrap', mt: 1 }}>
                    <Chip
                      label={algo.complexity}
                      size="small"
                      variant="outlined"
                      sx={{ fontSize: 11 }}
                    />
                    <Chip
                      label={`Best for: ${algo.bestFor}`}
                      size="small"
                      variant="outlined"
                      sx={{ fontSize: 11 }}
                    />
                  </Box>
                </Box>
              }
              sx={{ width: '100%', alignItems: 'flex-start', m: 0 }}
            />
          </Paper>
        ))}
      </RadioGroup>
    </Box>
  );
};

export default AlgorithmSelector;
