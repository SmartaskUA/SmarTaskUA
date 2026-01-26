import React from "react";
import {
  Accordion,
  AccordionSummary,
  AccordionDetails,
  CardContent,
  Typography,
  Box,
  Paper,
  Chip,
  Grid,
  Tooltip
} from "@mui/material";
import ExpandMoreIcon from "@mui/icons-material/ExpandMore";
import ErrorIcon from "@mui/icons-material/Error";
import CheckCircleIcon from "@mui/icons-material/CheckCircle";
import HelpOutlineIcon from "@mui/icons-material/HelpOutline";

const metricInfo = {
  // ============ SHIFT-BASED METRICS (kpiVerification.py) ============                                   
  tmFails: {
    label: "Afternoon-Morning Sequence",
    description: "Number of times an employee works in an afternoon shift followed by a morning shift in the day after.",
  },
  consecutiveDays: {
    label: "Consecutive Work-Day Violations",
    description: "Number of times employees exceeded the maximum allowed run of five consecutive working days.",
  },
  workHolidays: {
    label: "Holidays and Sundays Work Days",
    description: "Number of work days falling on holidays and Sundays that exceed the predefined threshold.",
  },
  missedVacationDays: {
    label: "Missed Vacation Days",
    description: "Total variance between actual and target vacation days for all employees.",
  },
  missedWorkDays: {
    label: "Missed Working Days",
    description: "Total variance between actual and target working days for all employees.",
  },
  missedTeamMin: {
    label: "Missed Minimums",
    description: "Each team, shift, and day, the count of employees below the required minimum staffing level.",
  },
  missedTeamIdeal: {
    label: "Missed Ideals",
    description: "Each team, shift, and day, the count of employees below the ideal staffing level.",
  },
  singleTeamViolations: {
    label: "Single Team Violations",
    description: "Number of employees allowed to work only one team but worked in more than one.",
  },
  shiftBalance: {
    label: "Shift Balance",
    description: "Percentage deviation of the most unbalanced shift distribution exhibited by any employee.",
  },
  teamSatisfactionLevel: {
    label: "Team Satisfaction Level",
    description: "Median distribution of work between primary and secondary team for employees assigned to two teams.",
  },
  hourlyCoverageGaps: {
    label: "Hourly Coverage Gaps",
    description: "Total shortfall versus required hourly staffing across all teams and days.",
  },
  hourlyOverstaff: {
    label: "Hourly Overstaff",
    description: "Total overstaffing versus required hourly staffing across all teams and days.",
  },

  // ============ HOURLY METRICS (kpiVerification_unified_v3.py) ============                             
  workDaysTargetDeviation: {                                                                              
    label: "Work Days Target Deviation",                                                                  
    description: "Total absolute deviation from the target of 223 workdays per year, summed across all employees (0 means everyone has exactly 223 workdays).",                                                  
  }, 

  vacationDaysQuotaDeviation: {                                                                           
    label: "Vacation Days Quota Deviation",                                                               
    description: "Total absolute deviation from the mandatory vacation days per year, across all employees (0 means everyone has exactly 30 vacation days).",                                                       
  },                                                                                                      
  holidayWorkLimitViolations: {                                                                           
    label: "Holiday Work Limit Violations",                                                               
    description: "Total number of holiday/weekend workdays beyond the legal limit of 22, summed across employees.",                                                                                              
  },                                                                                                      
  consecutiveDaysViolations: {                                                                            
    label: "Consecutive Days Violations",                                                                 
    description: "Total count of violations where an employee worked 6 or more consecutive days without a rest day.",                                                                                               
  },                                                                                                      
  totalStaffingGap: {                                                                                     
    label: "Total Staffing Gap",                                                                          
    description: "Total missing staff compared to required minimums across all teams, time slots and days.",                                                                                                   
  },         
  staffingCoverageRate: {                                                                                 
    label: "Staffing Coverage Rate",                                                                      
    description: "Percentage of time slots where the minimum staffing requirement was met (100% means all minimums were satisfied).",                                                                               
  },                                                                                               
  totalIdealGap: {                                                                                        
    label: "Total Ideal Gap",                                                                             
    description: "Total missing staff compared to ideal staffing levels across all teams, time slots and days (N/A when no ideal requirements are provided).",                                                     
  },                                                                                                      
  excessStaffing: {                                                                                       
    label: "Excess Staffing",                                                                             
    description: "Total extra staff assigned beyond required minimums across all teams, time slots and days.",                                                                                                   
  },                                                                                                      
  minRestViolations: {                                                                                    
    label: "Minimum Rest Violations",                                                                     
    description: "Number of shift-to-shift transitions where the rest time between consecutive working days is less than 11 hours (should be 0 if the schedule is valid).",                                      
  },                                                                                               
};                                            


const KPIReport = ({ metrics = {}, scheduleType }) => {
  console.log("KPI Metrics:", metrics);
  const normalizedType = String(scheduleType || "").toLowerCase();

  // Detect if hourly based on schedule type OR presence of hourly-specific metrics
  const isHourly =
    normalizedType === "horas" ||
    normalizedType === "hours" ||
    metrics.totalStaffingGap !== undefined ||                                                             
    metrics.excessStaffing !== undefined ||                                                               
    metrics.workDaysTargetDeviation !== undefined;  

  // Shift-based metrics (from kpiVerification.py)     
  const shiftMetrics = [
    "tmFails",
    "consecutiveDays",
    "workHolidays",
    "missedVacationDays",
    "missedWorkDays",
    "missedTeamMin",
    "missedTeamIdeal",
    "singleTeamViolations",
    "shiftBalance",
    "teamSatisfactionLevel",
  ];

  // Hourly metrics (from kpiVerification_unified_v3.py)       
  const hourlyMetrics = [                                                                                 
    "workDaysTargetDeviation",                                                                            
    "vacationDaysQuotaDeviation",                                                                         
    "holidayWorkLimitViolations",                                                                         
    "consecutiveDaysViolations",                                                                          
    "minRestViolations",                                                                                  
    "totalStaffingGap",
    "staffingCoverageRate",                                                                                  
    "totalIdealGap",                                                                                      
    "excessStaffing",                                                                                     
  ]; 

  const displayMetrics = isHourly ? hourlyMetrics : shiftMetrics;
  const percentMetrics = new Set(["shiftBalance", "teamSatisfactionLevel", "staffingCoverageRate"]);

  // Filter out metrics that shouldn't count as issues 
  const issueMetrics = displayMetrics.filter(
    (key) => key !== "shiftBalance" && key !== "teamSatisfactionLevel"
  );
  
  const totalIssues = issueMetrics                                                                        
    .map((key) => {                                                                                       
      const value = metrics[key];                                                                         
      // Handle null/undefined (e.g., totalIdealGap can be null)                                          
      if (value === null || value === undefined) return 0;                                                
      const numValue = Number(value);                                                                     
      return Number.isFinite(numValue) ? numValue : 0;                                                    
    })                                                                                                    
    .filter((v) => v > 0).length;  

  const getStatusChip = () =>
    totalIssues === 0 ? (
      <Chip label="No Issues" color="success" icon={<CheckCircleIcon />} />
    ) : (
      <Chip label="Issues Found" color="error" icon={<ErrorIcon />} />
    );

  const renderMetric = (key, value, isViolation, isPercentage = false) => {
    const { label, description } = metricInfo[key] || {};
    return (
      <Box>
        <Typography variant="subtitle1" fontWeight="bold" color="primary" gutterBottom>
          <Tooltip title={description || ""} arrow>
            <span style={{ display: "flex", alignItems: "center", gap: 4 }}>
              {label || key}
              <HelpOutlineIcon fontSize="small" />
            </span>
          </Tooltip>
        </Typography>
        <Typography
          color={
            isPercentage
              ? "text.primary"
              : isViolation
              ? "error.main"
              : "success.main"
          }
        >
          {value}
        </Typography>
      </Box>
    );
  };

  return (
    <CardContent sx={{ px: 0, mt: 2 }}>
      <Accordion elevation={3} sx={{ borderRadius: 2 }}>
        <AccordionSummary expandIcon={<ExpandMoreIcon />} sx={{ px: 2 }}>
          <Typography variant="h6" fontWeight="bold" sx={{ flexGrow: 1 }}>
            Key Performance Indicators (KPIs)
          </Typography>
          {getStatusChip()}
        </AccordionSummary>

        <AccordionDetails>
          <Paper elevation={0} sx={{ p: 3 }}>
            <Grid container spacing={3}>
              {displayMetrics.map((key) => {
                const rawValue = metrics[key];

                // Handle null (e.g., totalIdealGap when no ideals provided)
                if (rawValue === null || rawValue === undefined) {
                  return (
                    <Grid item xs={12} sm={6} md={3} key={key}>
                      {renderMetric(key, "N/A", false, false)}
                    </Grid>
                  );
                }

                const value = Number.isFinite(Number(rawValue)) ? Number(rawValue) : 0;
                const isPercentage = percentMetrics.has(key);
                const displayValue = isPercentage ? `${value}%` : value;
                const isViolation = !isPercentage && value > 0;
                return (
                  <Grid item xs={12} sm={6} md={3} key={key}>
                    {renderMetric(key, displayValue, isViolation, isPercentage)}
                  </Grid>
                );
              })}
            </Grid>
          </Paper>
        </AccordionDetails>
      </Accordion>
    </CardContent>
  );
};

export default KPIReport;
