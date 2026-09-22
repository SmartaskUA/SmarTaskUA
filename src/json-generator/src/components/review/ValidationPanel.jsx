import React from 'react';
import {
  Card,
  CardHeader,
  CardContent,
  Typography,
  Alert,
  AlertTitle,
  List,
  ListItem,
  ListItemText,
  Button,
  Badge,
  Box,
  Chip
} from '@mui/material';
import { CheckCircle, Error as ErrorIcon, Warning, Refresh } from '@mui/icons-material';

/**
 * Validation Panel Component
 *
 * Displays validation results with:
 * - Success state with stats
 * - Error list (blocks generation)
 * - Warning list (doesn't block generation)
 * - Revalidate button
 */
const ValidationPanel = ({ results, onRevalidate }) => {
  if (!results) {
    return (
      <Card sx={{ mb: 3 }}>
        <CardContent>
          <Typography>Running validation...</Typography>
        </CardContent>
      </Card>
    );
  }

  const { valid, errors, warnings, stats } = results;

  return (
    <Card sx={{ mb: 3 }}>
      <CardHeader
        title={
          <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
            <Typography variant="h6">Validation Results</Typography>
            {valid && errors.length === 0 && <CheckCircle color="success" />}
            {errors.length > 0 && <ErrorIcon color="error" />}
          </Box>
        }
        action={
          <Button
            size="small"
            startIcon={<Refresh />}
            onClick={onRevalidate}
            variant="outlined"
          >
            Revalidate
          </Button>
        }
      />
      <CardContent>
        {/* Success State */}
        {valid && errors.length === 0 && (
          <Alert severity="success" icon={<CheckCircle />}>
            <AlertTitle>All Validations Passed!</AlertTitle>
            <Typography variant="body2">
              Your configuration is valid and ready to download.
            </Typography>
            {stats && (
              <Box sx={{ mt: 2, display: 'flex', gap: 1, flexWrap: 'wrap' }}>
                <Chip
                  label={`${stats.totalEmployees} Employees`}
                  size="small"
                  color="success"
                  variant="outlined"
                />
                <Chip
                  label={`${stats.totalContracts} Contracts`}
                  size="small"
                  color="success"
                  variant="outlined"
                />
                <Chip
                  label={`${stats.totalWorkPeriods} Work Periods`}
                  size="small"
                  color="success"
                  variant="outlined"
                />
                <Chip
                  label={`${stats.dateRange} Days`}
                  size="small"
                  color="success"
                  variant="outlined"
                />
                {stats.totalTeams > 0 && (
                  <Chip
                    label={`${stats.totalTeams} Teams`}
                    size="small"
                    color="success"
                    variant="outlined"
                  />
                )}
                {stats.totalDemandEntries > 0 && (
                  <Chip
                    label={`${stats.totalDemandEntries} Demand Entries`}
                    size="small"
                    color="success"
                    variant="outlined"
                  />
                )}
                {stats.scheduleInputCoverage > 0 && (
                  <Chip
                    label={`${stats.scheduleInputCoverage}% Schedule Coverage`}
                    size="small"
                    color="success"
                    variant="outlined"
                  />
                )}
              </Box>
            )}
          </Alert>
        )}

        {/* Errors */}
        {errors && errors.length > 0 && (
          <Alert severity="error" icon={<ErrorIcon />} sx={{ mb: 2 }}>
            <AlertTitle>
              <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
                <span>Errors Found</span>
                <Badge badgeContent={errors.length} color="error" />
              </Box>
            </AlertTitle>
            <List dense sx={{ mt: 1 }}>
              {errors.map((err, i) => (
                <ListItem key={i} sx={{ pl: 0 }}>
                  <ListItemText
                    primary={err.message}
                    secondary={
                      <span>
                        <strong>Step {err.step}</strong>
                        {err.field && ` • ${err.field}`}
                      </span>
                    }
                    primaryTypographyProps={{ variant: 'body2' }}
                    secondaryTypographyProps={{ variant: 'caption' }}
                  />
                </ListItem>
              ))}
            </List>
            <Typography variant="caption" color="error" sx={{ display: 'block', mt: 1 }}>
              Fix these errors to enable file download.
            </Typography>
          </Alert>
        )}

        {/* Warnings */}
        {warnings && warnings.length > 0 && (
          <Alert severity="warning" icon={<Warning />}>
            <AlertTitle>
              <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
                <span>Warnings</span>
                <Badge badgeContent={warnings.length} color="warning" />
              </Box>
            </AlertTitle>
            <List dense sx={{ mt: 1 }}>
              {warnings.map((warn, i) => (
                <ListItem key={i} sx={{ pl: 0 }}>
                  <ListItemText
                    primary={warn.message}
                    secondary={
                      <span>
                        <strong>Step {warn.step}</strong>
                        {warn.field && ` • ${warn.field}`}
                      </span>
                    }
                    primaryTypographyProps={{ variant: 'body2' }}
                    secondaryTypographyProps={{ variant: 'caption' }}
                  />
                </ListItem>
              ))}
            </List>
            <Typography variant="caption" color="text.secondary" sx={{ display: 'block', mt: 1 }}>
              Warnings don't prevent file download, but you should review them.
            </Typography>
          </Alert>
        )}
      </CardContent>
    </Card>
  );
};

export default ValidationPanel;
